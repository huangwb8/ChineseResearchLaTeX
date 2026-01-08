"""
测试引用强制守护者
"""

import pytest
from core.reference_guardian import ReferenceGuardian


def test_protect_references():
    """测试引用保护"""
    config = {"reference_protection": {"enabled": True}}
    guardian = ReferenceGuardian(config)

    content = r"""这是正文内容，参见\ref{fig1}和\cite{author2024}。
另外见图\includegraphics{figures/fig1.pdf}。"""

    protected, ref_map = guardian.protect_references(content)

    # 应该生成占位符
    assert "__REF_" in protected
    assert len(ref_map) > 0

    # 原始引用应该被替换
    assert r"\ref{fig1}" not in protected
    assert r"\cite{author2024}" not in protected


def test_restore_references():
    """测试引用恢复"""
    config = {"reference_protection": {"enabled": True}}
    guardian = ReferenceGuardian(config)

    content = r"""参见\ref{fig1}和\cite{author2024}。"""
    protected, ref_map = guardian.protect_references(content)
    restored = guardian.restore_references(protected, ref_map)

    # 应该完全恢复原始引用
    assert restored == content


def test_extract_references():
    """测试引用提取"""
    config = {"reference_protection": {"enabled": True}}
    guardian = ReferenceGuardian(config)

    content = r"""\ref{fig1} \cite{author2024} \citep{author2023}"""
    refs = guardian._extract_all_references(content)

    assert "fig1" in refs
    assert "author2024" in refs
    assert "author2023" in refs


def test_validate_references():
    """测试引用验证"""
    config = {"reference_protection": {"enabled": True}}
    guardian = ReferenceGuardian(config)

    original_refs = {"fig1", "author2024"}

    # 测试完整引用
    content = r"""\ref{fig1} \cite{author2024}"""
    validation = guardian.validate_references(content, original_refs)
    assert validation["valid"] is True
    assert validation["missing_count"] == 0

    # 测试缺失引用
    content = r"""\ref{fig1}"""
    validation = guardian.validate_references(content, original_refs)
    assert validation["valid"] is False
    assert validation["missing_count"] == 1
    assert "author2024" in validation["missing"]


def test_generate_reference_report():
    """测试生成引用报告"""
    config = {"reference_protection": {"enabled": True}}
    guardian = ReferenceGuardian(config)

    content = r"""\ref{fig1} \cite{author2024} \cite{author2023}"""
    report = guardian.generate_reference_report(content)

    assert "ref" in report
    assert "cite" in report
    assert report["ref"]["count"] == 1
    assert report["cite"]["count"] == 2
    assert report["total"] == 3


def test_disabled():
    """测试禁用保护"""
    config = {"reference_protection": {"enabled": False}}
    guardian = ReferenceGuardian(config)

    content = r"""\ref{fig1}"""
    protected, ref_map = guardian.protect_references(content)

    # 禁用时应直接返回原内容
    assert protected == content
    assert ref_map == {}
