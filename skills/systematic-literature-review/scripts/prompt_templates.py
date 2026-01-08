#!/usr/bin/env python3
"""
prompt_templates.py - AI 评分 Prompt 模板管理器

P1-2: AI 评分 Prompt 与领域检测联动 - 根据领域自动选择合适的评分模板

功能：
  - 管理跨领域评分 Prompt 模板
  - 根据检测到的领域自动加载对应模板
  - 支持模板变量替换
  - 提供模板验证和测试功能

使用示例：
    from scripts.prompt_templates import PromptTemplateManager, load_domain_prompt

    # 方式1: 使用管理器
    manager = PromptTemplateManager()
    template = manager.get_template('cs')
    prompt = template.fill(paper_data={"title": "...", "abstract": "..."})

    # 方式2: 直接加载
    template = load_domain_prompt('clinical')

    # 应用 PICO 框架
    prompt = template.fill(paper_data={"P": "...", "I": "...", "C": "...", "O": "..."})
"""

import json
import logging
import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# 领域枚举
# ============================================================================

class Domain(Enum):
    """研究领域枚举"""
    CLINICAL = "clinical"
    CS = "cs"
    ENGINEERING = "engineering"
    SOCIAL = "social"
    GENERAL = "general"

    @classmethod
    def from_string(cls, domain_str: str) -> 'Domain':
        """从字符串创建领域枚举（支持别名）"""
        aliases = {
            'clinical': [cls.CLINICAL, 'medicine', 'medical'],
            'cs': [cls.CS, 'computer_science', 'machine_learning', 'ai'],
            'engineering': [cls.ENGINEERING, 'physical', 'physics'],
            'social': [cls.SOCIAL, 'social_science', 'humanities'],
            'general': [cls.GENERAL, 'default', 'other']
        }

        domain_lower = domain_str.lower()

        for key, values in aliases.items():
            if domain_lower in [v.value if isinstance(v, cls) else v for v in values]:
                return values[0]

        return cls.GENERAL


# ============================================================================
# Prompt 模板类
# ============================================================================

class PromptTemplate:
    """Prompt 模板类"""

    def __init__(
        self,
        template: str,
        metadata: Optional[Dict[str, Any]] = None,
        variables: Optional[List[str]] = None
    ):
        """
        初始化模板

        Args:
            template: 模板内容（支持 {variable} 占位符）
            metadata: 模板元数据（版本、作者、更新时间等）
            variables: 模板变量列表（自动从模板提取）
        """
        self.template = template
        self.metadata = metadata or {}
        self.variables = variables or self._extract_variables()

    def _extract_variables(self) -> List[str]:
        """从模板中提取变量（{variable} 格式）"""
        pattern = r'\{([^}]+)\}'
        variables = re.findall(pattern, self.template)
        return list(set(variables))

    def fill(self, **kwargs) -> str:
        """
        填充模板变量

        Args:
            **kwargs: 变量值

        Returns:
            填充后的 Prompt 字符串

        Raises:
            ValueError: 缺少必需变量
        """
        # 检查缺失变量
        missing_vars = set(self.variables) - set(kwargs.keys())
        if missing_vars:
            raise ValueError(f"缺少必需变量: {missing_vars}")

        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"变量未定义: {e}")

    def validate(self) -> bool:
        """验证模板格式"""
        # 检查变量格式
        pattern = r'\{[^}]+\}'
        all_matches = re.findall(pattern, self.template)
        for match in all_matches:
            if not re.match(r'^\{[a-zA-Z_][a-zA-Z0-9_]*\}$', match):
                logger.warning(f"可疑变量格式: {match}")
                return False

        return True

    def get_variable_help(self) -> Dict[str, str]:
        """获取变量帮助信息（从模板注释中提取）"""
        help_text = {}

        # 简单实现：从模板中提取变量说明
        for var in self.variables:
            # 查找变量说明（格式: # {var}: 说明）
            pattern = rf'#\s*\{{{var}\}}:\s*([^\n]+)'
            match = re.search(pattern, self.template)
            if match:
                help_text[var] = match.group(1).strip()

        return help_text


# ============================================================================
# Prompt 模板管理器
# ============================================================================

