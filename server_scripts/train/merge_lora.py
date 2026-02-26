#!/usr/bin/env python3
"""
LoRAアダプターをベースモデルにマージして完全なモデルとして保存

使用方法:
  python merge_lora.py \
    --base /home/user/youkai-hazard/models/base/Qwen2.5-14B-Instruct \
    --lora /home/user/youkai-hazard/models/qlora_output/lora_adapter \
    --output /home/user/youkai-hazard/models/merged/youkai-hazard-14b-v1
"""

import argparse

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


def main():
    parser = argparse.ArgumentParser(description="LoRAマージ")
    parser.add_argument("--base", required=True, help="ベースモデルのパス")
    parser.add_argument("--lora", required=True, help="LoRAアダプターのパス")
    parser.add_argument("--output", required=True, help="マージ後の出力パス")
    args = parser.parse_args()

    print("=" * 60)
    print("LoRAマージ")
    print(f"ベース: {args.base}")
    print(f"LoRA:   {args.lora}")
    print(f"出力:   {args.output}")
    print("=" * 60)

    # ベースモデル読み込み（フル精度）
    print("\n[1/4] ベースモデル読み込み (bfloat16)...")
    model = AutoModelForCausalLM.from_pretrained(
        args.base,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )

    # トークナイザー
    print("[2/4] トークナイザー読み込み...")
    tokenizer = AutoTokenizer.from_pretrained(args.base, trust_remote_code=True)

    # LoRAマージ
    print("[3/4] LoRAアダプターをマージ中...")
    model = PeftModel.from_pretrained(model, args.lora)
    model = model.merge_and_unload()

    # 保存
    print("[4/4] マージ済みモデル保存中...")
    model.save_pretrained(args.output, safe_serialization=True)
    tokenizer.save_pretrained(args.output)

    print(f"\n保存完了: {args.output}")
    print("\n次のステップ:")
    print(f"  vLLMで起動: python -m vllm.entrypoints.openai.api_server --model {args.output}")


if __name__ == "__main__":
    main()
