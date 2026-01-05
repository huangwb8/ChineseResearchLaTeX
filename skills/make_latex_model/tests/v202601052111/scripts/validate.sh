#!/bin/bash
# ================================
# make_latex_model 验证自动化脚本
# ================================

# 不使用 set -e,手动控制错误处理

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BASE_DIR="$(cd "$SKILL_DIR/../.." && pwd)"
PROJECT="$BASE_DIR/projects/NSFC_Young"
CONFIG="$PROJECT/extraTex/@config.tex"
SKILL_MD="$SKILL_DIR/SKILL.md"
CONFIG_YAML="$SKILL_DIR/config.yaml"

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

# 辅助函数
pass() {
  echo -e "${GREEN}✅${NC} $1"
  ((PASS_COUNT++))
}

warn() {
  echo -e "${YELLOW}⚠️${NC} $1"
  ((WARN_COUNT++))
}

fail() {
  echo -e "${RED}❌${NC} $1"
  ((FAIL_COUNT++))
}

info() {
  echo -e "${BLUE}ℹ️${NC} $1"
}

# 开始验证
echo "========================================="
echo "  make_latex_model 验证报告"
echo "========================================="
echo ""
echo "测试时间: $(date)"
echo "项目路径: $PROJECT"
echo ""

# ========================================
# 第一优先级：基础编译检查
# ========================================
echo "========================================="
echo "第一优先级：基础编译检查"
echo "========================================="
echo ""

# 检查项目目录
if [ -d "$PROJECT" ]; then
  pass "项目目录存在: $PROJECT"
else
  fail "项目目录不存在: $PROJECT"
fi

# 检查配置文件
if [ -f "$CONFIG" ]; then
  pass "配置文件存在: @config.tex"
else
  fail "配置文件不存在: @config.tex"
fi

# 检查编译产物
if [ -f "$PROJECT/main.pdf" ]; then
  pass "编译成功: main.pdf 存在"

  # 获取文件大小
  PDF_SIZE=$(ls -lh "$PROJECT/main.pdf" | awk '{print $5}')
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
if grep -q "\\renewcommand{\\baselinestretch}{1.0}" "$CONFIG"; then
  pass "行距设置: baselinestretch{1.0} (符合 v1.2.0 标准)"
elif grep -q "\\renewcommand{\\baselinestretch}" "$CONFIG"; then
  LINE_STRETCH=$(grep "\\renewcommand{\\baselinestretch}" "$CONFIG" | sed 's/.*{\(.*\)}.*/\1/')
  warn "行距设置: baselinestretch{$LINE_STRETCH} (建议为 1.0)"
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
echo "  2. 将 PDF 转换为 PNG (pdftoppm)"
echo "  3. 运行像素对比脚本"
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
