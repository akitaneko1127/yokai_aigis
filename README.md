# 妖怪ハザードマップ

土地の災害リスクを、妖怪たちが優しく教えてくれるWebアプリケーションです。
Qwen2.5-14B-Instruct をベースに QLoRA で学習した独自AIモデルと、VOICEVOX による音声読み上げを搭載しています。

## 妖怪キャラクター

| 妖怪 | 担当災害 | 特徴 |
|------|----------|------|
| 河童 | 水害（洪水・津波・高潮） | 親しみやすい、お調子者 |
| 大ナマズ | 地震（液状化・盛土崩壊） | 落ち着いていて頼りがいがある |
| 土蜘蛛 | 土砂災害 | 物静かで思慮深い |
| 天狗 | 暴風・竜巻 | 誇り高く正義感が強い |
| 火車 | 火災・風害 | 気まぐれだが情に厚い |
| 雪女 | 雪害 | 穏やかで面倒見がいい |
| ヒノカグツチ | 火山災害 | 威厳があり寛大 |

## 機能

- **地図クリックでリスク分析** - 任意の地点をクリックするだけで災害リスクを分析
- **リスクスコア表示** - 各災害種別のリスクを視覚的に表示
- **妖怪からのメッセージ** - LLMが生成する妖怪キャラクターの会話をゆっくり劇場風UIで表示
- **音声読み上げ（TTS）** - VOICEVOXによるキャラクター別の音声合成
- **おすすめの備え** - 具体的な対策を提案
- **歴史的土地利用分析** - 過去の土地利用変遷に基づくリスク分析
- **自然災害伝承碑** - 近隣の災害伝承碑情報を表示
- **避難所情報** - 指定緊急避難場所を距離順に表示

## 必要環境

- Python 3.10+
- Node.js 18+
- vLLM等の推論サーバー（LLM応答を使う場合、無効時はテンプレート応答）
- VOICEVOX Engine（音声合成を使う場合）

## セットアップ

### 1. バックエンド

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# .env を編集してAPIキーを設定
```

### 2. フロントエンド

```bash
cd frontend
npm install
```

### 3. VOICEVOX（任意）

```powershell
# PowerShellで実行（自動ダウンロード・展開）
.\scripts\setup-voicevox.ps1
```

または [VOICEVOX公式サイト](https://voicevox.hiroshiba.jp/) から手動インストール。

### 4. 環境変数

`backend/.env.example` を `backend/.env` にコピーし、以下を設定:

| 変数 | 説明 | デフォルト |
|------|------|-----------|
| `REINFOLIB_API_KEY` | 不動産情報ライブラリAPIキー（必須） | - |
| `LLM_ENABLED` | LLM推論の有効化 | `true` |
| `LLM_API_URL` | 推論サーバーURL | `http://localhost:8001/v1` |
| `LLM_MODEL_NAME` | モデル名（空欄で自動検出） | 自動検出 |
| `LLM_TIMEOUT` | LLMリクエストタイムアウト（秒） | `120` |
| `LLM_MAX_TOKENS_YOUKAI` | 妖怪応答の最大トークン数 | `2048` |
| `LLM_MAX_TOKENS_DEFAULT` | デフォルト最大トークン数 | `512` |
| `LLM_TEMPERATURE` | 生成温度 | `0.3` |
| `TTS_ENABLED` | 音声合成の有効化 | `true` |
| `TTS_API_URL` | VOICEVOX APIのURL | `http://localhost:50021` |
| `TTS_TIMEOUT` | TTSリクエストタイムアウト（秒） | `30` |
| `TTS_CACHE_MAX_SIZE` | TTS音声キャッシュ上限数 | `100` |

## 起動方法

```bash
# ターミナル1: バックエンド（ポート8000）
cd backend
uvicorn app.main:app --reload --port 8000

# ターミナル2: フロントエンド（ポート5173）
cd frontend
npm run dev

# ターミナル3: VOICEVOX（任意）
.\scripts\start-voicevox.ps1
```

- **フロントエンド**: http://localhost:5173
- **バックエンドAPI**: http://localhost:8000/docs

## API

