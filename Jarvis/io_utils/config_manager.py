from pathlib import Path
try:
    # si le module existe déjà, on le réutilise
    from .json_loader import load_json
except Exception as e:
    raise

# chemin par défaut: Jarvis/config/config.json
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "config.json"

def get_config(path: str | None = None):
    """
    Charge un JSON de config. Si path est None, utilise Jarvis/config/config.json
    """
    p = Path(path) if path else DEFAULT_CONFIG_PATH
    return load_json(str(p))

# Compatibilité avec l'ancien code (session.py attend load_config)
def load_config(path: str | None = None):
    return get_config(path)
