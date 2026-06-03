"""
Django management command: python manage.py translate_po
"""
import os
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from llm_po_translator.translator import LANG_NAMES, detect_lang_from_path, process_po
from llm_po_translator.providers import PROVIDERS


def _get_env(key: str, default: str = "") -> str:
    try:
        from decouple import config
        return config(key, default=os.environ.get(key, default))
    except ImportError:
        return os.environ.get(key, default)


class Command(BaseCommand):
    help = "Translate .po files via LLM (Anthropic, Groq)"

    def add_arguments(self, parser):
        parser.add_argument(
            "po_files", nargs="*",
            help="Path(s) to .po file(s) — scans locale/ automatically if omitted",
        )
        parser.add_argument("--lang", help="Target language code (auto-detected from path if omitted)")
        parser.add_argument(
            "--provider", choices=list(PROVIDERS.keys()),
            default=_get_env("LLM_PROVIDER", "anthropic"),
        )
        parser.add_argument("--api-key", default=_get_env("LLM_API_KEY"))
        parser.add_argument("--verbose", action="store_true")

    def handle(self, *args, **options):
        api_key = options["api_key"]
        if not api_key:
            raise CommandError("LLM_API_KEY not set (env var or --api-key)")

        provider = PROVIDERS[options["provider"]](api_key=api_key)

        po_files = options["po_files"]
        if not po_files:
            # Auto-discover locale/ in project root
            base_dir = Path(settings.BASE_DIR)
            po_files = sorted(base_dir.glob("locale/*/LC_MESSAGES/django.po"))
            if not po_files:
                raise CommandError("No .po files found under locale/. Pass paths explicitly.")

        for po_file in po_files:
            po_file = str(po_file)
            lang = options["lang"] or detect_lang_from_path(po_file)
            if not lang:
                self.stderr.write(f"Skipping {po_file} — could not detect language")
                continue

            self.stdout.write(f"\n>>> {lang} — {po_file}")
            process_po(po_file, lang, provider.translate, verbose=options["verbose"])
