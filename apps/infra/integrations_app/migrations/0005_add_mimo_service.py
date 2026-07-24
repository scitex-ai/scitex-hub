# Add "mimo" (Xiaomi MiMo) to IntegrationConnection.service choices so the
# terminal model-provider picker can store per-user MiMo API keys in the
# existing llm_app key store (feat/terminal-model-provider).
# Choices-only change — no database schema alteration.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("integrations_app", "0004_add_llm_providers"),
    ]

    operations = [
        migrations.AlterField(
            model_name="integrationconnection",
            name="service",
            field=models.CharField(
                choices=[
                    ("orcid", "ORCID"),
                    ("github", "GitHub"),
                    ("gitlab", "GitLab"),
                    ("zotero", "Zotero"),
                    ("overleaf", "Overleaf"),
                    ("slack", "Slack"),
                    ("discord", "Discord"),
                    ("anthropic", "Anthropic (Claude)"),
                    ("openai", "OpenAI (GPT)"),
                    ("gemini", "Google (Gemini)"),
                    ("mistral", "Mistral AI"),
                    ("xai", "xAI (Grok)"),
                    ("deepseek", "DeepSeek"),
                    ("mimo", "Xiaomi MiMo"),
                    ("openrouter", "OpenRouter"),
                    ("ollama", "Ollama (local)"),
                    ("local_llm", "Local LLM (Ollama/LM Studio)"),
                ],
                max_length=20,
            ),
        ),
    ]
