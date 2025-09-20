#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nestor Emotion Video Player
---------------------------
- Plays an "idle" video in a loop by default.
- On receiving an emotion trigger (typed in console), plays that emotion video once.
- After the emotion video ends, returns to the idle loop automatically.

Dependencies:
    pip install python-vlc

Usage:
    python nestor_player.py emotions.json

Console commands during runtime:
    - Type an emotion name from the JSON (e.g., joie, tristesse, colere, surprise, douceur, idle)
    - Type "list" to print available emotions
    - Type "quit" to exit

Notes:
    - The script will open a VLC player window. You can adjust fullscreen/volume flags below if needed.
    - Video files can be absolute or relative to the JSON file directory.
"""

import json
import os
import sys
import threading
import queue
import time
from typing import Dict, Any

try:
    import vlc  # python-vlc
except ImportError as e:
    print("Erreur: python-vlc n'est pas installé. Installe-le avec: pip install python-vlc", file=sys.stderr)
    raise

class EmotionPlayer:
    def __init__(self, config_path: str):
        self.config_path = os.path.abspath(config_path)
        self.base_dir = os.path.dirname(self.config_path)
        self.config = self._load_config(self.config_path)

        self._validate_config(self.config)
        self.media_map = self._resolve_media_paths(self.config["emotions"])

        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()

        self.current_mode = "idle"
        self.idle_name = "idle"
        self.command_q: "queue.Queue[str]" = queue.Queue()
        self.lock = threading.RLock()
        self.stop_flag = threading.Event()

        self._register_events()
        self._prepare_idle()

    def _load_config(self, path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _validate_config(self, cfg: Dict[str, Any]) -> None:
        if "emotions" not in cfg or not isinstance(cfg["emotions"], dict):
            raise ValueError('Le JSON doit contenir une clé "emotions" de type objet.')
        if "idle" not in cfg["emotions"]:
            raise ValueError('La clé "idle" est requise dans "emotions".')
        for name, meta in cfg["emotions"].items():
            if not isinstance(meta, dict):
                raise ValueError(f'L\'entrée pour "{name}" doit être un objet avec au minimum la clé "file".')
            if "file" not in meta:
                raise ValueError(f'L\'entrée pour "{name}" doit contenir la clé "file".')

    def _resolve_media_paths(self, emotions_obj: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        out = {}
        for name, meta in emotions_obj.items():
            file_path = meta.get("file", "")
            resolved = file_path
            if not os.path.isabs(file_path):
                resolved = os.path.abspath(os.path.join(self.base_dir, file_path))
            out[name] = {
                "file": resolved,
                "loop": bool(meta.get("loop", False)),
                "description": meta.get("description", ""),
            }
        return out

    def _register_events(self):
        events = self.player.event_manager()
        events.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_media_end)

    def _on_media_end(self, event):
        with self.lock:
            if self.current_mode != self.idle_name:
                self._play_idle()
            else:
                self._play_idle()

    def _prepare_idle(self):
        if self.idle_name not in self.media_map:
            raise ValueError('Aucune entrée "idle" trouvée dans la configuration.')
        self._play_idle()

    def _make_media(self, filepath: str) -> "vlc.Media":
        media = self.instance.media_new(filepath)
        return media

    def _play_media(self, name: str, loop: bool = False):
        info = self.media_map[name]
        path = info["file"]
        if not os.path.exists(path):
            print(f'[AVERTISSEMENT] Fichier introuvable pour "{name}": {path}', file=sys.stderr)
        media = self._make_media(path)
        self.player.set_media(media)
        if loop:
            media.add_option("input-repeat=-1")
        self.player.play()
        time.sleep(0.05)

    def _play_idle(self):
        self.current_mode = self.idle_name
        self._play_media(self.idle_name, loop=True)

    def trigger_emotion(self, name: str):
        with self.lock:
            if name not in self.media_map:
                print(f'[INFO] Émotion inconnue: "{name}". Tape "list" pour voir les options.')
                return
            if name == self.idle_name:
                self._play_idle()
                return
            self.current_mode = name
            self._play_media(name, loop=False)

    def list_emotions(self):
        print("Émotions disponibles:")
        for k in sorted(self.media_map.keys()):
            meta = self.media_map[k]
            desc = meta.get("description", "")
            loop_str = " (loop)" if meta.get("loop", False) else ""
            print(f"  - {k}{loop_str} -> {meta['file']}{' — ' + desc if desc else ''}")

    def run(self):
        t = threading.Thread(target=self._input_thread, daemon=True)
        t.start()

        print("Nestor Emotion Player prêt. Tape 'list' pour voir les émotions, ou 'quit' pour quitter.")
        try:
            while not self.stop_flag.is_set():
                try:
                    cmd = self.command_q.get(timeout=0.2)
                except queue.Empty:
                    continue
                cmd = cmd.strip()
                if not cmd:
                    continue
                if cmd.lower() in ("quit", "exit", "q"):
                    break
                elif cmd.lower() == "list":
                    self.list_emotions()
                else:
                    self.trigger_emotion(cmd)
        finally:
            self.stop()

    def _input_thread(self):
        while not self.stop_flag.is_set():
            try:
                line = sys.stdin.readline()
            except KeyboardInterrupt:
                self.stop_flag.set()
                break
            if not line:
                time.sleep(0.1)
                continue
            self.command_q.put(line)

    def stop(self):
        self.stop_flag.set()
        try:
            self.player.stop()
        except Exception:
            pass

def main():
    if len(sys.argv) < 2:
        print("Usage: python nestor_player.py emotions.json", file=sys.stderr)
        sys.exit(1)
    config_path = sys.argv[1]
    if not os.path.exists(config_path):
        print(f"Fichier de configuration introuvable: {config_path}", file=sys.stderr)
        sys.exit(1)
    player = EmotionPlayer(config_path)
    try:
        player.run()
    except KeyboardInterrupt:
        pass
    finally:
        player.stop()

if __name__ == "__main__":
    main()
