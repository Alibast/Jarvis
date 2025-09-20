# Nestor M3 (pack prêt-à-tester)

## Lancer un test rapide
1. Ouvre un terminal **dans le dossier qui contient `nestor/` et `toolkit/`**.
2. Assure-toi que les paquets Python sont reconnus :
   ```powershell
   python -m nestor.dialogue.session
   ```

Tu devrais voir un `--- OUTPUT ---` et un fichier `logs/logs.txt` créé avec les entrées de log.

## Configuration
- Fichier: `nestor/config/config.json`
  - `data_path`: chemin vers le corpus (`toolkit/data/sitcom.jsonl` par défaut)
  - `logging.file`: chemin du fichier log (`logs/logs.txt`)
  - `provider`: "local" pour le stub LLM

## Structure
- `nestor/` (code runtime)
- `toolkit/` (données et préviews)
- `logs/` (créé à l'écriture)