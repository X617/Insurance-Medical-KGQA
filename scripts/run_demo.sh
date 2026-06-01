#!/usr/bin/env bash
set -euo pipefail

# 用法：
#   bash scripts/run_demo.sh
#
# 首次运行前：
#   1. cp .env.example .env
#   2. 修改 .env 里的 NEO4J_PASSWORD 和 DEEPSEEK_API_KEY
#   3. 确保 Neo4j 已启动，并且里面已经导入图谱数据
#
# 如需启动前重新导入 DataCleaned 下的结构化数据：
#   RUN_IMPORT=1 bash scripts/run_demo.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-8501}"

find_free_port() {
  python - "$1" "$2" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])

while True:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((host, port))
    except OSError:
        port += 1
    else:
        sock.close()
        print(port)
        break
    finally:
        sock.close()
PY
}

if [ ! -d ".venv" ]; then
  "$PYTHON_BIN" -m venv .venv
fi

source .venv/bin/activate
python -m pip install -r requirements.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "已生成 .env。当前会继续启动 demo，但完整问答需要先填写 NEO4J_PASSWORD 和 DEEPSEEK_API_KEY。"
fi

set -a
source .env
set +a

REQUESTED_BACKEND_PORT="$BACKEND_PORT"
REQUESTED_FRONTEND_PORT="$FRONTEND_PORT"
BACKEND_PORT="$(find_free_port "$BACKEND_HOST" "$BACKEND_PORT")"
FRONTEND_PORT="$(find_free_port "$FRONTEND_HOST" "$FRONTEND_PORT")"

if [ "$BACKEND_PORT" != "$REQUESTED_BACKEND_PORT" ]; then
  echo "端口 ${REQUESTED_BACKEND_PORT} 已被占用，后端自动改用 ${BACKEND_PORT}。"
fi
if [ "$FRONTEND_PORT" != "$REQUESTED_FRONTEND_PORT" ]; then
  echo "端口 ${REQUESTED_FRONTEND_PORT} 已被占用，前端自动改用 ${FRONTEND_PORT}。"
fi

export API_URL="http://${BACKEND_HOST}:${BACKEND_PORT}/chat"
export BACKEND_URL="http://${BACKEND_HOST}:${BACKEND_PORT}"

if [ "${NEO4J_PASSWORD:-}" = "your_neo4j_password" ] || [ "${DEEPSEEK_API_KEY:-}" = "sk-your-key" ]; then
  echo "注意：.env 仍包含模板占位值。页面可以启动，但完整问答需要填写真实 Neo4j 密码和 DeepSeek API Key。"
fi

if [ "${RUN_IMPORT:-0}" = "1" ]; then
  python -m src.kg_construction.neo4j_loader
fi

cleanup() {
  if [ -n "${BACKEND_PID:-}" ]; then
    kill "$BACKEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

python -m uvicorn src.api.main:app \
  --host "$BACKEND_HOST" \
  --port "$BACKEND_PORT" &
BACKEND_PID=$!

echo "后端 API: http://${BACKEND_HOST}:${BACKEND_PORT}/docs"
echo "前端页面: http://${FRONTEND_HOST}:${FRONTEND_PORT}"
echo "请打开前端页面使用聊天功能；8000 是后端接口端口，不是前端页面。"

python -m streamlit run frontend/streamlit_app.py \
  --server.headless true \
  --server.address "$FRONTEND_HOST" \
  --server.port "$FRONTEND_PORT" \
  --browser.gatherUsageStats false
