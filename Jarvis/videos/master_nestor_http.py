#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
master_nestor_http.py
---------------------
Serveur HTTP + WebSocket pour piloter l'avatar de Nestor.
- Charge la config maître (chemins, audio, routing)
- Instancie EmotionPlayer (vidéos) + EmotionRouter (texte -> émotion) + TTS
- Expose une API HTTP pour:
    GET  /health
    GET  /emotions
    POST /trigger   { "emotion": "joie" }
    POST /route     { "text": "..." }
    POST /say       { "text": "..." }
    POST /chat      { "text": "..." }  # route + joue + TTS + réponse

- Expose un WebSocket (optionnel) :
    ws://HOST:WS_PORT/ws
    Messages JSON:
      {"cmd":"trigger","emotion":"joie"}
      {"cmd":"route","text":"..."}  -> {"emotion":"joie","score":1.2}
      {"cmd":"say","text":"..."}
      {"cmd":"chat","text":"..."}   -> {"reply":"...", "emotion_in":"...", "emotion_reply":"..."}

Dépendances:
    pip install flask python-vlc pyttsx3 websockets
(Installe VLC sur la machine)
"""

import os
import sys
import json
import time
import threading
from typing import Optional, Dict, Any, Tuple

from flask import Flask, request, jsonify

# Imports locaux (assure-toi que ces fichiers sont dans le PYTHONPATH ou même dossier)
from json_loader import load as load_json
from nestor_player import EmotionPlayer
try:
    from emotion_router import EmotionRouter
except Exception:
    EmotionRouter = None

# ---------- TTS ----------
class TTS:
    def __init__(self, backend="pyttsx3", voice=None, rate=175):
        self.backend = backend
        self.voice = voice
        self.rate = rate
        self.engine = None
        if backend == "pyttsx3":
            try:
                import pyttsx3
                self.engine = pyttsx3.init()
                if rate:
                    self.engine.setProperty("rate", rate)
                if voice:
                    for v in self.engine.getProperty("voices"):
                        if voice.lower() in (v.name or "").lower():
                            self.engine.setProperty("voice", v.id)
                            break
            except Exception as e:
                print("[TTS] pyttsx3 indisponible, passage en mode dummy.", file=sys.stderr)
                self.backend = "dummy"

    def say(self, text: str):
        if self.backend == "dummy" or self.engine is None:
            print(f"[TTS] {text}")
            return
        self.engine.say(text)
        self.engine.runAndWait()

# ---------- Réponse LLM (stub) ----------
def generate_reply(user_text: str) -> str:
    if not user_text:
        return "Oui, je suis là."
    if user_text.endswith("?"):
        return "Bonne question. Laisse-moi y penser une seconde."
    return "Je t'écoute. " + user_text

# ---------- Orchestrateur partagé ----------
class NestorCore:
    def __init__(self, master_config_path: str):
        self.cfg = load_json(master_config_path)

        # Router (optionnel)
        self.router = None
        if self.cfg.get("routing", {}).get("use_router", True) and EmotionRouter is not None:
            emo_json_path = self.cfg["paths"]["emotions"]
            cfg_for_router = load_json(emo_json_path)
            self.router = EmotionRouter(cfg_for_router)

        # TTS
        tts_backend = self.cfg.get("audio", {}).get("tts_backend", "pyttsx3")
        tts_voice = self.cfg.get("audio", {}).get("voice", None)
        tts_rate = self.cfg.get("audio", {}).get("rate", 175)
        self.tts = TTS(backend=tts_backend, voice=tts_voice, rate=tts_rate)

        # Player (vidéos)
        emotions_json = self.cfg["paths"]["emotions"]
        self.player = EmotionPlayer(emotions_json)

        # Logs
        self.print_logs = bool(self.cfg.get("ui", {}).get("print_logs", True))

    def route_emotion(self, text: str) -> Tuple[Optional[str], float]:
        if not self.router:
            return None, 0.0
        emo, score = self.router.analyze(text or "")
        if emo and emo != "idle":
            if self.print_logs:
                print(f"[Router] -> {emo} (score: {score:.2f})")
            return emo, score
        return None, 0.0

    def trigger(self, emotion: str) -> bool:
        if not emotion:
            return False
        self.player.trigger_emotion(emotion)
        return True

    def say(self, text: str):
        self.tts.say(text)

    def chat(self, text: str) -> Dict[str, Any]:
        emo_in, score_in = self.route_emotion(text or "")
        if emo_in:
            self.player.trigger_emotion(emo_in)

        reply = generate_reply(text or "")

        emo_reply, score_reply = self.route_emotion(reply)
        if emo_reply:
            self.player.trigger_emotion(emo_reply)

        self.tts.say(reply)

        return {
            "reply": reply,
            "emotion_in": emo_in,
            "emotion_in_score": score_in,
            "emotion_reply": emo_reply,
            "emotion_reply_score": score_reply
        }

# ---------- HTTP (Flask) ----------
def create_app(core: NestorCore) -> Flask:
    app = Flask(__name__)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/emotions")
    def emotions():
        # Lire les émotions depuis le player
        try:
            emos = []
            for name, meta in core.player.media_map.items():
                emos.append({
                    "name": name,
                    "file": meta.get("file"),
                    "loop": bool(meta.get("loop")),
                    "description": meta.get("description", "")
                })
            return jsonify({"emotions": sorted(emos, key=lambda x: x["name"])})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.post("/trigger")
    def trigger():
        data = request.get_json(force=True, silent=True) or {}
        emotion = data.get("emotion")
        if not emotion:
            return jsonify({"error": "champ 'emotion' requis"}), 400
        core.trigger(emotion)
        return jsonify({"ok": True, "emotion": emotion})

    @app.post("/route")
    def route():
        data = request.get_json(force=True, silent=True) or {}
        text = data.get("text", "")
        emo, score = core.route_emotion(text)
        return jsonify({"emotion": emo or "idle", "score": float(score)})

    @app.post("/say")
    def say():
        data = request.get_json(force=True, silent=True) or {}
        text = data.get("text", "")
        core.say(text)
        return jsonify({"ok": True})

    @app.post("/chat")
    def chat():
        data = request.get_json(force=True, silent=True) or {}
        text = data.get("text", "")
        result = core.chat(text)
        return jsonify(result)

    return app

# ---------- WebSocket (websockets) ----------
async def ws_handler(websocket, path, core: NestorCore):
    import json as _json
    await websocket.send(_json.dumps({"hello": "nestor", "status": "ready"}))
    try:
        async for message in websocket:
            try:
                data = _json.loads(message)
            except Exception:
                await websocket.send(_json.dumps({"error": "invalid_json"}))
                continue
            cmd = (data.get("cmd") or "").lower()
            if cmd == "trigger":
                emo = data.get("emotion")
                core.trigger(emo)
                await websocket.send(_json.dumps({"ok": True, "emotion": emo}))
            elif cmd == "route":
                text = data.get("text", "")
                emo, score = core.route_emotion(text)
                await websocket.send(_json.dumps({"emotion": emo or "idle", "score": float(score)}))
            elif cmd == "say":
                text = data.get("text", "")
                core.say(text)
                await websocket.send(_json.dumps({"ok": True}))
            elif cmd == "chat":
                text = data.get("text", "")
                res = core.chat(text)
                await websocket.send(_json.dumps(res))
            else:
                await websocket.send(_json.dumps({"error": "unknown_cmd"}))
    except Exception as e:
        # connexion interrompue
        return

def start_ws_server(core: NestorCore, host: str, port: int):
    import asyncio
    import websockets

    async def _main():
        async def _handler(ws, path):
            await ws_handler(ws, path, core)
        server = await websockets.serve(_handler, host, port)
        print(f"[WS] running on ws://{host}:{port}/ws")
        await server.wait_closed()

    loop = asyncio.new_event_loop()
    t = threading.Thread(target=loop.run_until_complete, args=(_main(),), daemon=True)
    t.start()
    return t

# ---------- Entrée principale ----------
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="Chemin du master_config.json")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5005)
    parser.add_argument("--ws-port", type=int, default=8765, help="Port WebSocket (0 pour désactiver)")
    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(f"Config introuvable: {args.config}", file=sys.stderr)
        sys.exit(1)

    core = NestorCore(args.config)

    # Démarrer WS si demandé
    if args.ws_port and args.ws_port > 0:
        try:
            start_ws_server(core, args.host, args.ws_port)
        except Exception as e:
            print("[WS] Impossible de démarrer le serveur WebSocket:", e, file=sys.stderr)

    app = create_app(core)
    print(f"[HTTP] running on http://{args.host}:{args.port}")
    # threaded=True pour simultanéité simple
    app.run(host=args.host, port=args.port, threaded=True)

if __name__ == "__main__":
    main()
