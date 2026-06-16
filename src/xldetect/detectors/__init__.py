"""Pluggable structural detection strategies.

Each module here exports a single focused function that operates purely on a
:class:`xldetect.grid.Grid` (and plain rectangle bounds), never on a live
``openpyxl`` worksheet. This keeps every heuristic independently testable.
"""

from __future__ import annotations

from .regions import RawRegion, detect_regions
from .headers import HeaderResult, detect_header
from .decorative import TrimResult, trim_decorative
from .merged import merged_in_region, is_banner_row

__all__ = [
    "RawRegion",
    "detect_regions",
    "HeaderResult",
    "detect_header",
    "TrimResult",
    "trim_decorative",
    "merged_in_region",
    "is_banner_row",
]
