#!/usr/bin/env python3
"""
QLoRA Fine-tuning: Qwen2.5-14B-Instruct
妖怪ハザードマップ + 避難案内AI 統合学習 (142,000件)

使用方法:
  python train_qlora.py --config train_config.yaml

必要パッケージ:
  pip install torch transformers peft bitsandbytes trl datasets accelerate wandb
"""

import argparse
import json
import os
import sys
from pathlib import Path

import torch
import yaml
from datasets import Dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from trl import SFTTrainer, DataCollatorForCompletionOnlyLM

# ============================================================
# task_type別システムプロンプト
# ============================================================

SYSTEM_PROMPTS = {
    "youkai_hazard": (
        "あなたは妖怪ハザードマップの案内役です。"
        "妖怪キャラクターの口調を使い、地域の災害リスクについてわかりやすく説明してください。"
        "出力は指定されたJSON形式で返してください。"
    ),
    "evacuation_qa": (
        "あなたは災害時避難支援AIです。"
        "避難所に関する質問に対して、正確で分かりやすい情報を提供してください。"
        "緊急時は簡潔に、平時は詳細に回答してください。"
        "出力は指定されたJSON形式で返してください。"
    ),
    "route_guidance": (
        "あなたは避難経路案内AIです。"
        "ユーザーの現在地と状況に基づき、安全な避難経路を案内してください。"
        "複数のルートがある場合は選択肢を提示してください。"
        "出力は指定されたJSON形式で返してください。"
    ),
    "disaster_scenario": (
        "あなたは災害対応AIです。"
        "発生した災害の種別に応じて、適切な避難行動を案内してください。"
        "パニックを避け、冷静で具体的な指示を心がけてください。"
        "出力は指定されたJSON形式で返してください。"
    ),
    "local_info": (
        "あなたは地域防災情報AIです。"
        "地域固有の災害リスクや避難に関する情報を提供してください。"
        "過去の災害経験や地域の知恵を活かした回答を心がけてください。"
        "出力は指定されたJSON形式で返してください。"
    ),
}


def load_train_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def format_record_to_messages(record: dict) -> list[dict]:
    """教師データ1件をchat messages形式に変換"""
    task_type = record.get("task_type", "youkai_hazard")
    instruction = record.get("instruction", "")
    input_data = record.get("input", "")
    output_data = record.get("output", record.get("response", ""))

    system_prompt = SYSTEM_PROMPTS.get(task_type, SYSTEM_PROMPTS["youkai_hazard"])

    # ユーザーメッセージ: instruction + input
    if isinstance(input_data, dict):
        input_text = json.dumps(input_data, ensure_ascii=False, indent=2)
    elif isinstance(input_data, str):
        input_text = input_data
    else:
        input_text = str(input_data)

    user_content = f"{instruction}\n\n{input_text}" if input_text else instruction

    # アシスタントメッセージ: output
    if isinstance(output_data, dict):
        assistant_content = json.dumps(output_data, ensure_ascii=False, indent=2)
    elif isinstance(output_data, str):
        assistant_content = output_data
    else:
        assistant_content = str(output_data)

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
        {"role": "assistant", "content": assistant_content},
    ]


def load_dataset_from_jsonl(file_path: str, tokenizer) -> Dataset:
    """JSONL → HuggingFace Dataset (テキスト形式に変換済み)"""
    records = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    # messages → chat template適用済みテキストに変換
    formatted = []
    for record in records:
        messages = format_record_to_messages(record)
        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=False
        )
        formatted.append({"text": text})

    return Dataset.from_list(formatted)


