# Reverse Platform — Expert Prompt Guidelines

## Message Hierarchy
- system → context → user → assistant

## Techniques
- ReACT (Reason + Act)
- Chain-of-Thought (CoT)
- Self-Reflection loop (max 2 itérations)
- Force-Functions (JSON schema validation)

## Style
- Réponse concise ≤ 300 mots (sauf diff)
- Toujours citer fichiers + lignes
- Patch au format unified-diff

## Scoring
- severity: 0–10
- confidence: 0–1

## Finish-reasons
- “final_patch” ou “insufficient_context”
