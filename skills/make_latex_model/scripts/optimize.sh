#!/bin/bash
# ================================
# make_latex_model 一键式优化脚本
# ================================
#
# 使用方法:
#   ./scripts/optimize.sh --project NSFC_Young
#   ./scripts/optimize.sh --project NSFC_Young --interactive
#   ./scripts/optimize.sh --project NSFC_Young --report report.html
#

set -euo pipefail

# ================================
# 默认配置
# ================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BASE_DIR="$(cd "$SKILL_DIR/../.." && pwd)"

DEFAULT_PROJECT="NSFC_Young"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# ================================
# 解析命令行参数
# ================================
PROJECT=""
INTERACTIVE=""
REPORT=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --project)
      PROJECT="$2"
      shift 2
      ;;
    --interactive|-i)
      INTERACTIVE="--interactive"
      shift
      ;;
    --report)
      REPORT="--report $2"
      shift 2
      ;;
    --help|-h)
      echo "用法: $0 [OPTIONS]"
      echo ""
      echo "选项:"
      echo "  --project PATH      项目路径或名称"
      echo "  --interactive, -i   交互模式"
      echo "  --report PATH       生成报告文件"
      echo "  --help, -h          显示帮助"
      echo ""
      echo "示例:"
      echo "  $0 --project NSFC_Young"
      echo "  $0 --project NSFC_Young --interactive"
      exit 0
      ;;
    *)
      echo -e "${RED}错误: 未知参数 $1${NC}"
      exit 1
      ;;
  esac
done

# 如果未指定项目，使用默认项目
if [ -z "$PROJECT" ]; then
  PROJECT="$DEFAULT_PROJECT"
fi

# ================================
# 解析项目路径
# ================================
if [[ "$PROJECT" != /* ]] && [[ "$PROJECT" != .* ]]; then
  if [[ "$PROJECT" != *"/"* ]]; then
    PROJECT_PATH="$BASE_DIR/projects/$PROJECT"
  else
    PROJECT_PATH="$BASE_DIR/$PROJECT"
  fi
else
  PROJECT_PATH="$PROJECT"
fi

PROJECT_PATH="$(cd "$PROJECT_PATH" 2>/dev/null && pwd)" || {
  echo -e "${RED}错误: 项目路径不存在: $PROJECT_PATH${NC}"
  exit 1
}

# ================================
# 检查 Python 脚本
# ================================
PYTHON_SCRIPT="$SCRIPT_DIR/optimize.py"

if [ ! -f "$PYTHON_SCRIPT" ]; then
  echo -e "${RED}错误: Python 脚本不存在: $PYTHON_SCRIPT${NC}"
  exit 1
fi

# ================================
# 运行优化脚本
# ================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  LaTeX 模板一键优化${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "项目: $PROJECT_PATH"
echo "模式: ${INTERACTIVE:-自动}"
echo ""

python3 "$PYTHON_SCRIPT" --project "$PROJECT_PATH" $INTERACTIVE $REPORT

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  优化完成${NC}"
echo -e "${GREEN}========================================${NC}"
