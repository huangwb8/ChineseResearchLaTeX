#!/usr/bin/env python3
"""
detect_domain.py - 领域自动检测脚本

P1-1: 避免评分标准误用 - 自动检测研究主题所属领域

输入：研究主题/摘要
输出：预测领域（clinical/cs/engineering/social）+ 置信度

使用示例：
    python detect_domain.py --topic "CRISPR gene editing efficiency"
    python detect_domain.py --abstract "Deep learning for medical image analysis..."
    python detect_domain.py --topic "Transformer in computer vision" --verbose
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


# ============================================================================
# 领域关键词词典
# ============================================================================

DOMAIN_KEYWORDS = {
    "clinical": {
        "primary": [
            # 疾病/症状
            "cancer", "tumor", "carcinoma", "melanoma", "leukemia", "lymphoma",
            "diabetes", "obesity", "hypertension", "cardiovascular", "stroke",
            "infection", "virus", "bacteria", "inflammation", "immune",
            # 医学方法
            "chemotherapy", "radiotherapy", "immunotherapy", "surgery",
            "diagnosis", "prognosis", "biomarker", "clinical trial", "rct",
            "patient", "cohort", "treatment", "therapy", "drug", "medication",
            # 解剖/生理
            "cell", "tissue", "organ", "blood", "gene", "protein", "dna",
        ],
        "secondary": [
            "hospital", "clinic", "physician", "doctor", "nurse",
            "symptom", "syndrome", "disease", "disorder", "pathology",
            "efficacy", "safety", "adverse event", "side effect",
            "survival", "mortality", "morbidity", "remission", "relapse",
        ],
        "journals": [
            "nature medicine", "lancet", "nejm", "jama", "bmj",
            "clinical cancer research", "journal of clinical oncology",
        ],
    },
    "cs": {
        "primary": [
            # AI/ML 方法
            "deep learning", "neural network", "machine learning", "artificial intelligence",
            "transformer", "attention", "bert", "gpt", "llm",
            "reinforcement learning", "supervised learning", "unsupervised learning",
            # CS 任务
            "classification", "regression", "clustering", "detection", "segmentation",
            "computer vision", "natural language processing", "nlp", "speech recognition",
            # 数据/算法
            "algorithm", "data structure", "computational", "optimization",
            "big data", "dataset", "benchmark", "evaluation metric",
        ],
        "secondary": [
            "convolutional", "recurrent", "lstm", "cnn", "rnn", "gan",
            "feature extraction", "representation learning", "embedding",
            "training", "inference", "prediction", "accuracy", "precision",
            "framework", "library", "implementation", "code", "github",
        ],
        "venues": [
            "neurips", "icml", "iclr", "cvpr", "eccv", "iccv", "acl", "emnlp",
            "aaai", "ijcai", "kdd", "recsys", "sigir",
        ],
    },
    "engineering": {
        "primary": [
            # 材料/器件
            "solar cell", "battery", "semiconductor", "catalyst", "polymer",
            "composite", "alloy", "ceramic", "nanomaterial", "graphene",
            # 工程方法
            "fabrication", "synthesis", "manufacturing", "processing",
            "characterization", "measurement", "performance", "efficiency",
            # 物理/化学
            "thermal", "electrical", "mechanical", "optical", "magnetic",
            "conductivity", "stability", "durability", "reliability",
        ],
        "secondary": [
            "device", "sensor", "actuator", "circuit", "system",
            "temperature", "pressure", "voltage", "current", "frequency",
            "simulation", "modeling", "experiment", "testing",
            "scale-up", "deployment", "application", "industrial",
        ],
        "units": [
            "joule", "watt", "volt", "ampere", "hertz", "kelvin", "pascal",
        ],
    },
    "social": {
        "primary": [
            # 社会科学概念
            "survey", "questionnaire", "interview", "focus group", "participant",
            "behavior", "attitude", "perception", "opinion", "belief",
            "social", "cultural", "economic", "political", "psychological",
            # 研究方法
            "qualitative", "quantitative", "mixed method", "longitudinal", "cross-sectional",
            "statistical analysis", "regression", "correlation", "hypothesis",
        ],
        "secondary": [
            "respondent", "sample", "population", "demographic", "socioeconomic",
            "education", "income", "employment", "gender", "age", "ethnicity",
            "policy", "governance", "management", "organization", "institution",
            "validity", "reliability", "bias", "ethics", "consent",
        ],
        "journals": [
            "american sociological review", "social forces", "social psychology",
            "journal of personality", "organizational behavior",
        ],
    },
}


# ============================================================================
# 领域检测器
# ============================================================================

class DomainDetector:
    """领域检测器"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.keywords = DOMAIN_KEYWORDS

    def _score_text(self, text: str, domain: str) -> Dict:
        """计算文本在某个领域的得分"""
        text_lower = text.lower()
        domain_keywords = self.keywords.get(domain, {})

        score = 0
        matches = []

        # 主要关键词（权重 3）
        for kw in domain_keywords.get("primary", []):
            count = text_lower.count(kw.lower())
            if count > 0:
                score += count * 3
                matches.append(f"primary: {kw} ({count})")

        # 次要关键词（权重 1）
        for kw in domain_keywords.get("secondary", []):
            count = text_lower.count(kw.lower())
            if count > 0:
                score += count
                matches.append(f"secondary: {kw} ({count})")

        # 期刊/会议/单位（权重 2）
        for kw in domain_keywords.get("journals", domain_keywords.get("venues", domain_keywords.get("units", []))):
            if kw.lower() in text_lower:
                score += 2
                matches.append(f"venue: {kw}")

        return {"score": score, "matches": matches}

    def detect(self, topic: str = "", abstract: str = "") -> Dict:
        """检测领域"""
        text = f"{topic} {abstract}".strip()

        if not text or len(text) < 20:
            return {
                "domain": "unknown",
                "confidence": 0.0,
                "reason": "输入文本过短，无法检测"
            }

        # 计算各领域得分
        scores = {}
        for domain in self.keywords.keys():
            result = self._score_text(text, domain)
            scores[domain] = result

            if self.verbose:
                print(f"\n{domain.upper()} 得分: {result['score']}")
                if result['matches']:
                    print("  匹配关键词:")
                    for m in result['matches'][:10]:
                        print(f"    - {m}")

        # 找出最高分
        max_score = 0
        best_domain = "unknown"
        for domain, result in scores.items():
            if result["score"] > max_score:
                max_score = result["score"]
                best_domain = domain

        # 计算置信度
        total_score = sum(r["score"] for r in scores.values())
        if total_score == 0:
            confidence = 0.0
        else:
            confidence = max_score / total_score

        # 判断是否需要人工确认
        needs_confirmation = confidence < 0.6 or max_score < 5

        return {
            "domain": best_domain,
            "confidence": confidence,
            "scores": {d: r["score"] for d, r in scores.items()},
            "needs_confirmation": needs_confirmation,
            "reason": self._generate_reason(scores, best_domain, confidence)
        }

    def _generate_reason(self, scores: Dict, best_domain: str, confidence: float) -> str:
        """生成检测理由"""
        if confidence >= 0.8:
            return f"高度匹配 {best_domain} 领域"
        elif confidence >= 0.6:
            return f"可能属于 {best_domain} 领域，建议确认"
        elif scores[best_domain]["score"] > 0:
            return f"跨领域或新兴主题，默认选择 {best_domain}，强烈建议确认"
        else:
            return "未检测到明确领域信号，需要人工指定"


