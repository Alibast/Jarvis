from __future__ import annotations
import os, json
from datetime import datetime
from pathlib import Path

from io_utils.config_manager import load_config
from io_utils.logger import get_logger, info
from nestor.dialogue.session import (
    SessionState,
    build_prompt,
    maybe_call_llm,
    load_corpus_from_config,
    select_item,
)

def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

def main():
    cfg = load_config()
    log_cfg = cfg.get("logging", {})
    get_logger(log_cfg.get("file","logs/logs.txt"), log_cfg.get("level","INFO"), log_cfg.get("echo", True))

    # session & storage
    sid = os.environ.get("NESTOR_SESSION_ID","cli")
    state = SessionState(id=sid)
    items = load_corpus_from_config(cfg)

    today = datetime.now().strftime("%Y-%m-%d")
    stamp = datetime.now().strftime("%H%M%S")
    out_path = Path(f"data/sessions/{today}/{stamp}_{sid}.jsonl")
    _ensure_parent(out_path)

    # runtime options
    compact = False

    print("=== Nestor CLI ===")
    print("• ENTER = blague au hasard")
    print("• Entrez un thème pour une blague à la demande")
    print("• Commandes: :compact (toggle 2 phrases max), :help, :q\n")

    while True:
        raw = input("Thème (ENTER aléatoire, :q quitter): ").strip()

        if raw == "":
            item = select_item(items)
        elif raw.startswith(":"):
            cmd = raw.lower()
            if cmd in {":q", ":quit", ":exit"}:
                print(f"\nHistorique → {out_path.as_posix()}\nÀ bientôt! 👋")
                break
            if cmd == ":help":
                print("Commandes: :compact (toggle), :q (quitter)")
                continue
            if cmd == ":compact":
                compact = not compact
                print(f"Mode compact = {'ON (2 phrases max)' if compact else 'OFF'}")
                continue
            print("Commande inconnue. Essayez :help")
            continue
        else:
            # thème guidé par l’utilisateur
            item = {"setup": raw, "tags": ["user"]}

        # prompt
        prompt = build_prompt(item, state)
        if compact:
            prompt += "\nRéponds en 2 phrases maximum."

        # génération
        text = maybe_call_llm(prompt, cfg)
        state.history.append({"prompt": prompt, "output": text})

        # affichage
        print("\n--- Nestor ---\n" + text + "\n")

        # sauvegarde incrémentale (JSONL)
        with out_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"prompt": prompt, "output": text}, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    main()
