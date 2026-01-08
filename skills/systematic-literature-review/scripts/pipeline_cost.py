#!/usr/bin/env python3
"""
Pipeline Cost Tracker - 原生 AI 驱动的成本追踪系统

使用方式：
1. python pipeline_cost.py init                    # 初始化
2. python pipeline_cost.py fetch-prices            # AI 自动获取价格（推荐）
3. python pipeline_cost.py log --in 1234 --out 567 # 记录使用
4. python pipeline_cost.py summary                 # 查看统计

设计原则：
- 单文件：所有功能集中
- 原生 AI 驱动：价格获取在技能环境中自动完成
- 零维护：AI 自动处理所有细节
"""

import csv
import uuid
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict

# ========== 路径配置 ==========
SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR.parent / "config.yaml"
PRICE_FILE = SCRIPT_DIR / "pipeline_cost.yaml"


def get_paths():
    """获取项目级路径"""
    work_dir = Path.cwd()
    slr_dir = work_dir / ".systematic-literature-review"
    cost_dir = slr_dir / "cost"

    return {
        'work_dir': work_dir,
        'slr_dir': slr_dir,
        'cost_dir': cost_dir,
        'usage_csv': cost_dir / "token_usage.csv",
        'project_prices': cost_dir / "price_config.yaml",
        'session_id': f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    }


# ========== 配置管理 ==========
def get_config():
    """加载配置"""
    if not CONFIG_FILE.exists():
        return {
            'cost_tracking': {
                'enabled': True,
                'model_providers': ['OpenAI', 'Anthropic', '智谱清言'],
                'price_cache_max_days': 30,
                'currency_rates': {'USD_TO_CNY': 7.2}
            }
        }

    with open(CONFIG_FILE, encoding='utf-8') as f:
        config = yaml.safe_load(f)

    return config.get('cost_tracking', {})


# ========== 初始化 ==========
def init():
    """初始化追踪系统"""
    paths = get_paths()
    config = get_config()

    if not config.get('enabled', True):
        print("⚠️  成本追踪未启用")
        return False

    # 创建目录
    paths['cost_dir'].mkdir(parents=True, exist_ok=True)

    # 创建 CSV
    if not paths['usage_csv'].exists():
        with open(paths['usage_csv'], 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'session_id', 'tool_name', 'model',
                'input_tokens', 'output_tokens', 'total_tokens', 'step_name'
            ])

    print(f"✅ 初始化完成")
    print(f"   项目目录: {paths['cost_dir']}")
    print(f"   使用记录: {paths['usage_csv']}")
    print(f"   价格缓存: {PRICE_FILE}")

    return True


# ========== 价格获取（原生 AI 驱动）==========
def fetch_prices():
    """
    AI 自动获取价格

    用户运行此命令后，AI 将自动：
    1. 读取 config.yaml 中的模型商配置
    2. 使用 WebSearch 工具查询官方价格
    3. 解析并生成 YAML 格式
    4. 调用 save_prices() 保存到 pipeline_cost.yaml
    """
    config = get_config()
    providers = config.get('model_providers', ['OpenAI', 'Anthropic', '智谱清言'])

    print("=" * 70)
    print("🤖 原生 AI 驱动的价格获取")
    print("=" * 70)
    print(f"\n📋 配置的模型商: {', '.join(providers)}")
    print(f"\n📁 价格将保存到: {PRICE_FILE}")
    print("\n" + "=" * 70)
    print("✨ AI 请自动执行以下步骤：")
    print("=" * 70)
    print(f"""
1. 使用 WebSearch 工具查询以下模型商的官方 API 定价

   需要查询的模型商：{', '.join(providers)}

2. 对每个模型商，搜索其常用模型的定价：
   - OpenAI: gpt-4o, gpt-4o-mini, o1, o1-mini
   - Anthropic: claude-opus-4-5, claude-sonnet-4-5, claude-haiku-4-5
   - 智谱清言: glm-4, glm-4-air, glm-4-flash

3. 从官方定价页面提取：
   - 模型名称（如 gpt-4o）
   - 输入价格（每 1K tokens）
   - 输出价格（每 1K tokens）
   - 货币单位（USD/CNY）
   - 官方来源 URL

4. 生成 YAML 格式，包含以下结构：

```yaml
models:
  gpt-4o:
    input: 0.015
    output: 0.06
    currency: USD
    display_name: "GPT-4o"
    source_url: "https://openai.com/pricing"
    provider: "OpenAI"

  claude-opus-4-5:
    input: 0.015
    output: 0.075
    currency: USD
    display_name: "Claude Opus 4.5"
    source_url: "https://www.anthropic.com/pricing"
    provider: "Anthropic"

  glm-4:
    input: 0.01
    output: 0.01
    currency: CNY
    display_name: "智谱 GLM-4"
    source_url: "https://open.bigmodel.cn/pricing"
    provider: "智谱清言"

metadata:
  fetched_at: "2025-01-02T10:00:00"
  fetched_by: "native_ai"
  providers_queried: ["OpenAI", "Anthropic", "智谱清言"]
```

5. 调用保存函数：
   import sys
   sys.path.insert(0, '{SCRIPT_DIR}')
   from pipeline_cost import save_prices
   save_prices(yaml_content)
""")
    print("=" * 70)
    print("\n💡 AI 将自动完成上述步骤，无需人工干预\n")

    return True


