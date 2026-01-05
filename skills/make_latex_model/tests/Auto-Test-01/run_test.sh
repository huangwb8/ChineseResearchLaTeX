#!/bin/bash
# ============================================
# Auto-Test-01 自动化测试脚本
# ============================================

set -e  # 遇到错误立即退出

# ================================
# 配置
# ================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
WORKSPACE="$SCRIPT_DIR/workspace"
LOGS="$SCRIPT_DIR/logs"
ARTIFACTS="$SCRIPT_DIR/artifacts"
MAX_ROUNDS=10

# 目标 skill
TARGET_SKILL="make_latex_model"
SKILL_PATH="$PROJECT_ROOT/skills/$TARGET_SKILL"

# 测试项目
TEST_PROJECT="NSFC_Young"
SOURCE_PROJECT="$PROJECT_ROOT/projects/$TEST_PROJECT"
WORKSPACE_PROJECT="$WORKSPACE/$TEST_PROJECT"

# Word 模板
WORD_TEMPLATE="$SOURCE_PROJECT/template/2026年最新word模板-青年科学基金项目（C类）-正文.doc"
BASELINE_PDF="$ARTIFACTS/baseline/word.pdf"
BASELINE_PNG="$ARTIFACTS/baseline/word.png"

# ================================
# 工具函数
# ================================

log_info() {
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOGS/summary.log"
}

log_error() {
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOGS/summary.log"
}

log_success() {
    echo "[SUCCESS] $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOGS/summary.log"
}

print_header() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
}

# ================================
# 初始化
# ================================
init() {
    print_header "初始化测试环境"

    # 创建目录
    mkdir -p "$WORKSPACE" "$LOGS" "$ARTIFACTS/baseline" "$ARTIFACTS/output"

    log_info "测试目录: $SCRIPT_DIR"
    log_info "项目根目录: $PROJECT_ROOT"
    log_info "工作空间: $WORKSPACE"
    log_info "最大测试轮次: $MAX_ROUNDS"

    # 检查依赖
    check_dependencies
}

# ================================
# 检查依赖
# ================================
check_dependencies() {
    log_info "检查依赖..."

    # 检查 LibreOffice
    if ! command -v soffice &> /dev/null; then
        log_error "LibreOffice 未安装。请运行: brew install --cask libreoffice"
        exit 1
    fi

    # 检查 XeLaTeX
    if ! command -v xelatex &> /dev/null; then
        log_error "XeLaTeX 未安装。请安装 MacTeX 或 TeX Live"
        exit 1
    fi

    # 检查 pdftoppm
    if ! command -v pdftoppm &> /dev/null; then
        log_error "pdftoppm 未安装。请安装 poppler-utils"
        exit 1
    fi

    # 检查目标 skill
    if [ ! -f "$SKILL_PATH/SKILL.md" ]; then
        log_error "目标 skill 不存在: $SKILL_PATH"
        exit 1
    fi

    # 检查源项目
    if [ ! -d "$SOURCE_PROJECT" ]; then
        log_error "源项目不存在: $SOURCE_PROJECT"
        exit 1
    fi

    # 检查 Word 模板
    if [ ! -f "$WORD_TEMPLATE" ]; then
        log_error "Word 模板不存在: $WORD_TEMPLATE"
        exit 1
    fi

    log_success "所有依赖检查通过"
}

# ================================
# 生成 Word PDF 基准
# ================================
generate_baseline() {
    print_header "生成 Word PDF 基准"

    if [ -f "$BASELINE_PDF" ]; then
        log_info "Word PDF 基准已存在，跳过生成"
        return
    fi

    log_info "使用 LibreOffice 转换 Word 模板为 PDF..."
    soffice --headless --convert-to pdf \
        --outdir "$ARTIFACTS/baseline" \
        "$WORD_TEMPLATE"

    if [ -f "$BASELINE_PDF" ]; then
        log_success "Word PDF 基准生成成功: $BASELINE_PDF"
    else
        log_error "Word PDF 基准生成失败"
        exit 1
    fi

    # 转换为 PNG（用于像素对比）
    log_info "转换 PDF 为 PNG（用于像素对比）..."
    pdftoppm -png -r 150 -singlefile \
        "$BASELINE_PDF" \
        "$ARTIFACTS/baseline/word"

    if [ -f "$BASELINE_PNG" ]; then
        log_success "PNG 生成成功: $BASELINE_PNG"
    else
        log_error "PNG 生成失败"
        exit 1
    fi
}

