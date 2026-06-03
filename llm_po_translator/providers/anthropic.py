from ..translator import LANG_NAMES, DEFAULT_SYSTEM_PROMPT


class AnthropicProvider:
    model = "claude-haiku-4-5-20251001"

    def __init__(self, api_key: str, system_prompt: str = DEFAULT_SYSTEM_PROMPT):
        try:
            import anthropic
        except ImportError:
            raise ImportError("Install anthropic: pip install 'llm-po-translator[anthropic]'")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.system_prompt = system_prompt

    def translate(self, text: str, lang: str) -> str:
        lang_name = LANG_NAMES.get(lang, lang)
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            system=self.system_prompt,
            messages=[{"role": "user", "content": f"Translate to {lang_name}:\n{text}"}],
        )
        return msg.content[0].text
