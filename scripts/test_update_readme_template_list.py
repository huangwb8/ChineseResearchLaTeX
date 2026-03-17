from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import update_readme_template_list as updater
from scripts.update_readme_template_list import render_template_section


def test_render_template_section_includes_thesis_release_assets():
    release = {
        "tag_name": "v4.0.1",
        "published_at": "2026-03-15T23:34:20Z",
        "assets": [
            {
                "name": "thesis-smu-master-v4.0.1.zip",
                "size": 564731,
                "browser_download_url": "https://example.com/thesis-smu-master-v4.0.1.zip",
            },
            {
                "name": "thesis-smu-master-Overleaf-v4.0.1.zip",
                "size": 576416,
                "browser_download_url": "https://example.com/thesis-smu-master-Overleaf-v4.0.1.zip",
            },
            {
                "name": "thesis-sysu-doctor-v4.0.1.zip",
                "size": 569793,
                "browser_download_url": "https://example.com/thesis-sysu-doctor-v4.0.1.zip",
            },
            {
                "name": "thesis-sysu-doctor-Overleaf-v4.0.1.zip",
                "size": 581478,
                "browser_download_url": "https://example.com/thesis-sysu-doctor-Overleaf-v4.0.1.zip",
            },
        ],
    }

    rendered = render_template_section("huangwb8/ChineseResearchLaTeX", release)

    assert "| 模板 | 院校 | 学位 | 标准包 | Overleaf 包 |" in rendered
    assert "[thesis-smu-master](projects/thesis-smu-master/)" in rendered
    assert "[thesis-sysu-doctor](projects/thesis-sysu-doctor/)" in rendered
    assert "| [thesis-smu-master](projects/thesis-smu-master/) | 南方医科大学 | 硕士 |" in rendered
    assert "| [thesis-sysu-doctor](projects/thesis-sysu-doctor/) | 中山大学 | 博士 |" in rendered
    assert "https://example.com/thesis-smu-master-v4.0.1.zip" in rendered
    assert "https://example.com/thesis-sysu-doctor-Overleaf-v4.0.1.zip" in rendered
    assert "[bensz-thesis](packages/bensz-thesis/)" not in rendered


def test_render_template_section_includes_cv_release_assets():
    release = {
        "tag_name": "v4.0.2",
        "published_at": "2026-03-16T07:31:00Z",
        "assets": [
            {
                "name": "cv-01-v4.0.2.zip",
                "size": 2081792,
                "browser_download_url": "https://example.com/cv-01-v4.0.2.zip",
            },
            {
                "name": "cv-01-Overleaf-v4.0.2.zip",
                "size": 105994240,
                "browser_download_url": "https://example.com/cv-01-Overleaf-v4.0.2.zip",
            },
        ],
    }

    rendered = render_template_section("huangwb8/ChineseResearchLaTeX", release)

    assert "### 简历模板" in rendered
    assert "[cv-01](projects/cv-01/)" in rendered
    assert "https://example.com/cv-01-v4.0.2.zip" in rendered
    assert "https://example.com/cv-01-Overleaf-v4.0.2.zip" in rendered


def test_render_template_section_includes_paper_customization_issue_hints():
    release = {
        "tag_name": "v4.0.2",
        "published_at": "2026-03-16T07:31:00Z",
        "assets": [
            {
                "name": "paper-sci-01-v4.0.2.zip",
                "size": 2081792,
                "browser_download_url": "https://example.com/paper-sci-01-v4.0.2.zip",
            },
            {
                "name": "paper-sci-01-Overleaf-v4.0.2.zip",
                "size": 105994240,
                "browser_download_url": "https://example.com/paper-sci-01-Overleaf-v4.0.2.zip",
            },
        ],
    }

    rendered = render_template_section("huangwb8/ChineseResearchLaTeX", release)

    assert "### SCI 论文模板" in rendered
    assert "如有这类需求，建议提交 [SCI 论文模板定制需求]" in rendered
    assert "?template=paper-template-customization.yml" in rendered
    assert "如果最关键的是" not in rendered


