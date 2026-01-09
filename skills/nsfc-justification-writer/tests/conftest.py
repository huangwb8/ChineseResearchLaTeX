import os
import sys
from pathlib import Path


skill_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(skill_root))

# 测试环境避免受用户全局 override.yaml 影响
os.environ.setdefault("NSFC_JUSTIFICATION_WRITER_DISABLE_USER_OVERRIDE", "1")
