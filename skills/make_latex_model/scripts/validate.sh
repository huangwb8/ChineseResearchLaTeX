#!/bin/bash
# ================================
# make_latex_model 验证自动化脚本（通用化版本）
# ================================
#
# 使用方法:
#   # 验证指定项目（自动检测模板）
#   ./scripts/validate.sh --project projects/NSFC_Young
#
#   # 验证指定项目并指定模板
#   ./scripts/validate.sh --project projects/MyProject --template thesis/bachelor
#
#   # 使用项目名称（自动查找项目）
#   ./scripts/validate.sh --project NSFC_Young
#
#   # 查看帮助
#   ./scripts/validate.sh --help
#

set -euo pipefail

# ================================
# 默认配置
# ================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BASE_DIR="$(cd "$SKILL_DIR/../.." && pwd)"

# 默认项目
DEFAULT_PROJECT="NSFC_Young"
DEFAULT_TEMPLATE=""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 计数器
PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

# ================================
# 解析命令行参数
# ================================
PROJECT=""
TEMPLATE=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --project)
      PROJECT="$2"
      shift 2
      ;;
    --template)
      TEMPLATE="$2"
      shift 2
      ;;
    --help|-h)
      echo "用法: $0 [OPTIONS]"
      echo ""
      echo "选项:"
      echo "  --project PATH    项目路径或名称（如 NSFC_Young 或 projects/NSFC_Young）"
      echo "  --template NAME   模板名称（如 nsfc/young，留空则自动检测）"
      echo "  --help, -h        显示帮助信息"
      echo ""
      echo "示例:"
      echo "  $0 --project NSFC_Young"
      echo "  $0 --project projects/NSFC_Young"
      echo "  $0 --project projects/MyProject --template thesis/bachelor"
      exit 0
      ;;
    *)
      echo -e "${RED}错误: 未知参数 $1${NC}"
      echo "使用 --help 查看帮助"
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
# 支持两种格式:
# 1. 项目名称: NSFC_Young -> $BASE_DIR/projects/NSFC_Young
# 2. 相对/绝对路径: projects/NSFC_Young -> 直接使用

