#!/bin/bash
# ============================================
# 一键启动脚本（uv 管理 Python 环境）
# 会自动：同步后端依赖 → 启动后端 → 启动前端 → 打开浏览器
# ============================================
set -e
cd "$(dirname "$0")"

echo "======================================"

# ---------- 1. 检查 uv ----------
if ! command -v uv >/dev/null 2>&1; then
  echo "❌ 未找到 uv，请先安装：brew install uv"
  exit 1
fi
echo "[1/4] uv 已就绪：$(uv --version)"

# ---------- 2. 检查 API Key 配置 ----------
if [ ! -f backend/.env ]; then
  echo ""
  echo "❌ 未找到 backend/.env 配置文件"
  echo "   请执行：cp backend/.env.example backend/.env"
  echo "   然后编辑 backend/.env，填入你的 OPENAI_API_KEY"
  echo ""
  exit 1
fi

if ! grep -q "OPENAI_API_KEY=." backend/.env; then
  echo ""
  echo "❌ backend/.env 中的 OPENAI_API_KEY 为空"
  echo "   请编辑 backend/.env，填入你的 API Key"
  echo ""
  exit 1
fi
echo "[2/4] API Key 配置已就绪"

# ---------- 3. 同步后端依赖（以 uv.lock 为准，幂等且很快） ----------
if [ ! -d backend/.venv ]; then
  echo "[3/4] 首次运行，正在创建 venv 并安装后端依赖..."
else
  echo "[3/4] 正在同步后端依赖..."
fi
(cd backend && uv sync --quiet)
echo "       Python: $(cd backend && uv run python -V | cut -d' ' -f2)"

# ---------- 4. 安装前端依赖 ----------
if [ ! -d frontend/node_modules ]; then
  echo "[4/4] 首次运行，正在安装前端依赖（需要几分钟）..."
  (cd frontend && npm install)
else
  echo "[4/4] 前端依赖已就绪"
fi

# ---------- 启动服务 ----------
echo ""
echo "  后端地址: http://localhost:8000"
echo "  接口文档地址: http://localhost:8000/docs"
echo "  前端页面: http://localhost:5173"
echo "  按 Ctrl+C 可停止所有服务"
echo ""

(cd backend && uv run python -m uvicorn app.main:app --port 8000) &
BACKEND_PID=$!
trap "kill $BACKEND_PID 2>/dev/null" EXIT

# 稍后自动打开浏览器
(sleep 3 && open http://localhost:5173) &

# 前台启动前端（Ctrl+C 一起退出）
cd frontend && npm run dev