def save_prices(yaml_content: str):
    """
    保存 AI 生成的价格数据

    Args:
        yaml_content: AI 生成的 YAML 格式价格数据
    """
    try:
        # 解析 YAML
        data = yaml.safe_load(yaml_content)

        # 添加元数据
        if 'metadata' not in data:
            data['metadata'] = {}
        data['metadata']['saved_at'] = datetime.now().isoformat()
        data['metadata']['version'] = '1.0'

        # 保存到 scripts/pipeline_cost.yaml
        with open(PRICE_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

        print(f"\n✅ 价格数据已保存")
        print(f"   文件: {PRICE_FILE}")
        print(f"   模型数量: {len(data.get('models', {}))}")

        # 同时复制到当前项目
        paths = get_paths()
        import shutil
        paths['cost_dir'].mkdir(parents=True, exist_ok=True)
        shutil.copy(PRICE_FILE, paths['project_prices'])
        print(f"   已复制到项目: {paths['project_prices']}")

        return True

    except Exception as e:
        print(f"\n❌ 保存失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def load_prices() -> Dict:
    """加载价格数据（优先项目级，回退到技能级）"""
    paths = get_paths()

    # 优先项目级
    if paths['project_prices'].exists():
        with open(paths['project_prices'], encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    # 回退到技能级
    if PRICE_FILE.exists():
        with open(PRICE_FILE, encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    return {}


def copy_prices():
    """复制价格到当前项目"""
    paths = get_paths()

    if not PRICE_FILE.exists():
        print("❌ 价格缓存不存在，请先运行: python pipeline_cost.py fetch-prices")
        return False

    import shutil
    paths['cost_dir'].mkdir(parents=True, exist_ok=True)
    shutil.copy(PRICE_FILE, paths['project_prices'])

    print(f"✅ 价格已复制到: {paths['project_prices']}")
    return True


# ========== Token 记录 ==========
def log_usage(tool_name: str, input_tokens: int, output_tokens: int,
              step_name: str = "", model: str = ""):
    """记录 token 使用"""
    paths = get_paths()

    if not paths['usage_csv'].exists():
        init()

    total = input_tokens + output_tokens

    with open(paths['usage_csv'], 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().isoformat(),
            paths['session_id'],
            tool_name,
            model,
            input_tokens,
            output_tokens,
            total,
            step_name
        ])


# ========== 费用计算 ==========
def calculate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """计算费用"""
    prices = load_prices()
    config = get_config()

    if not prices or 'models' not in prices:
        return 0.0

    # 查找模型价格
    model_config = None
    for model_name, config_data in prices['models'].items():
        if model_name.lower() in model.lower() or model.lower() in model_name.lower():
            model_config = config_data
            break

    if not model_config:
        return 0.0

    # 计算费用
    input_cost = (input_tokens / 1000) * model_config['input']
    output_cost = (output_tokens / 1000) * model_config['output']
    total_cost = input_cost + output_cost

    # 货币转换
    rates = config.get('currency_rates', {})

    if model_config['currency'] == 'CNY':
        return total_cost
    elif model_config['currency'] == 'USD':
        return total_cost * rates.get('USD_TO_CNY', 7.2)

    return total_cost


# ========== 统计报告 ==========
def summary(report_type: str = "project", include_cost: bool = True):
    """生成统计报告"""
    paths = get_paths()

    if not paths['usage_csv'].exists():
        return "⚠️  暂无使用记录，请先运行: python pipeline_cost.py init\n"

    # 读取记录
    records = []
    with open(paths['usage_csv'], encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)

    if not records:
        return "⚠️  暂无使用记录\n"

    # 筛选
    if report_type == "session":
        records = [r for r in records if r['session_id'] == paths['session_id']]
        period = f"当前会话 ({paths['session_id']})"
    else:
        period = "整个项目"

    if not records:
        return f"⚠️  {period}暂无使用记录\n"

    # 汇总
    total_input = sum(int(r['input_tokens']) for r in records)
    total_output = sum(int(r['output_tokens']) for r in records)
    total_tokens = sum(int(r['total_tokens']) for r in records)

    # 费用
    cost_section = ""
    total_cost = 0.0

    if include_cost:
        prices = load_prices()

        if prices and 'models' in prices:
            for r in records:
                model = r['model'] or 'unknown'
                total_cost += calculate_cost(int(r['input_tokens']), int(r['output_tokens']), model)

            cost_section = f"\n💰 预计总费用: ¥{total_cost:.2f} CNY\n"

            # 按模型分解
            model_stats = {}
            for r in records:
                model = r['model'] or 'unknown'
                if model not in model_stats:
                    model_stats[model] = {'input': 0, 'output': 0}
                model_stats[model]['input'] += int(r['input_tokens'])
                model_stats[model]['output'] += int(r['output_tokens'])

            if model_stats:
                cost_section += "\n按模型分解：\n"
                for model, tokens in sorted(model_stats.items(), key=lambda x: x[1]['output'], reverse=True):
                    cost = calculate_cost(tokens['input'], tokens['output'], model)
                    cost_section += f"  {model}: ¥{cost:.2f}\n"
        else:
            cost_section = "\n⚠️  无法估算费用（未配置价格）\n"
            cost_section += "   请运行: python pipeline_cost.py fetch-prices\n"

    # 按工具统计
    tool_stats = {}
    for r in records:
        tool = r['tool_name'] or 'unknown'
        if tool not in tool_stats:
            tool_stats[tool] = {'input': 0, 'output': 0, 'calls': 0}
        tool_stats[tool]['input'] += int(r['input_tokens'])
        tool_stats[tool]['output'] += int(r['output_tokens'])
        tool_stats[tool]['calls'] += 1

    # 生成报告
    report = f"""
{'='*70}
📊 Token 使用统计 - {period}
{'='*70}

📈 总览：
  总输入 Token:  {total_input:,}
  总输出 Token:  {total_output:,}
  总计 Token:    {total_tokens:,}
  记录次数:      {len(records)} 次
{cost_section}
🔧 按工具统计：
"""

    for tool, stats in sorted(tool_stats.items(), key=lambda x: x[1]['output'], reverse=True):
        report += f"\n  {tool}:\n"
        report += f"    调用: {stats['calls']} | 输入: {stats['input']:,} | 输出: {stats['output']:,}\n"

    # 最近记录
    if report_type == "project" and len(records) > 5:
        recent = sorted(records, key=lambda x: x['timestamp'], reverse=True)[:5]
        report += f"\n📝 最近 5 条记录：\n"
        for r in recent:
            time_str = r['timestamp'][:19].replace('T', ' ')
            report += f"  {time_str} | {r['tool_name']}: {r['input_tokens']} in + {r['output_tokens']} out"
            if r['step_name']:
                report += f" | {r['step_name']}"
            report += "\n"

    report += f"{'='*70}\n"

    return report


# ========== 自动追踪 ==========
def track_response(response, tool_name: str, step_name: str = ""):
    """自动从响应中提取并记录"""
    tokens = None

    if hasattr(response, 'usage'):
        usage = response.usage
        tokens = {
            'input': getattr(usage, 'prompt_tokens', 0),
            'output': getattr(usage, 'completion_tokens', 0),
            'model': getattr(usage, 'model', '')
        }
    elif isinstance(response, dict) and 'usage' in response:
        usage = response['usage']
        tokens = {
            'input': usage.get('prompt_tokens', 0),
            'output': usage.get('completion_tokens', 0),
            'model': usage.get('model', '')
        }

    if tokens and (tokens['input'] > 0 or tokens['output'] > 0):
        log_usage(tool_name, tokens['input'], tokens['output'], step_name, tokens['model'])
        print(f"✅ 已记录: {tokens['input'] + tokens['output']:,} tokens")


# ========== CLI ==========
def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Pipeline Cost Tracker',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python pipeline_cost.py init           # 初始化
  python pipeline_cost.py fetch-prices   # AI 自动获取价格
  python pipeline_cost.py log --in 1234 --out 567 --step "search"
  python pipeline_cost.py summary        # 查看统计
        """
    )

    parser.add_argument('command', nargs='?', help='命令')
    parser.add_argument('--in', type=int, dest='input_tokens', help='输入 tokens')
    parser.add_argument('--out', type=int, dest='output_tokens', help='输出 tokens')
    parser.add_argument('--step', default='', help='步骤名称')
    parser.add_argument('--tool', default='manual', help='工具名称')
    parser.add_argument('--model', default='', help='模型名称')
    parser.add_argument('--type', choices=['session', 'project'], default='project', help='报告类型')
    parser.add_argument('--no-cost', action='store_true', help='不显示费用')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == 'init':
        init()

    elif args.command == 'fetch-prices':
        fetch_prices()

    elif args.command == 'log':
        if args.input_tokens is None or args.output_tokens is None:
            print("❌ 请提供 --in 和 --out 参数")
            return
        log_usage(args.tool, args.input_tokens, args.output_tokens, args.step, args.model)
        print(f"✅ 已记录: {args.input_tokens + args.output_tokens:,} tokens")

    elif args.command == 'summary':
        print(summary(args.type, not args.no_cost))

    elif args.command == 'copy-prices':
        copy_prices()

    else:
        print(f"❌ 未知命令: {args.command}")
        parser.print_help()


if __name__ == '__main__':
    main()
