from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

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

    assert "[thesis-smu-master](projects/thesis-smu-master/)" in rendered
    assert "[thesis-sysu-doctor](projects/thesis-sysu-doctor/)" in rendered
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
