"""Streamlit Cloud entrypoint.

Keeps the app importable as a package: adds `src/` to sys.path so
`dailybettingtips.*` resolves, then renders the app. `main()` must be
called explicitly on every rerun (Streamlit re-executes this script on
each interaction), rather than relying on a side-effecting import.
"""
import sys
from pathlib import Path

root = Path(__file__).parent
sys.path.insert(0, str(root / "src"))

import dailybettingtips.app as app  # noqa: E402

app.main()