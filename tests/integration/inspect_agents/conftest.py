"""Minimal test bootstrap.

Ensure the repo `src/` is importable and defer to the installed `inspect_ai`
package provided by uv/pip. We intentionally do not add or stub the
`external/inspect_ai` submodule to avoid version skew.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

