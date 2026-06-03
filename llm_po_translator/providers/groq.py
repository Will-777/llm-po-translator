from ..translator import LANG_NAMES, DEFAULT_SYSTEM_PROMPT


class GroqProvider:
    model = "llama-3.3-70b-versatile"

    def __init__(self, api_key: str, system_prompt: str = DEFAULT_SYSTEM_PROMPT):
        try:
            from groq import Groq
        except ImportError:
            raise ImportError("Install groq: pip install 'llm-po-translator[groq]'")
        self.client = Groq(api_key=api_key)
        self.system_prompt = system_prompt

    def translate(self, text: str, lang: str) -> str:
        lang_name = LANG_NAMES.get(lang, lang)
        msg = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Translate to {lang_name}:\n{text}"},
            ],
            temperature=1,
            max_completion_tokens=512,
            top_p=1,
            stream=False,
            stop=None,
        )
        return msg.choices[0].message.content
