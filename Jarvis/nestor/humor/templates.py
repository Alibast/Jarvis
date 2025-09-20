def build_prompt(setup: str, punch: str | None = None) -> str:
    base = 'Tu es Nestor, ado ophanim/cartoon.\n'
    if punch:
        return base + f'Blague:\nSetup: {setup}\nPunchline: {punch}\n'
    else:
        return base + 'Complète avec humour: ' + setup