class PromptTemplateManager:
    """Prompt 模板管理器"""

    # 默认模板目录
    DEFAULT_TEMPLATE_DIR = Path(__file__).parent.parent / "references" / "prompts"

    def __init__(self, template_dir: Optional[Path] = None):
        """
        初始化管理器

        Args:
            template_dir: 模板目录路径
        """
        self.template_dir = template_dir or self.DEFAULT_TEMPLATE_DIR
        self._cache: Dict[str, PromptTemplate] = {}

        # 如果目录不存在，创建默认模板
        if not self.template_dir.exists():
            self._create_default_templates()

    def _create_default_templates(self):
        """创建默认 Prompt 模板"""
        self.template_dir.mkdir(parents=True, exist_ok=True)

        # 这里可以写入默认模板到文件
        # 为简化，这里只创建目录
        logger.info(f"模板目录已创建: {self.template_dir}")

    def get_template(self, domain: str) -> PromptTemplate:
        """
        获取指定领域的 Prompt 模板

        Args:
            domain: 领域标识

        Returns:
            Prompt 模板对象
        """
        # 检查缓存
        if domain in self._cache:
            return self._cache[domain]

        # 枚举化领域
        domain_enum = Domain.from_string(domain)
        domain_key = domain_enum.value

        # 尝试加载模板文件
        template_path = self.template_dir / f"{domain_key}.txt"
        if template_path.exists():
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
        else:
            # 使用内置默认模板
            template_content = self._get_builtin_template(domain_key)

        # 创建模板对象
        template = PromptTemplate(
            template=template_content,
            metadata={'domain': domain_key, 'source': str(template_path)}
        )

        # 缓存
        self._cache[domain] = template

        return template

    def _get_builtin_template(self, domain: str) -> str:
        """获取内置默认模板"""

        # 临床医学模板（PICO 框架）
        if domain == 'clinical':
            return """请评估以下临床研究论文的相关性和质量。

# 研究问题（PICO框架）
- P (Population): {Population}
- I (Intervention): {Intervention}
- C (Comparator): {Comparator}
- O (Outcome): {Outcome}

# 论文信息
标题: {title}
摘要: {abstract}
期刊: {venue}
发表年份: {year}

# 评估维度（每项0-3分）
1. 研究人群匹配度: 论文的研究人群与目标人群的相似程度
2. 干预措施相关性: 干预措施与目标干预的相似程度
3. 结局指标相关性: 结局指标与目标结局的相关性
4. 研究设计质量: RCT > 队列研究 > 病例对照 > 病例系列
5. 样本量充足性: 样本量是否足够支持结论

请以JSON格式返回评分：
{"scores": {"dimension1": 2, "dimension2": 3, ...}, "total_score": 12, "rationale": "..."}"""

        # 计算机科学模板（任务-数据-方法-指标）
        elif domain == 'cs':
            return """请评估以下计算机科学论文的相关性和质量。

# 研究问题框架
- 任务: {task}
- 数据类型: {data_type}
- 方法类别: {method_category}
- 评估指标: {evaluation_metric}

# 论文信息
标题: {title}
摘要: {abstract}
发表 venue: {venue}
年份: {year}

# 评估维度（每项0-3分）
1. 任务相关性: 论文任务与目标任务的匹配程度
2. 方法创新性: 方法的创新程度和技术贡献
3. 实验充分性: 实验设计和数据集的充分性
4. 结果可信度: 结果的可信度和可复现性
5. 影响力: 引用数和社区认可度

请以JSON格式返回评分：
{"scores": {"dimension1": 2, ...}, "total_score": 12, "rationale": "..."}"""

        # 工程学模板（实验-方法-性能-可复现性）
        elif domain == 'engineering':
            return """请评估以下工程/物理论文的相关性和质量。

# 论文信息
标题: {title}
摘要: {abstract}
期刊: {venue}
年份: {year}
研究主题: {topic}

# 评估维度（每项0-3分）
1. 主题相关性: 与研究主题的相关程度
2. 方法科学性: 实验方法的科学性和严谨性
3. 结果可靠性: 结果的可靠性和误差分析
4. 创新性: 方法的创新程度
5. 实用性: 工程应用前景

请以JSON格式返回评分：
{"scores": {"dimension1": 2, ...}, "total_score": 10, "rationale": "..."}"""

        # 社会科学模板（研究对象-变量-关系-方法）
        elif domain == 'social':
            return """请评估以下社会科学论文的相关性和质量。

# 论文信息
标题: {title}
摘要: {abstract}
期刊: {venue}
年份: {year}
研究主题: {topic}

# 评估维度（每项0-3分）
1. 主题相关性: 与研究主题的相关程度
2. 理论贡献: 对理论发展的贡献
3. 方法严谨性: 研究方法的严谨性
4. 证据充分性: 经验证据的充分性
5. 启发性: 对后续研究的启发价值

请以JSON格式返回评分：
{"scores": {"dimension1": 2, ...}, "total_score": 10, "rationale": "..."}"""

        # 通用模板
        else:
            return """请评估以下论文的相关性和质量。

# 论文信息
标题: {title}
摘要: {abstract}
期刊: {venue}
年份: {year}

# 评估维度（每项0-3分）
1. 主题相关性: 与目标研究主题的相关程度
2. 方法质量: 研究方法的质量和严谨性
3. 结果可靠性: 结果的可靠性
4. 创新性: 研究的创新程度
5. 影响力: 学术影响力（引用、期刊等）

请以JSON格式返回评分：
{"scores": {"dimension1": 2, ...}, "total_score": 10, "rationale": "..."}"""

    def list_templates(self) -> List[str]:
        """列出所有可用的模板"""
        templates = []

        # 文件模板
        if self.template_dir.exists():
            for file in self.template_dir.glob("*.txt"):
                templates.append(file.stem)

        # 内置模板
        templates.extend(['clinical', 'cs', 'engineering', 'social', 'general'])

        return sorted(set(templates))

    def reload_template(self, domain: str):
        """重新加载指定领域的模板（清除缓存）"""
        if domain in self._cache:
            del self._cache[domain]
        logger.info(f"已清除 {domain} 模板缓存")


