import requests

def _merge_cfg(cfg: dict | None, **kw):
    cfg = dict(cfg or {})
    cfg.update(kw)
    # valeurs par défaut
    cfg.setdefault("base_url", "http://localhost:1234/v1")
    cfg.setdefault("model", "openai/gpt-oss-20b")
    cfg.setdefault("temperature", 0.6)
    cfg.setdefault("top_p", 0.95)
    cfg.setdefault("max_tokens", 256)
    return cfg

def generate(prompt: str, cfg: dict | None = None, **kw) -> str:
    """
    Appel OpenAI-like /chat/completions vers LM Studio.
    Accepte:
      - generate(prompt, base_url=..., model=..., ...)
      - generate(prompt, cfg)
    """
    cfg = _merge_cfg(cfg, **kw)
    url = cfg["base_url"].rstrip("/") + "/chat/completions"
    payload = {
        "model": cfg["model"],
        "messages": (
            ([{"role": "system", "content": cfg.get("system")}]
             if cfg.get("system") else [])
            + [{"role": "user", "content": prompt}]
        ),
        "temperature": cfg["temperature"],
        "top_p": cfg["top_p"],
        "max_tokens": cfg["max_tokens"],
    }
    r = requests.post(url, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]

# compat héritée: certains anciens codes appellent complete(...)
def complete(prompt: str, cfg: dict | None = None, **kw) -> str:
    return generate(prompt, cfg, **kw)
