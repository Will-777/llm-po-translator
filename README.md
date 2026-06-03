# llm-po-translator

Automatically translate Django `.po` files via LLM — Anthropic (Claude) or Groq (Llama).

- Skips already-translated entries
- Strips venv/site-packages pollution
- Rate limit detection: silences output after 3 consecutive 429s, counts silently, re-run to resume
- Auto-detects language from path (`locale/es/LC_MESSAGES/django.po` → `es`)
- Works as a **CLI** or a **Django management command**

## Install

```bash
pip install llm-po-translator            # no provider (bring your own)
pip install 'llm-po-translator[groq]'    # + Groq
pip install 'llm-po-translator[anthropic]' # + Anthropic
pip install 'llm-po-translator[all]'     # both
```

## Setup

Set your API key and provider in your environment (or `.env`):

```
LLM_PROVIDER=groq         # anthropic | groq
LLM_API_KEY=gsk_...       # Groq key (gsk_...) or Anthropic key (sk-ant-...)
```

## Usage

### CLI

```bash
# Auto-detect language from path
llm-po-translate locale/es/LC_MESSAGES/django.po

# Explicit language
llm-po-translate locale/es/LC_MESSAGES/django.po es

# Override provider
llm-po-translate locale/ja/LC_MESSAGES/django.po --provider anthropic

# Verbose (raw API errors)
llm-po-translate locale/fr/LC_MESSAGES/django.po --verbose
```

### Django management command

Add `llm_po_translator` to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    ...
    "llm_po_translator",
]
```

Then:

```bash
# Auto-discover all locale/*/LC_MESSAGES/django.po
python manage.py translate_po

# Single file
python manage.py translate_po locale/es/LC_MESSAGES/django.po

# Override provider
python manage.py translate_po --provider groq
```

## Providers

| Provider | Model | Install |
|---|---|---|
| `anthropic` | claude-haiku-4-5-20251001 | `pip install anthropic` |
| `groq` | llama-3.3-70b-versatile | `pip install groq` |

## License

MIT