# ============================================================================
# 命令行接口
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="领域自动检测 - 避免评分标准误用"
    )
    parser.add_argument(
        "--topic", "-t",
        help="研究主题（一句话描述）"
    )
    parser.add_argument(
        "--abstract", "-a",
        help="摘要或研究描述"
    )
    parser.add_argument(
        "--file", "-f",
        type=Path,
        help="从文件读取（第一行为主题，后续为摘要）"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="显示详细的匹配过程"
    )

    args = parser.parse_args()

    # 获取输入
    topic = args.topic or ""
    abstract = args.abstract or ""

    if args.file:
        content = args.file.read_text(encoding='utf-8').strip()
        lines = content.split('\n')
        if not topic:
            topic = lines[0] if lines else ""
        if not abstract:
            abstract = '\n'.join(lines[1:]) if len(lines) > 1 else ""

    if not topic and not abstract:
        print("错误: 必须提供 --topic, --abstract 或 --file", file=sys.stderr)
        sys.exit(1)

    # 运行检测
    detector = DomainDetector(verbose=args.verbose)
    result = detector.detect(topic, abstract)

    # 输出结果
    print("\n" + "=" * 70)
    print("领域检测结果")
    print("=" * 70)
    print(f"\n检测到的领域: **{result['domain'].upper()}**")
    print(f"置信度: {result['confidence']:.1%}")

    if args.verbose:
        print("\n各领域得分:")
        for domain, score in result['scores'].items():
            print(f"  {domain}: {score}")

    print(f"\n判断理由: {result['reason']}")

    if result['needs_confirmation']:
        print("\n⚠️  检测置信度较低，建议:")
        print("  1. 人工复核领域选择")
        print("  2. 使用 --domain 参数明确指定领域")
        print(f"  3. 如需强制使用 {result['domain']}，请确认是否合适")

    # 输出 JSON 格式（供脚本调用）
    print("\n" + "-" * 70)
    print("JSON 输出（供脚本使用）:")
    print("-" * 70)
    import json
    json_output = {
        "domain": result['domain'],
        "confidence": result['confidence'],
        "needs_confirmation": result['needs_confirmation']
    }
    print(json.dumps(json_output))

    return 0


if __name__ == "__main__":
    sys.exit(main())
