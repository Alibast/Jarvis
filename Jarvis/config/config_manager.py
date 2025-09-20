from __future__ import annotations
import os, json
from typing import Any, Dict

def _default_config_path() -> str:
    here = os.path.dirname(__file__)
    default_path = os.path.normpath(os.path.join(here, "..", "config", "config.json"))
    return os.environ.get("NESTOR_CONFIG", default_path)

def load_config(path: str | None = None) -> Dict[str, Any]:
    path = path or _default_config_path()
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)