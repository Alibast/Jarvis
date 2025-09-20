from io_utils.config_manager import load_config
from nestor.llm import client as c
import traceback

cfg = load_config()["llm"]
print("Model:", cfg["model"])
try:
    print("Reply:", c.generate("Répond exactement: NESTOR-OK", **cfg))
except Exception as e:
    print("ERR:", e)
    print(traceback.format_exc())
