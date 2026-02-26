#!/bin/bash
# サーバー側ディレクトリ構成の作成
# 実行: bash ~/youkai-hazard/scripts/setup/setup_dirs.sh

set -e

BASE_DIR="$HOME/youkai-hazard"

echo "=== ディレクトリ構成作成 ==="

# スクリプト
mkdir -p $BASE_DIR/scripts/{setup,generate,validate,train,deploy,continuous,utils}

# データ
mkdir -p $BASE_DIR/data/{raw,cleaned,train,eval,test}
mkdir -p $BASE_DIR/data/external/monuments/{by_type,raw}

# モデル
mkdir -p $BASE_DIR/models/{base,trained,serving}

# プロンプト・設定・ログ・結果
mkdir -p $BASE_DIR/{prompts,configs,logs,results}

echo "=== 構成確認 ==="
find $BASE_DIR -type d | sort | head -40

echo "=== 完了 ==="
