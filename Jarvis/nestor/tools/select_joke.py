import random

def pick(items):
    if not items:
        raise RuntimeError('empty corpus')
    return random.choice(items)
