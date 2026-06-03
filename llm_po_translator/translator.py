"""
Core translation logic — provider-agnostic .po file processor.
"""

import re
import os

LANG_NAMES = {
    "af": "Afrikaans", "ar": "Arabic", "bg": "Bulgarian", "ca": "Catalan",
    "cs": "Czech", "da": "Danish", "de": "German", "el": "Greek",
    "en": "English", "es": "Spanish", "et": "Estonian", "eu": "Basque",
    "fa": "Persian", "fi": "Finnish", "fr": "French", "ga": "Irish",
    "gl": "Galician", "he": "Hebrew", "hi": "Hindi", "hr": "Croatian",
    "hu": "Hungarian", "id": "Indonesian", "it": "Italian", "ja": "Japanese",
    "ko": "Korean", "lt": "Lithuanian", "lv": "Latvian", "mk": "Macedonian",
    "ms": "Malay", "nl": "Dutch", "no": "Norwegian", "pl": "Polish",
    "pt": "Portuguese", "ro": "Romanian", "ru": "Russian", "sk": "Slovak",
    "sl": "Slovenian", "sq": "Albanian", "sr": "Serbian", "sv": "Swedish",
    "sw": "Swahili", "th": "Thai", "tr": "Turkish", "uk": "Ukrainian",
    "ur": "Urdu", "vi": "Vietnamese", "zh": "Chinese",
}

DEFAULT_SYSTEM_PROMPT = (
    "You are a professional software translator. "
    "Translate UI strings naturally for a professional audience. "
    "Rules: reply with ONLY the translated string. "
    "No quotes around it, no explanation, no alternatives. "
    "Preserve placeholders like %(name)s, %(count)d, {value} exactly as-is."
)

_NL = "\x00NL\x00"  # sentinel: survives backslash-escaping, replaced with \n at write time


# ── Output sanitization ────────────────────────────────────────────────────────

def _sanitize(text: str) -> str:
    """Normalize LLM output before writing to .po.
    Replace real newlines with sentinel (converted to \\n after .po escaping).
    """
    return text.strip().replace("\r\n", _NL).replace("\r", _NL).replace("\n", _NL)


# ── .po parsing ────────────────────────────────────────────────────────────────

def detect_lang_from_path(filepath: str) -> str | None:
    """Extract language code from a path like locale/es/LC_MESSAGES/django.po."""
    m = re.search(r'locale[/\\]([a-z]{2,5})[/\\]LC_MESSAGES', filepath)
    return m.group(1) if m else None


def extract_msgid_text(block_lines: list) -> str:
    text = ""
    in_msgid = False
    for line in block_lines:
        if line.startswith('msgid "') and not line.startswith('msgid_plural'):
            in_msgid = True
            text += line[7:-1]
        elif in_msgid and line.startswith('"') and line.endswith('"'):
            text += line[1:-1]
        elif line.startswith('msgstr') or line.startswith('msgid_plural'):
            break
    return text


def has_translation(block_lines: list) -> bool:
    msgstr_idx = next((i for i, l in enumerate(block_lines) if l.startswith('msgstr')), None)
    if msgstr_idx is None:
        return False
    val = ""
    for line in block_lines[msgstr_idx:]:
        if line.startswith('msgstr "'):
            val += line[8:-1]
        elif line.startswith('"') and line.endswith('"'):
            val += line[1:-1]
    return bool(val.strip())


def is_venv_only(block_lines: list) -> bool:
    locs = [l for l in block_lines if l.startswith('#:')]
    if not locs:
        return False
    return all('venv/' in l or 'site-packages' in l for l in locs)


def remove_venv_location_lines(block_lines: list) -> list:
    return [
        l for l in block_lines
        if not (l.startswith('#:') and ('venv/' in l or 'site-packages' in l))
    ]


