"""
CLI entry point: llm-po-translate
"""
import argparse
import os
import sys

from .translator import LANG_NAMES, detect_lang_from_path, process_po
from .providers import PROVIDERS


def get_env(key: str, default: str = "") -> str:
    try:
        from decouple import config
        return config(key, default=os.environ.get(key, default))
    except ImportError:
        return os.environ.get(key, default)


def main():
    parser = argparse.ArgumentParser(
        prog="llm-po-translate",
        description="Translate a Django .po file via LLM (Anthropic, Groq)",
    )
    parser.add_argument("po_file", help="Path to the .po file")
    parser.add_argument(
        "lang", nargs="?",
        help="Target language code — auto-detected from path if omitted (e.g. es, ja, fr)",
    )
    parser.add_argument(
        "--provider", choices=list(PROVIDERS.keys()),
        default=get_env("LLM_PROVIDER", "anthropic"),
        help="LLM provider (default: $LLM_PROVIDER or 'anthropic')",
    )
    parser.add_argument(
        "--api-key",
        default=get_env("LLM_API_KEY"),
        help="API key (default: $LLM_API_KEY)",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print full error details (raw API response)",
    )
    args = parser.parse_args()

    if not os.path.exists(args.po_file):
        print(f"Error: file not found: {args.po_file}")
        sys.exit(1)

    lang = args.lang or detect_lang_from_path(args.po_file)
    if not lang:
        print("Error: could not detect language from path. Pass it explicitly.")
        sys.exit(1)

    if not args.api_key:
        print("Error: LLM_API_KEY not set (env var or --api-key)")
        sys.exit(1)

    provider = PROVIDERS[args.provider](api_key=args.api_key)
    lang_name = LANG_NAMES.get(lang, lang)

    print(f"Provider : {args.provider}")
    print(f"Language : {lang_name} ({lang})")
    print(f"File     : {args.po_file}")
    print(f"Venv entries will be stripped. Existing translations preserved.\n")

    process_po(args.po_file, lang, provider.translate, verbose=args.verbose)


if __name__ == "__main__":
    main()
