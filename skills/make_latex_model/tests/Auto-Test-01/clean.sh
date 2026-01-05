#!/bin/bash
# ============================================
# 清理测试环境
# ============================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "清理测试环境..."
echo "工作空间: $SCRIPT_DIR/workspace"
echo "日志: $SCRIPT_DIR/logs"
echo "输出产物: $SCRIPT_DIR/artifacts/output"
echo ""

# 询问确认
read -p "确定要清理所有测试产物吗？(y/N) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # 清理工作空间
    rm -rf "$SCRIPT_DIR/workspace"
    echo "✓ 工作空间已清理"

    # 清理日志
    rm -rf "$SCRIPT_DIR/logs"
    echo "✓ 日志已清理"

    # 清理输出产物
    rm -rf "$SCRIPT_DIR/artifacts/output"
    echo "✓ 输出产物已清理"

    echo ""
    echo "清理完成！"
else
    echo "取消清理"
fi
