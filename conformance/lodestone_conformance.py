#!/usr/bin/env python3
"""The suite's earlier name, kept so existing commands keep working. Use carrick_conformance.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from carrick_conformance import *  # noqa: E402,F401,F403
from carrick_conformance import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
