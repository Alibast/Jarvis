from __future__ import annotations
import os, sys, json, threading, datetime
from typing import Optional

_LEVELS = {"DEBUG":10, "INFO":20, "WARN":30, "ERROR":40}
_lock = threading.Lock()
_singleton = None

class Logger:
    def __init__(self, path: str="logs/logs.txt", level: str="INFO", echo: bool=True):
        self.path = path
        self.level = _LEVELS.get(level.upper(), 20)
        self.echo = echo
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    def log(self, message: str, level: str="INFO", ctx: Optional[dict]=None):
        lvl = _LEVELS.get(level.upper(), 20)
        if lvl < self.level:
            return
        ts = datetime.datetime.now().isoformat(timespec="seconds")
        line = f"{ts} [{level.upper():5}] {message}"
        if ctx:
            try:
                line += " | " + json.dumps(ctx, ensure_ascii=False, separators=(",",":"))
            except Exception:
                pass
        with _lock:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        if self.echo:
            print(line, file=(sys.stderr if lvl>=30 else sys.stdout))

def get_logger(path: Optional[str]=None, level: str="INFO", echo: bool=True) -> Logger:
    global _singleton
    if _singleton is None:
        if path is None:
            path = os.environ.get("NESTOR_LOG_FILE", "logs/logs.txt")
        _singleton = Logger(path, level=level, echo=echo)
    return _singleton

def debug(msg, **ctx): get_logger().log(msg, "DEBUG", ctx or None)
def info(msg, **ctx):  get_logger().log(msg, "INFO",  ctx or None)
def warn(msg, **ctx):  get_logger().log(msg, "WARN",  ctx or None)
def error(msg, **ctx): get_logger().log(msg, "ERROR", ctx or None)