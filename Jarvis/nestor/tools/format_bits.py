def shorten(s: str, n: int = 140) -> str:
    return s if len(s)<=n else s[:n-1]+'…'