if [[ "$PROJECT" != /* ]] && [[ "$PROJECT" != .* ]]; then
  # 不是绝对路径也不是相对路径，可能是项目名称
  if [[ "$PROJECT" != *"/"* ]]; then
    # 纯项目名称
    PROJECT_PATH="$BASE_DIR/projects/$PROJECT"
  else
    # 相对路径
    PROJECT_PATH="$BASE_DIR/$PROJECT"
  fi
else
  # 绝对路径或以 . 开头的相对路径
  PROJECT_PATH="$PROJECT"
fi

# 转换为绝对路径
PROJECT_PATH="$(cd "$PROJECT_PATH" 2>/dev/null && pwd)" || {
  echo -e "${RED}错误: 项目路径不存在: $PROJECT_PATH${NC}"
  exit 1
}

# 项目配置
CONFIG="$PROJECT_PATH/extraTex/@config.tex"
MAIN_TEX="$PROJECT_PATH/main.tex"
SKILL_MD="$SKILL_DIR/SKILL.md"
CONFIG_YAML="$SKILL_DIR/config.yaml"

# ================================
# 辅助函数
# ================================
pass() {
  echo -e "${GREEN}✅${NC} $1"
  ((PASS_COUNT++)) || true
}

warn() {
  echo -e "${YELLOW}⚠️${NC} $1"
  ((WARN_COUNT++)) || true
}

fail() {
  echo -e "${RED}❌${NC} $1"
  ((FAIL_COUNT++)) || true
}

info() {
  echo -e "${BLUE}ℹ️${NC} $1"
}

# ================================
# 开始验证
# ================================
echo "========================================="
echo "  make_latex_model 验证报告"
echo "========================================="
echo ""
echo "测试时间: $(date)"
echo "项目路径: $PROJECT_PATH"
echo "模板: ${TEMPLATE:-<自动检测>}"
echo ""

# ========================================
# 第一优先级：基础编译检查
# ========================================
echo "========================================="
echo "第一优先级：基础编译检查"
echo "========================================="
echo ""

# 检查项目目录
if [ -d "$PROJECT_PATH" ]; then
  pass "项目目录存在: $PROJECT_PATH"
else
  fail "项目目录不存在: $PROJECT_PATH"
fi

# 检查配置文件
if [ -f "$CONFIG" ]; then
  pass "配置文件存在: @config.tex"
else
  fail "配置文件不存在: @config.tex"
fi

# 检查主文件
if [ -f "$MAIN_TEX" ]; then
  pass "主文件存在: main.tex"
else
  fail "主文件不存在: main.tex"
fi

# 检查编译产物
if [ -f "$PROJECT_PATH/main.pdf" ]; then
  pass "编译成功: main.pdf 存在"

  # 获取文件大小
  PDF_SIZE=$(ls -lh "$PROJECT_PATH/main.pdf" | awk '{print $5}')
  info "PDF 文件大小: $PDF_SIZE"
else
  fail "编译失败: main.pdf 不存在"
fi

# 检查技能文档
if [ -f "$SKILL_MD" ]; then
  pass "技能文档存在: SKILL.md"

  # 检查版本号一致性
  SKILL_VERSION=$(grep "^version:" "$SKILL_MD" | head -n 1 | awk '{print $2}')
  CONFIG_VERSION=$(grep "version:" "$CONFIG_YAML" | grep -v "^#" | head -n 1 | awk '{print $2}')

  if [ "$SKILL_VERSION" = "$CONFIG_VERSION" ]; then
    pass "版本号一致: v$SKILL_VERSION"
  else
    warn "版本号不一致: SKILL.md v$SKILL_VERSION vs config.yaml v$CONFIG_VERSION"
  fi
else
  fail "技能文档不存在: SKILL.md"
fi

# ========================================
# 第二优先级：样式参数一致性
# ========================================
echo ""
echo "========================================="
echo "第二优先级：样式参数一致性"
echo "========================================="
echo ""

# 检查行距设置
if grep -q "baselinestretch.*1\.5" "$CONFIG"; then
  pass "行距设置: baselinestretch{1.5} (符合 Word 2026 模板标准)"
elif grep -q "baselinestretch" "$CONFIG"; then
  LINE_STRETCH=$(grep "baselinestretch" "$CONFIG" | sed 's/.*{\(.*\)}.*/\1/')
  warn "行距设置: baselinestretch{$LINE_STRETCH} (建议为 1.5)"
else
  fail "行距设置: 未找到 baselinestretch 定义"
fi

# 检查颜色定义
if grep -q "definecolor.*MsBlue.*RGB.*0,112,192" "$CONFIG"; then
  pass "颜色定义: MsBlue RGB 0,112,192 (正确)"
elif grep -q "definecolor.*MsBlue" "$CONFIG"; then
  MSBLUE=$(grep "definecolor.*MsBlue" "$CONFIG" | head -n 1)
  warn "颜色定义: MsBlue 值可能不正确"
  info "当前定义: $MSBLUE"
else
  fail "颜色定义: 未找到 MsBlue 定义"
fi

# 检查页面设置
if grep -q "geometry.*left=3.20cm.*right=3.14cm" "$CONFIG"; then
  pass "页面边距: 左 3.20cm, 右 3.14cm (符合 2026 模板)"
elif grep -q "geometry.*left=.*right=" "$CONFIG"; then
  warn "页面边距: 可能与 2026 模板不完全一致"
  info "当前设置: $(grep "geometry" "$CONFIG" | head -n 1)"
else
  warn "页面边距: 未找到明确的 geometry 设置"
fi

# 检查标题格式
if grep -q "titleformat.*section.*hspace.*1.45em" "$CONFIG"; then
  pass "Section 标题缩进: 1.45em (符合 2026 模板)"
elif grep -q "titleformat.*section" "$CONFIG"; then
  info "Section 标题缩进: 需人工检查"
else
  warn "Section 标题格式: 未找到 titleformat 定义"
fi

# ⚠️ 检查标题文字一致性
echo ""
echo "----------------------------------------"
echo "标题文字一致性检查"
echo "----------------------------------------"

# 检查 Python 和 compare_headings.py 是否可用
if command -v python3 &> /dev/null && [ -f "$SCRIPT_DIR/compare_headings.py" ]; then
  # 查找 Word 模板文件
  WORD_TEMPLATE=$(find "$PROJECT_PATH/template" -name "*.docx" 2>/dev/null | head -n 1)

  if [ -n "$WORD_TEMPLATE" ]; then
    info "正在对比标题文字..."
    info "Word 模板: $WORD_TEMPLATE"
    info "LaTeX 文件: $MAIN_TEX"

    # 运行对比脚本
    COMPARE_OUTPUT=$(python3 "$SCRIPT_DIR/compare_headings.py" "$WORD_TEMPLATE" "$MAIN_TEX" 2>&1)
    COMPARE_EXIT_CODE=$?

    if [ $COMPARE_EXIT_CODE -eq 0 ]; then
      # 提取统计信息
      MATCHED=$(echo "$COMPARE_OUTPUT" | grep "完全匹配:" | grep -oE "[0-9]+" || echo "0")
      DIFFERENCES=$(echo "$COMPARE_OUTPUT" | grep "有差异:" | grep -oE "[0-9]+" || echo "0")
      ONLY=$(echo "$COMPARE_OUTPUT" | grep "仅在一方:" | grep -oE "[0-9]+" || echo "0")

      if [ "$DIFFERENCES" -eq 0 ] && [ "$ONLY" -eq 0 ]; then
        pass "标题文字完全匹配 ($MATCHED 个)"
      else
        warn "标题文字存在差异: 匹配 $MATCHED | 差异 $DIFFERENCES | 仅在一方 $ONLY"
        info "详细报告: python3 $SCRIPT_DIR/compare_headings.py $WORD_TEMPLATE $MAIN_TEX --report heading_report.html"
      fi
    else
      warn "标题对比失败: $COMPARE_OUTPUT"
      info "请手动检查标题文字是否与 Word 模板一致"
    fi
  else
    warn "未找到 Word 模板文件 (.docx)，跳过标题文字自动对比"
    info "请手动检查 main.tex 中的标题文字是否与 Word 模板一致"
  fi
else
  warn "未安装 python3 或 compare_headings.py 不可用，跳过标题文字自动对比"
  info "安装 python-docx: pip install python-docx"
  info "请手动检查标题文字是否与 Word 模板一致"
fi


# ========================================
# 第三优先级：视觉相似度
# ========================================
echo ""
echo "========================================="
echo "第三优先级：视觉相似度"
echo "========================================="
echo ""

info "视觉相似度检查需要人工对比 PDF 与 Word 模板"
echo ""
echo "建议步骤:"
echo "  1. 在 Microsoft Word 中打开 2026 年模板"
echo "  2. 导出为 PDF (不能使用 QuickLook)"
echo "  3. 对比 LaTeX 生成的 PDF 与 Word PDF"
echo "  4. 检查每行字数、换行位置是否一致"

# ========================================
# 第四优先级：像素对比
# ========================================
echo ""
echo "========================================="
echo "第四优先级：像素对比"
echo "========================================="
echo ""

info "像素对比仅当使用 Word 打印 PDF 基准时才有意义"
echo ""
echo "如需进行像素对比:"
echo "  1. 准备 Word 打印 PDF 基准"
echo "     详见: docs/BASELINE_GUIDE.md"
echo "  2. 将 PDF 转换为 PNG (pdftoppm)"
echo "  3. 运行像素对比脚本"
echo ""
echo "快速生成基准:"
echo "  使用 LibreOffice: soffice --headless --convert-to pdf --outdir baseline template.doc"
echo ""
warn "如使用 QuickLook 基准,像素对比指标会失真,不建议进行"

# ========================================
# 总结
# ========================================
echo ""
echo "========================================="
echo "验证总结"
echo "========================================="
echo ""

TOTAL_CHECKS=$((PASS_COUNT + WARN_COUNT + FAIL_COUNT))

echo "总检查项: $TOTAL_CHECKS"
echo -e "  ${GREEN}通过: $PASS_COUNT${NC}"
echo -e "  ${YELLOW}警告: $WARN_COUNT${NC}"
echo -e "  ${RED}失败: $FAIL_COUNT${NC}"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
  echo -e "${GREEN}✅ 所有核心检查通过！${NC}"
  if [ $WARN_COUNT -gt 0 ]; then
    echo -e "${YELLOW}⚠️  但有 $WARN_COUNT 个警告需要注意${NC}"
  fi
else
  echo -e "${RED}❌ 有 $FAIL_COUNT 个检查失败，需要修复${NC}"
fi

echo ""
echo "验证完成时间: $(date)"
echo "========================================="

# 返回状态码
if [ $FAIL_COUNT -gt 0 ]; then
  exit 1
else
  exit 0
fi
