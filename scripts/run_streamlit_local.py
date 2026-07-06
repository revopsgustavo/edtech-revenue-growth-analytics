import runpy
import os
import sys
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_DEPS = ROOT.parent / ".streamlit_deps"

use_local_deps = os.environ.get("FORCE_LOCAL_STREAMLIT_DEPS") == "1"
streamlit_available = importlib.util.find_spec("streamlit") is not None

if LOCAL_DEPS.exists() and (use_local_deps or not streamlit_available):
    sys.path.insert(0, str(LOCAL_DEPS))

port = os.environ.get("STREAMLIT_PORT", "8501")

sys.argv = [
    "streamlit",
    "run",
    str(ROOT / "app" / "streamlit_app.py"),
    "--global.developmentMode",
    "false",
    "--server.headless",
    "true",
    "--server.port",
    port,
]

runpy.run_module("streamlit", run_name="__main__")
