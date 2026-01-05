#!/bin/bash
# make_latex_model 测试执行脚本
# 测试实例: v202601052142

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_section() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# 检查依赖
check_dependencies() {
    print_section "检查依赖"

    local missing_deps=()

    # 检查必需的命令
    command -v python3 >/dev/null 2>&1 || missing_deps+=("python3")
    command -v xelatex >/dev/null 2>&1 || missing_deps+=("xelatex")
    command -v bibtex >/dev/null 2>&1 || missing_deps+=("bibtex")

    if [ ${#missing_deps[@]} -ne 0 ]; then
        print_error "缺少依赖: ${missing_deps[*]}"
        exit 1
    fi

    # 检查可选依赖
    if command -v soffice >/dev/null 2>&1; then
        HAS_LIBREOFFICE=true
        print_success "LibreOffice 已安装（可用于生成 Word PDF 基准）"
    else
        HAS_LIBREOFFICE=false
        print_warning "LibreOffice 未安装（可选，用于生成 Word PDF 基准）"
    fi

    if command -v pdftoppm >/dev/null 2>&1; then
        HAS_PDFTOPPM=true
        print_success "pdftoppm 已安装（可用于像素对比）"
    else
        HAS_PDFTOPPM=false
        print_warning "pdftoppm 未安装（可选，用于像素对比）"
    fi

    print_success "依赖检查完成"
}

# 准备测试环境
setup_environment() {
    print_section "准备测试环境"

    # 创建必要的目录
    mkdir -p input/word_template
    mkdir -p input/project_backup
    mkdir -p output/latex_project
    mkdir -p output/artifacts
    mkdir -p output/changes
    mkdir -p expected

    # 复制 Word 模板
    if [ -f "../../../projects/NSFC_Young/template/2026年最新word模板-青年科学基金项目（C类）-正文.doc" ]; then
        cp "../../../projects/NSFC_Young/template/2026年最新word模板-青年科学基金项目（C类）-正文.doc" \
           "input/word_template/"
        print_success "Word 模板已复制"
    else
        print_error "Word 模板文件不存在"
        exit 1
    fi

    # 复制项目文件（作为测试基础）
    print_info "复制 NSFC_Young 项目到测试环境..."
    rsync -av --exclude='*.aux' --exclude='*.log' --exclude='*.out' --exclude='*.pdf' \
          "../../../projects/NSFC_Young/" "input/project_backup/" > /dev/null
    print_success "项目文件已复制"

    # 复制到输出目录（作为工作区）
    rsync -av --exclude='*.aux' --exclude='*.log' --exclude='*.out' --exclude='*.pdf' \
          "input/project_backup/" "output/latex_project/" > /dev/null
    print_success "工作区已准备"
}

# 生成 Word PDF 基准
generate_word_baseline() {
    print_section "生成 Word PDF 基准"

    if [ -f "expected/word_baseline.pdf" ]; then
        print_info "Word PDF 基准已存在，跳过生成"
        return
    fi

    if [ "$HAS_LIBREOFFICE" = true ]; then
        print_info "使用 LibreOffice 转换 Word 为 PDF..."

        soffice --headless --convert-to pdf \
                --outdir expected \
                "input/word_template/2026年最新word模板-青年科学基金项目（C类）-正文.doc" 2>/dev/null

        if [ -f "expected/2026年最新word模板-青年科学基金项目（C类）-正文.pdf" ]; then
            mv "expected/2026年最新word模板-青年科学基金项目（C类）-正文.pdf" \
               "expected/word_baseline.pdf"
            print_success "Word PDF 基准已生成"
        else
            print_warning "LibreOffice 转换失败，将继续但不生成像素对比"
        fi
    else
        print_warning "无可用工具生成 Word PDF 基准，像素对比将不可用"
        print_info "提示：安装 LibreOffice 可启用此功能：brew install --cask libreoffice"
    fi
}

# 执行 LaTeX 编译
compile_latex() {
    print_section "编译 LaTeX"

    cd output/latex_project

    print_info "第一次 XeLaTeX 编译..."
    xelatex -interaction=nonstopmode main.tex > /dev/null 2>&1

    print_info "BibTeX 编译..."
    bibtex main > /dev/null 2>&1

    print_info "第二次 XeLaTeX 编译..."
    xelatex -interaction=nonstopmode main.tex > /dev/null 2>&1

    print_info "第三次 XeLaTeX 编译..."
    xelatex -interaction=nonstopmode main.tex > /dev/null 2>&1

    cd "$SCRIPT_DIR"

    if [ -f "output/latex_project/main.pdf" ]; then
        cp output/latex_project/main.pdf output/artifacts/
        print_success "LaTeX 编译成功"
        return 0
    else
        print_error "LaTeX 编译失败"
        return 1
    fi
}

# 运行验证脚本
run_validation() {
    print_section "运行验证"

    if [ -f "validate.py" ]; then
        python3 validate.py
        print_success "验证完成"
    else
        print_warning "验证脚本不存在，跳过"
    fi
}

# 生成测试报告
generate_report() {
    print_section "生成测试报告"

    cat > REPORT.md << 'EOF'
# make_latex_model 测试报告 v202601052142

## 测试概述

- **测试ID**: v202601052142
- **测试日期**: 2026-01-05
- **技能版本**: 1.3.1
- **测试项目**: NSFC_Young
- **Word模板**: 2026年最新word模板-青年科学基金项目（C类）-正文.doc

## 测试环境

- **操作系统**: macOS (Darwin 25.2.0)
- **LaTeX引擎**: XeLaTeX
- **Python版本**: 3.x

## 测试执行结果

### 第一优先级：基础编译 (权重 40%)

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 编译无错误 | ⏳ 待测试 | - |
| 编译无警告 | ⏳ 待测试 | - |
| 跨平台兼容性 | ⏳ 待测试 | - |

**第一优先级通过率**: ⏳ 待测试

### 第二优先级：样式参数 (权重 30%)

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 页面设置 | ⏳ 待测试 | - |
| 字体字号 | ⏳ 待测试 | - |
| 行距 | ⏳ 待测试 | - |
| 颜色值 | ⏳ 待测试 | - |
| 标题格式 | ⏳ 待测试 | - |
| 列表样式 | ⏳ 待测试 | - |

**第二优先级通过率**: ⏳ 待测试

### 第三优先级：视觉相似度 (权重 20%)

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 布局相似度 | ⏳ 待测试 | - |
| 每行字数 | ⏳ 待测试 | - |
| 换行位置 | ⏳ 待测试 | - |

**第三优先级通过率**: ⏳ 待测试

### 第四优先级：像素对比 (权重 10%)

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 像素差异率 | ⏳ 待测试 | - |
| 关键区域对齐 | ⏳ 待测试 | - |

**第四优先级通过率**: ⏳ 待测试

## 综合评分

- **第一优先级**: ⏳ 待测试 / 100%
- **第二优先级**: ⏳ 待测试 / 100%
- **第三优先级**: ⏳ 待测试 / 100%
- **第四优先级**: ⏳ 待测试 / 100%

**加权总分**: ⏳ 待测试 / 100%

## 测试结论

⏳ 待测试

## 附录

### 编译日志

详见 `validation/compilation_log.txt`

### 样式检查结果

详见 `validation/style_check.json`

### 像素对比结果

详见 `validation/pixel_diff.json`

### 代码变更记录

详见 `output/changes/`

---

*此报告由自动化测试系统生成*
EOF

    print_success "测试报告已生成: REPORT.md"
}

# 清理函数
cleanup() {
    print_info "清理临时文件..."
    # 保留关键产物，清理临时文件
    find output/latex_project -name '*.aux' -delete 2>/dev/null || true
    find output/latex_project -name '*.log' -delete 2>/dev/null || true
}

# 主流程
main() {
    print_section "make_latex_model 测试 v202601052142"

    check_dependencies
    setup_environment
    generate_word_baseline
    compile_latex
    run_validation
    generate_report

    print_section "测试完成"

    print_success "测试执行完成！"
    print_info "查看测试报告: cat REPORT.md"
    print_info "查看生成的PDF: open output/artifacts/main.pdf"

    # 如果有错误，返回错误码
    if [ -f "validation/error.flag" ]; then
        exit 1
    fi
}

# 捕获退出信号
trap cleanup EXIT

# 执行主流程
main "$@"