def main():
    parser = argparse.ArgumentParser(description="QLoRA Fine-tuning for Qwen2.5-14B")
    parser.add_argument("--config", required=True, help="学習設定YAMLファイル")
    parser.add_argument("--resume-from", type=str, default=None, help="チェックポイントから再開")
    args = parser.parse_args()

    config = load_train_config(args.config)

    model_cfg = config["model"]
    lora_cfg = config["lora"]
    train_cfg = config["training"]
    data_cfg = config["data"]

    print("=" * 60)
    print("QLoRA Fine-tuning: Qwen2.5-14B-Instruct")
    print(f"ベースモデル: {model_cfg['name_or_path']}")
    print(f"学習データ: {data_cfg['train_file']}")
    print(f"検証データ: {data_cfg['val_file']}")
    print(f"出力先: {train_cfg['output_dir']}")
    print("=" * 60)

    # --------------------------------------------------------
    # 1. トークナイザー
    # --------------------------------------------------------
    print("\n[1/5] トークナイザー読み込み...")
    tokenizer = AutoTokenizer.from_pretrained(
        model_cfg["name_or_path"],
        trust_remote_code=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # --------------------------------------------------------
    # 2. 量子化設定 + モデル読み込み
    # --------------------------------------------------------
    print("[2/5] モデル読み込み (4-bit量子化)...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    local_rank = int(os.environ.get("LOCAL_RANK", 0))
    device_map = {"": local_rank}

    model = AutoModelForCausalLM.from_pretrained(
        model_cfg["name_or_path"],
        quantization_config=bnb_config,
        device_map=device_map,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
        attn_implementation="flash_attention_2" if model_cfg.get("use_flash_attn", False) else "eager",
    )
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)

    # --------------------------------------------------------
    # 3. LoRA設定
    # --------------------------------------------------------
    print("[3/5] LoRAアダプター設定...")
    lora_config = LoraConfig(
        r=lora_cfg["r"],
        lora_alpha=lora_cfg["alpha"],
        target_modules=lora_cfg["target_modules"],
        lora_dropout=lora_cfg.get("dropout", 0.05),
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # --------------------------------------------------------
    # 4. データセット読み込み
    # --------------------------------------------------------
    print("[4/5] データセット読み込み...")
    train_dataset = load_dataset_from_jsonl(data_cfg["train_file"], tokenizer)
    val_dataset = load_dataset_from_jsonl(data_cfg["val_file"], tokenizer)
    print(f"  train: {len(train_dataset):,}件")
    print(f"  val:   {len(val_dataset):,}件")

    # --------------------------------------------------------
    # 5. 学習実行
    # --------------------------------------------------------
    print("[5/5] 学習開始...")

    training_args = TrainingArguments(
        output_dir=train_cfg["output_dir"],
        num_train_epochs=train_cfg["epochs"],
        per_device_train_batch_size=train_cfg["batch_size"],
        per_device_eval_batch_size=train_cfg.get("eval_batch_size", 1),
        gradient_accumulation_steps=train_cfg["gradient_accumulation"],
        learning_rate=train_cfg["learning_rate"],
        lr_scheduler_type="cosine",
        warmup_ratio=train_cfg.get("warmup_ratio", 0.03),
        weight_decay=train_cfg.get("weight_decay", 0.01),
        optim="paged_adamw_8bit",
        bf16=True,
        logging_steps=train_cfg.get("logging_steps", 10),
        eval_strategy="steps",
        eval_steps=train_cfg.get("eval_steps", 500),
        save_strategy="steps",
        save_steps=train_cfg.get("save_steps", 500),
        save_total_limit=train_cfg.get("save_total_limit", 3),
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        max_grad_norm=train_cfg.get("max_grad_norm", 1.0),
        dataloader_num_workers=train_cfg.get("num_workers", 4),
        report_to=train_cfg.get("report_to", "none"),
        run_name=train_cfg.get("run_name", "youkai-hazard-qlora"),
    )

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        tokenizer=tokenizer,
        dataset_text_field="text",
        max_seq_length=train_cfg.get("max_seq_length", 4096),
    )

    # 学習実行
    if args.resume_from:
        print(f"  チェックポイントから再開: {args.resume_from}")
        trainer.train(resume_from_checkpoint=args.resume_from)
    else:
        trainer.train()

    # --------------------------------------------------------
    # 6. 保存
    # --------------------------------------------------------
    print("\n学習完了。LoRAアダプター保存中...")
    lora_output = os.path.join(train_cfg["output_dir"], "lora_adapter")
    model.save_pretrained(lora_output)
    tokenizer.save_pretrained(lora_output)
    print(f"  保存先: {lora_output}")

    # 最終eval
    print("\n最終評価...")
    metrics = trainer.evaluate()
    print(f"  eval_loss: {metrics['eval_loss']:.4f}")
    print(f"  perplexity: {torch.exp(torch.tensor(metrics['eval_loss'])):.2f}")

    print("\n" + "=" * 60)
    print("学習完了!")
    print("=" * 60)
    print(f"\n次のステップ:")
    print(f"  1. LoRAマージ: python merge_lora.py --base {model_cfg['name_or_path']} --lora {lora_output}")
    print(f"  2. テストデータで評価")
    print(f"  3. vLLMにデプロイ")


if __name__ == "__main__":
    main()
