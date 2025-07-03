import sys
from pathlib import Path

# Add repository root to ``sys.path`` for local package imports during tests.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
