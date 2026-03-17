from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
ISSUE_TEMPLATE_DIR = REPO_ROOT / ".github" / "ISSUE_TEMPLATE"


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def get_body_item_by_id(form: dict, item_id: str) -> dict:
    for item in form.get("body", []):
        if item.get("id") == item_id:
            return item
    raise AssertionError(f"未找到表单字段：{item_id}")


def test_issue_template_config_exists_and_links_contribution_guide():
    config = load_yaml(ISSUE_TEMPLATE_DIR / "config.yml")

    assert config["blank_issues_enabled"] is True
    assert any(
        "developer-contribution-guide.md" in link["url"]
        for link in config.get("contact_links", [])
    )


def test_all_expected_issue_forms_exist():
    expected_files = {
        "paper-template-customization.yml",
        "thesis-template-customization.yml",
        "template-bug-report.yml",
    }

    actual_files = {path.name for path in ISSUE_TEMPLATE_DIR.glob("*.yml")}

    assert expected_files.issubset(actual_files)


def test_paper_and_thesis_customization_forms_collect_baseline_decisions():
    paper_form = load_yaml(ISSUE_TEMPLATE_DIR / "paper-template-customization.yml")
    thesis_form = load_yaml(ISSUE_TEMPLATE_DIR / "thesis-template-customization.yml")

    paper_accept_item = get_body_item_by_id(paper_form, "accept_nearest_base")
    paper_format_item = get_body_item_by_id(paper_form, "format_requirements")
    thesis_accept_item = get_body_item_by_id(thesis_form, "accept_nearest_base")
    thesis_baseline_item = get_body_item_by_id(thesis_form, "baseline_status")

    assert paper_accept_item["validations"]["required"] is True
    assert paper_format_item["validations"]["required"] is True
    assert thesis_accept_item["validations"]["required"] is True
    assert thesis_baseline_item["validations"]["required"] is True


def test_generic_template_bug_form_requires_repro_context():
    form = load_yaml(ISSUE_TEMPLATE_DIR / "template-bug-report.yml")

    for item_id in (
        "product_line",
        "target_path",
        "problem_type",
        "reproduction_steps",
        "expected_result",
        "actual_result",
        "environment",
    ):
        item = get_body_item_by_id(form, item_id)
        assert item["validations"]["required"] is True
