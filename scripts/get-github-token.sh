#!/bin/bash
# 确保 .env 存在并读取 GH_TOKEN

ENV_FILE=".env"

# 如果 .env 不存在，创建它
if [ ! -f "$ENV_FILE" ]; then
    touch "$ENV_FILE"
    echo "# GitHub Token for releases" >> "$ENV_FILE"
    echo "GH_TOKEN=" >> "$ENV_FILE"
fi

# 确保 .env 在 .gitignore 中
if [ -f .gitignore ] && ! grep -q "^\.env$" .gitignore; then
    echo ".env" >> .gitignore
    echo "✅ 已将 .env 添加到 .gitignore"
fi

# 读取并返回 GH_TOKEN
source "$ENV_FILE"
echo "$GH_TOKEN"
