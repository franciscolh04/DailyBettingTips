"""Streamlit Cloud entrypoint.

Keeps the app importable as a package: adds `src/` to sys.path so
`dailybettingtips.*` resolves, then launches the real app UI.
"""
import sys
from pathlib import Path

root = Path(__file__).parent
sys.path.insert(0, str(root / "src"))

import dailybettingtips.app  # noqa: E402  (runs the UI)