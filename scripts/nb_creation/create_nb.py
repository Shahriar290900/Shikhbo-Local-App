"""Thin wrapper around build_index for backward-compatibility."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from build_index import build_index  # noqa: F401

if __name__ == "__main__":
    from platformdirs import user_data_dir
    index_dir = str(Path(user_data_dir("shikhbo")) / "index")
    data_dir = str(PROJECT_ROOT / "raw_data")
    build_index(index_dir, data_dir)
