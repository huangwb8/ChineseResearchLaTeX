import sys
from pathlib import Path


skill_scripts_root = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(skill_scripts_root))
