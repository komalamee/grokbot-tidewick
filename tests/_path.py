import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "fixed-files" / "engine"
CHAPTERS = ROOT / "fixed-files" / "chapters"
sys.path.insert(0, str(ENGINE))