# ============================================================================
# 便捷函数
# ============================================================================

def load_domain_prompt(domain: str) -> PromptTemplate:
    """
    加载指定领域的 Prompt 模板

    Args:
        domain: 领域标识

    Returns:
        Prompt 模板对象
    """
    manager = PromptTemplateManager()
    return manager.get_template(domain)


def fill_relevance_prompt(domain: str, paper_data: Dict[str, Any]) -> str:
    """
    填充相关性评分 Prompt

    Args:
        domain: 领域标识
        paper_data: 论文数据字典

    Returns:
        填充后的 Prompt 字符串
    """
    template = load_domain_prompt(domain)

    # 验证必需字段
    required_fields = ['title', 'abstract']
    missing_fields = [f for f in required_fields if f not in paper_data]

    if missing_fields:
        # 提供默认值
        for field in missing_fields:
            paper_data[field] = paper_data.get(field, "[N/A]")

    return template.fill(**paper_data)


def detect_domain_and_load_prompt(keywords: List[str],
                                  topic: str = "") -> tuple:
    """
    检测领域并加载对应的 Prompt 模板

    Args:
        keywords: 关键词列表
        topic: 研究主题（可选）

    Returns:
        (领域, Prompt模板对象)
    """
    # 这里可以调用 detect_domain.py 的逻辑
    # 为简化，这里使用关键词启发式判断

    keyword_text = ' '.join(keywords + [topic]).lower()

    # 临床医学关键词
    clinical_keywords = ['clinical', 'patient', 'trial', 'treatment', 'diagnosis',
                        'therapy', 'disease', 'symptom', 'drug', 'medicine']

    # 计算机科学关键词
    cs_keywords = ['algorithm', 'model', 'machine learning', 'neural', 'deep learning',
                  'data', 'computing', 'software', 'hardware', 'ai', 'classification']

    # 工程学关键词
    engineering_keywords = ['experiment', 'material', 'physics', 'chemistry',
                           'engineering', 'fabrication', 'measurement']

    # 社会科学关键词
    social_keywords = ['social', 'society', 'policy', 'economic', 'education',
                      'psychology', 'behavior', 'culture']

    scores = {
        'clinical': sum(1 for kw in clinical_keywords if kw in keyword_text),
        'cs': sum(1 for kw in cs_keywords if kw in keyword_text),
        'engineering': sum(1 for kw in engineering_keywords if kw in keyword_text),
        'social': sum(1 for kw in social_keywords if kw in keyword_text)
    }

    # 选择得分最高的领域
    detected_domain = max(scores.items(), key=lambda x: x[1])[0]
    if scores[detected_domain] == 0:
        detected_domain = 'general'

    logger.info(f"检测到领域: {detected_domain} (得分: {scores})")

    manager = PromptTemplateManager()
    template = manager.get_template(detected_domain)

    return detected_domain, template


# ============================================================================
# 命令行接口（用于测试）
# ============================================================================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Prompt 模板管理工具')
    parser.add_argument('--list', action='store_true', help='列出所有可用模板')
    parser.add_argument('--domain', '-d', help='显示指定领域的模板')
    parser.add_argument('--validate', action='store_true', help='验证模板格式')
    parser.add_argument('--test-fill', action='store_true', help='测试填充模板')

    args = parser.parse_args()

    manager = PromptTemplateManager()

    if args.list:
        templates = manager.list_templates()
        print("可用模板:")
        for t in templates:
            print(f"  - {t}")

    elif args.domain:
        template = manager.get_template(args.domain)

        print(f"=== {args.domain} 模板 ===\n")
        print(template.template)

        print(f"\n变量: {template.variables}")

        if args.validate:
            is_valid = template.validate()
            print(f"验证: {'✓ 通过' if is_valid else '✗ 失败'}")

        if args.test_fill:
            # 示例数据
            sample_data = {
                'title': 'Sample Paper Title',
                'abstract': 'This is a sample abstract.',
                'venue': 'Nature',
                'year': '2024',
                'topic': 'Machine Learning'
            }

            # 添加领域特定变量
            if args.domain == 'clinical':
                sample_data.update({
                    'Population': 'Adults with diabetes',
                    'Intervention': 'New drug X',
                    'Comparator': 'Standard treatment',
                    'Outcome': 'HbA1c levels'
                })
            elif args.domain == 'cs':
                sample_data.update({
                    'task': 'Image classification',
                    'data_type': 'Images',
                    'method_category': 'Deep learning',
                    'evaluation_metric': 'Accuracy'
                })

            try:
                filled = template.fill(**sample_data)
                print("\n=== 填充示例 ===\n")
                print(filled[:500] + "...")
            except ValueError as e:
                print(f"\n填充失败: {e}")
