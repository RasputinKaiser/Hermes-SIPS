#!/usr/bin/env python3
"""Start the vendored SIPS MCP server with Hermes profile-safe paths."""
from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
HERMES_HOME = Path(os.environ.get("HERMES_HOME", "~/.hermes")).expanduser().resolve()
os.environ.setdefault("SIPS_PLUGIN_ROOT", str(ROOT))
os.environ.setdefault("PLUGIN_ROOT", str(ROOT))
os.environ.setdefault("SIPS_HOME", str(HERMES_HOME / "sips"))
os.environ.setdefault("PYTHONUNBUFFERED", "1")
sys.path.insert(0, str(SCRIPTS))
runpy.run_path(str(SCRIPTS / "harness_homebase_mcp.py"), run_name="__main__")