| メソッド | エンドポイント | 説明 |
|----------|---------------|------|
| `POST` | `/api/hazard/analyze` | 位置のハザード分析 |
| `POST` | `/api/hazard/synthesize` | テキスト音声合成（TTS） |
| `GET` | `/api/hazard/health` | ヘルスチェック |
| `GET` | `/api/youkai/list` | 妖怪一覧 |

リクエスト例:
```json
POST /api/hazard/analyze
{
  "lat": 35.6812,
  "lng": 139.7671,
  "address": "東京都千代田区"
}
```

## AIモデル

Qwen2.5-14B-Instruct をベースに、142,000件の教師データでQLoRA学習したモデルです。

| 項目 | 値 |
|------|-----|
| ベースモデル | Qwen/Qwen2.5-14B-Instruct |
| 学習手法 | QLoRA (r=64, alpha=128) |
| 教師データ | 142,000件（12カテゴリ） |
| eval_loss | 0.312 |
| JSON成功率 | 99.97% |

### GGUF量子化モデル

| 量子化 | サイズ | 用途 |
|--------|--------|------|
| Q4_K_M | 8.4GB | 推奨（GPU 10GB+） |
| Q3_K_M | 6.9GB | メモリ節約版 |
| IQ3_XS | 6.0GB | 最小版（VPS等） |

### モデルの再構築

```bash
# 1. ベースモデルのダウンロード
huggingface-cli download Qwen/Qwen2.5-14B-Instruct --local-dir ./models/base/Qwen2.5-14B-Instruct

# 2. LoRAアダプターのマージ
python server_scripts/train/merge_lora.py \
  --base ./models/base/Qwen2.5-14B-Instruct \
  --lora ./lora_adapter \
  --output ./models/merged/youkai-hazard-14b-v1

# 3. GGUF変換（llama.cpp使用）
python llama.cpp/convert_hf_to_gguf.py ./models/merged/youkai-hazard-14b-v1 --outtype f16
llama.cpp/build/bin/llama-quantize youkai-hazard-14b-v1-f16.gguf youkai-hazard-14b-v1-q4_k_m.gguf Q4_K_M
```

## プロジェクト構成

```
youkaigis/
├── backend/                 # FastAPI バックエンド
│   ├── app/
│   │   ├── models/         # データモデル
│   │   ├── routers/        # APIルーター
│   │   ├── schemas/        # Pydanticスキーマ
│   │   └── services/       # LLM・TTS・APIクライアント
│   └── .env.example
├── frontend/                # React フロントエンド
│   ├── public/images/      # 妖怪キャラクター画像
│   └── src/
│       ├── components/     # UIコンポーネント
│       ├── data/           # 静的データ
│       ├── services/       # APIクライアント
│       └── types/          # TypeScript型定義
├── scripts/                 # VOICEVOX セットアップ・起動
├── server_scripts/          # AI学習・評価スクリプト
│   ├── generate/           # 教師データ生成
│   ├── train/              # QLoRA学習・マージ
│   ├── evaluate/           # モデル評価
│   ├── prepare/            # データ前処理
│   └── configs/            # 学習設定
└── 20260129_GeoJSON/        # 災害リスクGeoJSONデータ
```

## 技術スタック

| レイヤー | 技術 |
|----------|------|
| フロントエンド | React 18, TypeScript, Vite, Leaflet |
| バックエンド | Python 3.10+, FastAPI, httpx |
| AI推論 | vLLM |
| AI学習 | transformers, PEFT (QLoRA), llama.cpp |
| 音声合成 | VOICEVOX Engine |

## データ出典

- [国土交通省 不動産情報ライブラリ](https://www.reinfolib.mlit.go.jp/)
- [国土地理院 自然災害伝承碑](https://www.gsi.go.jp/bousaichiri/denshouhi.html)
- [国土地理院 GeoJSON データ](https://www.gsi.go.jp/)

## 謝辞

本プロジェクトのAIモデル学習（教師データ生成・QLoRA学習・評価）は、**ローカルLLMに向き合う会**の**inai17ibar**様よりGPU環境をお借りして実施しました。

- **inai17ibar** 様 - GPU環境の提供およびサポート
- **サルドラ** 様 - GPU環境利用の仲介およびサポート

## ライセンス

Apache License 2.0
