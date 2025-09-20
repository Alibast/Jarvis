# --- session.py (M3 propre : logger + orchestration légère) ---
from __future__ import annotations

import os, json, random, traceback
from typing import Any, Dict, List
from dataclasses import dataclass, field

from io_utils.config_manager import load_config
from io_utils.logger import get_logger, info, debug, warn, error


# --------------------------
# État de session
# --------------------------
@dataclass
class SessionState:
    id: str
    chakra: str = "racine"
    history: List[Dict[str, Any]] = field(default_factory=list)
    rating: str = "G"


# --------------------------
# Config + Logger
# --------------------------
cfg = load_config()

# -- LLM config résolue (une fois, en haut)
llm_cfg  = cfg.get("llm", {})
PROVIDER = llm_cfg.get("provider") or llm_cfg.get("backend") or "lmstudio"
BASE_URL = llm_cfg.get("base_url", "http://localhost:1234/v1")
MODEL    = llm_cfg.get("model", "openai/gpt-oss-20b")
TEMP     = llm_cfg.get("temperature", 0.6)
TOP_P    = llm_cfg.get("top_p", 0.95)
MAXTOK   = llm_cfg.get("max_tokens", 512)

# -- Logging config + init
log_cfg = cfg.get("logging", {})
get_logger(
    log_cfg.get("file", "logs/logs.txt"),
    log_cfg.get("level", "INFO"),
    log_cfg.get("echo", True),
)

# Log d’ouverture (préfixes pour éviter collisions de clés)
info("Session start", llm_provider=PROVIDER, llm_model=MODEL, llm_base_url=BASE_URL)

style_cfg   = cfg.get("style", {})
COMPACT     = bool(style_cfg.get("compact_default", False))
TARGET_SENT = int(style_cfg.get("target_sentences", 2))
USE_EMOJI   = bool(style_cfg.get("emoji", True))

# --------------------------
# Lecture corpus
# --------------------------
def _read_json(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get("items", [])
    if not isinstance(data, list):
        raise ValueError("Corpus JSON invalide: attendu une liste d'objets.")
    return data

def _read_jsonl(path: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items

def load_corpus_from_config(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    path = cfg.get("data_path") or "toolkit/data/sitcom.jsonl"
    if not os.path.exists(path):
        alt = "toolkit/data/sitcom.json"
        warn("Corpus path not found, trying fallback", missing=path, fallback=alt)
        path = alt
    if path.endswith(".jsonl"):
        items = _read_jsonl(path)
    else:
        items = _read_json(path)
    info("Corpus loaded", path=path, count=len(items))
    return items


# --------------------------
# Prompting
# --------------------------
def select_item(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not items:
        raise RuntimeError("Corpus vide : impossible de sélectionner un item.")
    return random.choice(items)

def build_prompt(item: Dict[str, Any], state: SessionState) -> str:
    setup = item.get("setup") or item.get("text") or ""
    punch = item.get("punch") or item.get("answer") or ""

    base = (
        "Tu es Nestor, ado ophanim/cartoon sympa. "
        f"Rating: {state.rating}. Garde un ton bienveillant et drôle.\n\n"
    )

    # ✅ Ajouts de style AVANT les retours
    if COMPACT:
        base += f"Réponds en {TARGET_SENT} phrases maximum.\n"
    if not USE_EMOJI:
        base += "N'utilise pas d'emojis.\n"

    if setup and punch:
        return base + f"Blague:\nSetup: {setup}\nPunchline: {punch}\n"
    elif setup:
        return base + f"Complète ou remixe avec humour:\n{setup}\n"
    else:
        return base + "Fais une petite blague propre et originale."



# --------------------------
# Appel LLM (vrai appel LM Studio, config globale)
# --------------------------
def maybe_call_llm(prompt: str, cfg: Dict[str, Any]) -> str:
    try:
        from nestor.llm import client as llm_client  # import absolu et clair

        out = llm_client.generate(
            prompt,
            base_url=BASE_URL,
            model=MODEL,
            temperature=TEMP,
            top_p=TOP_P,
            max_tokens=MAXTOK,
            system=None,  # persona déjà mis dans build_prompt()
        )

        # Normaliser la sortie
        if isinstance(out, dict):
            return out.get("text") or out.get("content") or json.dumps(out, ensure_ascii=False)
        return str(out)

    except Exception as e:
        error("LLM call failed; using fallback", err=str(e), tb=traceback.format_exc())
        return f"(fallback LLM OFF) {prompt}"


# --------------------------
# Orchestration
# --------------------------
def run_once(state: SessionState) -> str:
    try:
        items = load_corpus_from_config(cfg)
        item = select_item(items)
        info("Selected joke", joke_id=item.get("id"), tags=item.get("tags", []))
        prompt = build_prompt(item, state)
        debug("Prompt built", size=len(prompt))
        text = maybe_call_llm(prompt, cfg)
        info("Generation ok", chars=len(text))
        state.history.append({"prompt": prompt, "output": text})
        return text
    except Exception as e:
        error("Unhandled exception in run_once", err=str(e), tb=traceback.format_exc())
        raise


# --------------------------
# Entrée principale
# --------------------------
if __name__ == "__main__":
    sid = os.environ.get("NESTOR_SESSION_ID", "local")
    st = SessionState(id=sid)
    output = run_once(st)
    print("\n--- OUTPUT ---\n" + output)
