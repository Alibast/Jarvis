#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Emotion Router (keyword-based)
- Charge un JSON (même structure que emotions_with_triggers.sample.json).
- Calcule un score par émotion en fonction des mots/phrases présents.
- Renvoie l'émotion gagnante si score >= min_score_to_trigger, sinon 'fallback'.
"""
import json, re, time, unicodedata
from typing import Dict, Tuple

def strip_accents(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

class EmotionRouter:
    def __init__(self, cfg: Dict):
        self.cfg = cfg
        self.last_trigger_ts = 0.0

        self.strategy = cfg.get("routing", {}).get("strategy", {})
        self.min_score = float(self.strategy.get("min_score_to_trigger", 1.0))
        self.tie_breaker = self.strategy.get("tie_breaker", "priority")
        self.fallback = self.strategy.get("fallback", "idle")
        self.cooldown = float(self.strategy.get("cooldown_seconds", 2.0))

        self.routing = cfg.get("routing", {}).get("emotions", {})
        self.priority = {emo: int(data.get("priority", 0)) for emo, data in self.routing.items()}

    def analyze(self, text: str) -> Tuple[str, float]:
        now = time.time()
        if now - self.last_trigger_ts < self.cooldown:
            return self.fallback, 0.0

        # normaliser
        t = strip_accents(text.lower())

        # Scorer
        scores = {}
        for emo, data in self.routing.items():
            score = 0.0
            for kw, w in data.get("keywords", {}).items():
                if strip_accents(kw.lower()) in t.split():
                    score += float(w)
            for ph, w in data.get("phrases", {}).items():
                if strip_accents(ph.lower()) in t:
                    score += float(w)
            scores[emo] = score

        # meilleur
        best_emo, best_score = self._pick_best(scores)
        if best_score >= self.min_score:
            self.last_trigger_ts = now
            return best_emo, best_score
        return self.fallback, 0.0

    def _pick_best(self, scores: Dict[str, float]) -> Tuple[str, float]:
        best_emo = None
        best_score = -1.0
        for emo, s in scores.items():
            if s > best_score:
                best_emo, best_score = emo, s
            elif s == best_score and s > 0:
                if self.tie_breaker == "priority":
                    if self.priority.get(emo, 0) > self.priority.get(best_emo, 0):
                        best_emo, best_score = emo, s
        return best_emo or self.fallback, best_score