def set_msgstr(block_lines: list, translation: str) -> list:
    escaped = translation.replace('\\', '\\\\').replace('"', '\\"').replace(_NL, '\\n')
    result = []
    section = "before"
    for line in block_lines:
        if line.startswith('msgid '):
            section = "msgid"
            result.append(line)
        elif line.startswith('msgid_plural'):
            section = "msgid_plural"
            result.append(line)
        elif line.startswith('msgstr['):
            if line.startswith('msgstr[0]'):
                result.append(f'msgstr[0] "{escaped}"')
            section = "msgstr"
        elif line.startswith('msgstr '):
            result.append(f'msgstr "{escaped}"')
            section = "msgstr"
        elif line.startswith('"') and line.endswith('"'):
            if section in ("msgid", "msgid_plural"):
                result.append(line)
        else:
            result.append(line)
    return result


# ── Main processor ─────────────────────────────────────────────────────────────

def process_po(filepath: str, lang: str, translate_fn, verbose: bool = False):
    """
    Process a .po file: translate empty msgstr entries using translate_fn.

    Args:
        filepath:     Path to the .po file (modified in-place).
        lang:         Target language code (e.g. 'es', 'ja').
        translate_fn: Callable(text: str, lang: str) -> str  — calls the LLM.
        verbose:      Print raw error details on failure.
    """
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    raw_blocks = re.split(r'\n\n', content)
    output_blocks = []
    translated_count = 0
    skipped_venv = 0
    already_done = 0
    skipped_rate_limit = 0
    skipped_errors = 0
    consecutive_rate_limits = 0
    current_line = 1

    for raw_block in raw_blocks:
        lines = raw_block.split('\n')
        block_start = current_line
        current_line += len(lines) + 1

        locs = [l for l in lines if l.startswith('#:')]

        if not locs:
            output_blocks.append(raw_block)
            continue

        if is_venv_only(lines):
            skipped_venv += 1
            continue

        lines = remove_venv_location_lines(lines)

        if has_translation(lines):
            already_done += 1
            output_blocks.append('\n'.join(lines))
            continue

        msgid_text = extract_msgid_text(lines)
        if not msgid_text.strip():
            output_blocks.append('\n'.join(lines))
            continue

        msgstr_offset = next((i for i, l in enumerate(lines) if l.startswith('msgstr')), 0)
        file_line = block_start + msgstr_offset

        silenced = consecutive_rate_limits >= 3
        if silenced:
            skipped_rate_limit += 1
            print(f"\r  ⏳ Rate limit — skipped silently: {skipped_rate_limit}", end="", flush=True)
            output_blocks.append('\n'.join(lines))
            continue

        print(f"  [{translated_count + 1}:{file_line}] {msgid_text[:70]!r}", end=" ... ", flush=True)
        try:
            translation = _sanitize(translate_fn(msgid_text, lang))
            lines = set_msgstr(lines, translation)
            translated_count += 1
            consecutive_rate_limits = 0
            print(f"✓  {translation[:60]!r}")
        except Exception as e:
            error_str = str(e)
            if "429" in error_str:
                consecutive_rate_limits += 1
                skipped_rate_limit += 1
                retry_match = re.search(r'Please try again in ([^\.]+)', error_str)
                retry_in = retry_match.group(1) if retry_match else "a moment"
                print(f"⏳ Rate limit — retry in {retry_in}")
                if verbose:
                    print(f"     {error_str}")
                if consecutive_rate_limits >= 3:
                    print(f"  ↳ Rate limit persists — skipping API calls, counting silently...")
            else:
                consecutive_rate_limits = 0
                print(f"❌ ERROR: {e}" if not verbose else f"❌ ERROR: {error_str}")
                skipped_errors += 1

        output_blocks.append('\n'.join(lines))

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(output_blocks))

    if consecutive_rate_limits >= 3:
        print()
    print(f"\n✅  {translated_count} translated | {already_done} already done | {skipped_venv} venv stripped")
    if skipped_rate_limit:
        print(f"⏳  {skipped_rate_limit} skipped (rate limit) — re-run to complete")
    if skipped_errors:
        print(f"❌  {skipped_errors} errors — run with --verbose for details")
    print(f"    {filepath}")
