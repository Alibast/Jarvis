import json
from pathlib import Path

def load_json(path: str):
    p = Path(path)
    # utf-8-sig enlève le BOM si présent
    with p.open("r", encoding="utf-8-sig") as f:
        return json.load(f)

def save_json(path: str, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    # on écrit sans BOM
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
