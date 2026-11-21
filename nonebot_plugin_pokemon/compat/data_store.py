"""数据目录兼容层。"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union

from ..paths import data_root


def get_res_path(path: Optional[Union[str, List[str], Path]] = None) -> Path:
    root = data_root()
    if path is None:
        return root
    if isinstance(path, Path):
        path.mkdir(parents=True, exist_ok=True)
        return path
    if isinstance(path, str):
        result = root / path
    else:
        result = root.joinpath(*path)
    result.mkdir(parents=True, exist_ok=True)
    return result


__all__ = ["get_res_path"]