def test_render_template_section_includes_thesis_customization_issue_hint():
    release = {
        "tag_name": "v4.0.1",
        "published_at": "2026-03-15T23:34:20Z",
        "assets": [
            {
                "name": "thesis-smu-master-v4.0.1.zip",
                "size": 564731,
                "browser_download_url": "https://example.com/thesis-smu-master-v4.0.1.zip",
            },
            {
                "name": "thesis-smu-master-Overleaf-v4.0.1.zip",
                "size": 576416,
                "browser_download_url": "https://example.com/thesis-smu-master-Overleaf-v4.0.1.zip",
            },
            {
                "name": "thesis-sysu-doctor-v4.0.1.zip",
                "size": 569793,
                "browser_download_url": "https://example.com/thesis-sysu-doctor-v4.0.1.zip",
            },
            {
                "name": "thesis-sysu-doctor-Overleaf-v4.0.1.zip",
                "size": 581478,
                "browser_download_url": "https://example.com/thesis-sysu-doctor-Overleaf-v4.0.1.zip",
            },
        ],
    }

    rendered = render_template_section("huangwb8/ChineseResearchLaTeX", release)

    assert "### 毕业论文模板" in rendered
    assert "如有这类需求，建议提交 [毕业论文模板定制需求]" in rendered
    assert "?template=thesis-template-customization.yml" in rendered


def test_discover_thesis_template_specs_reads_school_from_template_json(tmp_path, monkeypatch):
    thesis_dir = tmp_path / "thesis-demo-master"
    thesis_dir.mkdir()
    (thesis_dir / "template.json").write_text(
        (
            "{\n"
            '  "project_name": "thesis-demo-master",\n'
            '  "school": "示例大学",\n'
            '  "degree": "master"\n'
            "}\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(updater, "PROJECTS_DIR", tmp_path)

    specs = updater.discover_thesis_template_specs()

    assert len(specs) == 1
    assert specs[0].display_name == "thesis-demo-master"
    assert specs[0].school == "示例大学"
    assert specs[0].degree == "master"


def test_discover_thesis_template_specs_requires_template_json(tmp_path, monkeypatch):
    thesis_dir = tmp_path / "thesis-missing-meta"
    thesis_dir.mkdir()

    monkeypatch.setattr(updater, "PROJECTS_DIR", tmp_path)

    with pytest.raises(RuntimeError, match="template.json"):
        updater.discover_thesis_template_specs()


def test_render_template_section_formats_bachelor_degree(tmp_path, monkeypatch):
    thesis_dir = tmp_path / "thesis-demo-bachelor"
    thesis_dir.mkdir()
    (thesis_dir / "template.json").write_text(
        (
            "{\n"
            '  "project_name": "thesis-demo-bachelor",\n'
            '  "school": "示例学院",\n'
            '  "degree": "bachelor"\n'
            "}\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(updater, "PROJECTS_DIR", tmp_path)

    release = {
        "tag_name": "v4.0.9",
        "published_at": "2026-03-16T09:00:00Z",
        "assets": [
            {
                "name": "thesis-demo-bachelor-v4.0.9.zip",
                "size": 123456,
                "browser_download_url": "https://example.com/thesis-demo-bachelor-v4.0.9.zip",
            },
            {
                "name": "thesis-demo-bachelor-Overleaf-v4.0.9.zip",
                "size": 234567,
                "browser_download_url": "https://example.com/thesis-demo-bachelor-Overleaf-v4.0.9.zip",
            },
        ],
    }

    rendered = render_template_section("huangwb8/ChineseResearchLaTeX", release)

    assert "| [thesis-demo-bachelor](projects/thesis-demo-bachelor/) | 示例学院 | 学士 |" in rendered