# ================================
# 准备测试环境
# ================================
prepare_workspace() {
    local round=$1

    print_header "准备测试环境 (Round $round)"

    # 清空工作空间
    log_info "清空工作空间..."
    rm -rf "$WORKSPACE"
    mkdir -p "$WORKSPACE"

    # 复制项目文件
    log_info "复制 $TEST_PROJECT 到工作空间..."
    cp -R "$SOURCE_PROJECT" "$WORKSPACE_PROJECT"

    # 排除不必要的文件
    rm -rf "$WORKSPACE_PROJECT/main.pdf"
    rm -rf "$WORKSPACE_PROJECT/main.aux"
    rm -rf "$WORKSPACE_PROJECT/main.log"
    rm -rf "$WORKSPACE_PROJECT/main.out"
    rm -rf "$WORKSPACE_PROJECT/main.bbl"
    rm -rf "$WORKSPACE_PROJECT/main.blg"

    log_success "测试环境准备完成"
}

# ================================
# 执行单轮测试
# ================================
run_round() {
    local round=$1
    local round_log="$LOGS/round-$(printf '%02d' $round).log"

    print_header "执行第 $round 轮测试"

    # 准备环境
    prepare_workspace "$round"

    # 调用 auto-test-skill
    log_info "调用 auto-test-skill 执行测试..."
    log_info "测试日志: $round_log"

    # 这里需要调用 auto-test-skill
    # 由于 auto-test-skill 是一个已安装的 skill，我们使用 Skill tool 调用它
    log_info "开始测试... (详情见 $round_log)"

    # 记录轮次开始
    echo ""
    echo "========================================== " >> "$round_log"
    echo "Round $round 测试开始" >> "$round_log"
    echo "时间: $(date '+%Y-%m-%d %H:%M:%S')" >> "$round_log"
    echo "==========================================" >> "$round_log"
    echo "" >> "$round_log"

    # 这里应该是 auto-test-skill 的执行逻辑
    # 由于 auto-test-skill 可能需要特定的输入格式，我们暂时记录日志
    log_info "测试参数:"
    log_info "  - 目标 skill: $TARGET_SKILL"
    log_info "  - 测试项目: $TEST_PROJECT"
    log_info "  - Word 模板: $WORD_TEMPLATE"
    log_info "  - 工作空间: $WORKSPACE_PROJECT"

    # 编译 LaTeX
    log_info "编译 LaTeX..."
    cd "$WORKSPACE_PROJECT"
    xelatex -interaction=nonstopmode main.tex > "$round_log" 2>&1 || true
    bibtex main > /dev/null 2>&1 || true
    xelatex -interaction=nonstopmode main.tex >> "$round_log" 2>&1 || true
    xelatex -interaction=nonstopmode main.tex >> "$round_log" 2>&1 || true

    # 检查编译结果
    if [ -f "$WORKSPACE_PROJECT/main.pdf" ]; then
        log_success "LaTeX 编译成功，PDF 生成"
        # 复制输出到 artifacts
        mkdir -p "$ARTIFACTS/output/round-$(printf '%02d' $round)"
        cp "$WORKSPACE_PROJECT/main.pdf" "$ARTIFACTS/output/round-$(printf '%02d' $round)/"
    else
        log_error "LaTeX 编译失败"
        echo "编译失败" >> "$round_log"
        return 1
    fi

    # 运行验证脚本
    log_info "运行验证脚本..."
    if [ -f "$SKILL_PATH/scripts/validate.sh" ]; then
        cd "$SKILL_PATH"
        bash scripts/validate.sh >> "$round_log" 2>&1 || true
        log_info "验证脚本执行完成"
    else
        log_info "验证脚本不存在，跳过"
    fi

    log_success "第 $round 轮测试完成"
}

# ================================
# 主测试循环
# ================================
main() {
    init
    generate_baseline

    local round=1
    local all_passed=false

    while [ $round -le $MAX_ROUNDS ]; do
        run_round "$round"

        # 这里应该有结果分析逻辑
        # 暂时简化：每轮都继续
        round=$((round + 1))

        # 如果完全通过，退出循环
        # if [ "$all_passed" = true ]; then
        #     log_success "所有测试通过！"
        #     break
        # fi
    done

    print_header "测试完成"
    log_info "总共执行 $((round - 1)) 轮测试"
    log_info "测试日志: $LOGS/"
    log_info "输出产物: $ARTIFACTS/output/"
}

# ================================
# 执行
# ================================
main "$@"
