#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
master_nestor.py
----------------
Fichier maître (orchestrateur) pour Nestor.
Rôles :
- Charge la config via json_loader.load()
- Démarre le lecteur d'avatar vidéo (EmotionPlayer depuis nestor_player.py)
- Ouvre une source d'entrée (console ou microphone) pour capter la parole/texte
- Route le texte -> émotion via EmotionRouter (optionnel)
- Génère une réponse (stub) et la parle via TTS (pyttsx3 si dispo)
- Déclenche l'animation correspondante (emotion -> video)

Dépendances potentielles :
    pip install python-vlc pyttsx3 SpeechRecognition pyaudio
"""

import os
import sys
import time
from typing import Optional

try:
    from json_loader import load as load_json
except Exception as e:
    print("ERREUR: json_loader introuvable. Place json_loader.py à côté de ce script.", file=sys.stderr)
    raise

try:
    from nestor_player import EmotionPlayer
except Exception as e:
    print("ERREUR: nestor_player.py introuvable ou import impossible.", file=sys.stderr)
    raise

try:
    from emotion_router import EmotionRouter
except Exception:
    EmotionRouter = None  # Router optionnel

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

class ConsoleInput:
    def listen(self) -> Optional[str]:
        try:
            line = input("> ")
            return line.strip()
        except EOFError:
            time.sleep(0.2)
            return None
        except KeyboardInterrupt:
            return None

class MicrophoneInput:
    def __init__(self):
        try:
            import speech_recognition as sr
            self.sr = sr
            self.recognizer = sr.Recognizer()
            self.mic = sr.Microphone()
        except Exception as e:
            print("[AudioInput] SpeechRecognition/PyAudio indisponible, repasse en console.", file=sys.stderr)
            self.sr = None

    def listen(self) -> Optional[str]:
        if not self.sr:
            return None
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
            print("(Écoute...)")
            audio = self.recognizer.listen(source, phrase_time_limit=8)
        try:
            text = self.recognizer.recognize_google(audio, language="fr-FR")
            return text.strip()
        except Exception as e:
            print("[AudioInput] Reconnaissance échouée:", e, file=sys.stderr)
            return ""

def generate_reply(user_text: str) -> str:
    if not user_text:
        return "Oui, je suis là."
    if user_text.endswith("?"):
        return "Bonne question. Laisse-moi y penser une seconde."
    return "Je t'écoute. " + user_text

class NestorMaster:
    def __init__(self, master_config_path: str):
        self.cfg = load_json(master_config_path)

        self.router = None
        if self.cfg.get("routing", {}).get("use_router", True) and EmotionRouter is not None:
            emo_json_path = self.cfg["paths"]["emotions"]
            cfg_for_router = load_json(emo_json_path)
            self.router = EmotionRouter(cfg_for_router)

        tts_backend = self.cfg.get("audio", {}).get("tts_backend", "pyttsx3")
        tts_voice = self.cfg.get("audio", {}).get("voice", None)
        tts_rate = self.cfg.get("audio", {}).get("rate", 175)
        self.tts = TTS(backend=tts_backend, voice=tts_voice, rate=tts_rate)

        audio_input_mode = self.cfg.get("audio", {}).get("input", "console")
        if audio_input_mode == "microphone":
            self.input = MicrophoneInput()
            if getattr(self.input, "sr", None) is None:
                print("[Master] Micro indisponible, bascule en console.")
                self.input = ConsoleInput()
        else:
            self.input = ConsoleInput()

        emotions_json = self.cfg["paths"]["emotions"]
        self.player = EmotionPlayer(emotions_json)

        self.print_logs = bool(self.cfg.get("ui", {}).get("print_logs", True))

    def route_emotion(self, text: str):
        if not self.router:
            return None
        emo, score = self.router.analyze(text or "")
        if emo and emo != "idle":
            if self.print_logs:
                print(f"[Router] -> {emo} (score: {score:.2f})")
            return emo
        return None

    def handle_text(self, text: str):
        if text is None:
            return False
        text = text.strip()
        if text.lower() in ("quit", "exit"):
            return False

        emo = self.route_emotion(text)
        if emo:
            self.player.trigger_emotion(emo)

        reply = generate_reply(text)

        emo_from_reply = self.route_emotion(reply)
        if emo_from_reply:
            self.player.trigger_emotion(emo_from_reply)

        self.tts.say(reply)
        return True

    def run(self):
        print("Nestor Master prêt. Tape 'quit' pour sortir.")
        while True:
            text = self.input.listen()
            if not self.handle_text(text):
                break

def main():
    if len(sys.argv) < 2:
        print("Usage: python master_nestor.py master_config.json", file=sys.stderr)
        sys.exit(1)
    cfg_path = sys.argv[1]
    if not os.path.exists(cfg_path):
        print(f"Config introuvable: {cfg_path}", file=sys.stderr)
        sys.exit(1)

    master = NestorMaster(cfg_path)
    try:
        master.run()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
