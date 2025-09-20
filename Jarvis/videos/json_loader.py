# json_loader.py
# Adaptateur minimal. Si tu as déjà un module json_loader, tu peux le remplacer à l'identique.
import json
from pathlib import Path
from typing import Any, Dict

def load(path: str) -> Dict[str, Any]:
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)
