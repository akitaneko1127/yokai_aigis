#!/bin/bash
# サーバーへのスクリプトデプロイ
# Windows側から実行: bash deploy_to_server.sh
# または手動でSCP/rsync

# 接続情報は環境変数で設定してください
# export DEPLOY_USER=your_username
# export DEPLOY_HOST=your_server_ip
SERVER="${DEPLOY_USER:-user}@${DEPLOY_HOST:-localhost}"
REMOTE_DIR="/home/${DEPLOY_USER:-user}/youkai-hazard"

echo "=== サーバーへスクリプトをデプロイ ==="

# スクリプト転送
scp -r setup/* $SERVER:$REMOTE_DIR/scripts/setup/
scp -r generate/* $SERVER:$REMOTE_DIR/scripts/generate/
scp -r validate/* $SERVER:$REMOTE_DIR/scripts/validate/
scp -r configs/* $SERVER:$REMOTE_DIR/configs/

echo "=== デプロイ完了 ==="
echo "サーバー上で以下を実行してください:"
echo "  cd ~/youkai-hazard"
echo "  bash scripts/setup/setup_dirs.sh"
echo "  pip install aiohttp pyyaml tqdm"
echo "  python scripts/generate/generate_training_data.py --config configs/generation_config.yaml --category cat1_basic --count 10"
