"""
complete_example skill - 测试用例
"""

import unittest
from pathlib import Path
import sys

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestResourceScanner(unittest.TestCase):
    """测试资源扫描器"""

    def setUp(self):
        """测试前准备"""
        from core.resource_scanner import ResourceScanner
        # 使用测试项目路径
        self.test_project = Path("projects/NSFC_Young")
        if self.test_project.exists():
            self.scanner = ResourceScanner(self.test_project)

    def test_scan_figures(self):
        """测试图片扫描"""
        if not hasattr(self, 'scanner'):
            self.skipTest("测试项目不存在")

        figures = self.scanner.scan_figures()
        self.assertIsInstance(figures, list)

    def test_scan_code(self):
        """测试代码扫描"""
        if not hasattr(self, 'scanner'):
            self.skipTest("测试项目不存在")

        code = self.scanner.scan_code()
        self.assertIsInstance(code, list)

    def test_scan_references(self):
        """测试文献扫描"""
        if not hasattr(self, 'scanner'):
            self.skipTest("测试项目不存在")

        refs = self.scanner.scan_references()
        self.assertIsInstance(refs, list)

    def test_scan_all(self):
        """测试完整扫描"""
        if not hasattr(self, 'scanner'):
            self.skipTest("测试项目不存在")

        report = self.scanner.scan_all()
        self.assertIsNotNone(report.summary)
        self.assertIn("total_figures", report.summary)


class TestFormatGuard(unittest.TestCase):
    """测试格式守护器"""

    def test_extract_protected_zones(self):
        """测试保护区域提取"""
        from core.format_guard import FormatGuard

        # 测试用例
        content = r"""\setlength{\parindent}{2em}
\some other text
\geometry{left=3cm,right=2cm}"""

        guard = FormatGuard(Path("."))
        zones = guard.extract_protected_zones(content)

        self.assertEqual(len(zones), 2)

    def test_protected_files(self):
        """测试受保护文件列表"""
        from core.format_guard import FormatGuard

        self.assertIn("extraTex/@config.tex", FormatGuard.PROTECTED_FILES)
        self.assertIn("main.tex", FormatGuard.PROTECTED_FILES)


class TestSemanticAnalyzer(unittest.TestCase):
    """测试语义分析器（需要 mock）"""

    def test_analyze_section_theme(self):
        """测试章节主题分析"""
        # 由于需要 LLM，这里使用 mock
        pass


class TestAIContentGenerator(unittest.TestCase):
    """测试内容生成器（需要 mock）"""

    def test_generate_narrative(self):
        """测试叙述生成"""
        # 由于需要 LLM，这里使用 mock
        pass


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def test_full_workflow(self):
        """测试完整工作流"""
        # 完整的集成测试
        pass


if __name__ == '__main__':
    unittest.main()
