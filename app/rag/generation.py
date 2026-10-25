import anthropic

from app.core.config import settings


# ── GÉNÉRATION DE TEXTE VIA CLAUDE (remplace Mistral chat, en rate limit) ─────

def get_claude_client():
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY manquante : impossible de générer du texte.")
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def generate_text(prompt):
    # Génère une réponse texte avec Claude Haiku à partir d'un prompt unique
    client = get_claude_client()
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text
