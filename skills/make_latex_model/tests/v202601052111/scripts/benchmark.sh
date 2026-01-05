#!/bin/bash
# ================================
# make_latex_model 性能基准测试脚本
# ================================

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BASE_DIR="$(cd "$SKILL_DIR/../.." && pwd)"
PROJECT="$BASE_DIR/projects/NSFC_Young"
TIMES=3
OUTPUT_DIR="$SCRIPT_DIR/../output"
OUTPUT_FILE="$OUTPUT_DIR/benchmark_results.json"

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

# 开始测试
echo "=== make_latex_model 性能基准测试 ==="
echo "测试时间: $(date)"
echo "测试次数: $TIMES"
echo ""

# 保存当前目录
CURRENT_DIR=$(pwd)

# 检查项目是否存在
if [ ! -d "$PROJECT" ]; then
  echo "❌ 错误: 项目目录不存在: $PROJECT"
  exit 1
fi

cd "$PROJECT"

# 清理临时文件
rm -f main.aux main.log main.out main.bbl main.blg

# 编译时间测试
echo "📊 编译性能测试..."

TOTAL_TIME=0
for i in $(seq 1 $TIMES); do
  echo "  [测试 $i/$TIMES] 编译 main.tex..."

  # 测量编译时间（毫秒）
  START=$(python3 -c "import time; print(int(time.time() * 1000))")
  xelatex -interaction=nonstopmode main.tex > /dev/null 2>&1
  END=$(python3 -c "import time; print(int(time.time() * 1000))")

  DURATION=$((END - START))
  TOTAL_TIME=$((TOTAL_TIME + DURATION))

  # 转换为秒
  DURATION_SEC=$(awk "BEGIN {printf \"%.2f\", $DURATION/1000}")
  echo "    ⏱️  耗时: ${DURATION_SEC} 秒"
done

# 计算平均时间
AVG_TIME=$((TOTAL_TIME / TIMES))
AVG_TIME_SEC=$(awk "BEGIN {printf \"%.2f\", $AVG_TIME/1000}")
echo ""
echo "📈 平均编译时间: ${AVG_TIME_SEC} 秒"

# 检查 PDF 文件大小
PDF_SIZE=$(ls -l "$PROJECT/main.pdf" | awk '{print $5}')
PDF_SIZE_MB=$(awk "BEGIN {printf \"%.2f\", $PDF_SIZE/1024/1024}")
echo "📄 PDF 文件大小: ${PDF_SIZE_MB} MB"

cd "$CURRENT_DIR"

# 生成 JSON 报告
cat > "$OUTPUT_FILE" << EOF
{
  "test_info": {
    "test_time": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "platform": "$(uname -s) $(uname -r)",
    "machine": "$(uname -m)"
  },
  "compilation": {
    "times": $TIMES,
    "total_time_ms": $TOTAL_TIME,
    "average_time_ms": $AVG_TIME,
    "average_time_sec": ${AVG_TIME_SEC}
  },
  "pdf": {
    "size_bytes": $PDF_SIZE,
    "size_mb": ${PDF_SIZE_MB}
  }
}
EOF

# 输出结果
echo ""
echo "✅ 测试完成！"
echo ""
echo "📄 结果已保存到: $OUTPUT_FILE"
echo ""
if command -v python3 &> /dev/null; then
  python3 -m json.tool "$OUTPUT_FILE"
else
  cat "$OUTPUT_FILE"
fi
echo ""
echo "=== 性能基准测试完成 ==="
