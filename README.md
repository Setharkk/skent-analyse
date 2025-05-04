![Build](https://github.com/Setharkk/reverse-platform/actions/workflows/audit.yml/badge.svg)
![CodeQL](https://github.com/Setharkk/reverse-platform/actions/workflows/codeql.yml/badge.svg)
![Visual Tests](https://github.com/Setharkk/reverse-platform/actions/workflows/playwright.yml/badge.svg)

# README for reverse-platform

## Stack
- FastAPI backend (Python 3.12)
- Streamlit frontend
- Postgres 15
- Redis 7
- Docker Compose orchestration

## Usage
1. Copier `.env.example` en `.env` et remplir les clés.
2. Lancer tous les services :
   ```sh
   make dev
   ```
3. Accéder à :
   - API : http://localhost:8000
   - Frontend : http://localhost:8501

## Installation (Poetry)

Pour installer toutes les dépendances (prod + dev) :

```bash
cd app
poetry install --with dev
pre-commit install
```

Cela installe l’environnement Python complet, les hooks de qualité de code, et prépare le projet pour le développement.

## Déploiement Kubernetes

Pour déployer la plateforme sur un cluster Kubernetes :

```sh
helm install reverse-platform ./infra/k8s
```

Vous pouvez ajuster les images et ressources via `values.yaml` ou en ligne de commande avec `--set`.

## Tests, lint, format
- `make test` — tests backend
- `make lint` — flake8
- `make format` — black

## Prompt Standards

All agent prompts must follow the [Expert Prompt Guidelines](app/agents/prompts/_guidelines.md):
- Message hierarchy: system → context → user → assistant
- Techniques: ReACT, Chain-of-Thought, Self-Reflection (max 2), Force-Functions (JSON schema validation)
- Style: concise ≤ 300 words (except diff), always cite files+lines, unified-diff for patches
- Scoring: severity 0–10, confidence 0–1
- Finish-reasons: “final_patch” or “insufficient_context”
