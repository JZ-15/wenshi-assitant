from collections.abc import Generator

import anthropic


class LLM:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def generate(
        self,
        system: str,
        user: str,
        max_tokens: int = 4096,
    ) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text

    def stream(
        self,
        system: str,
        user: str,
        max_tokens: int = 4096,
    ) -> Generator[str, None, None]:
        """Yield text tokens as they are generated."""
        with self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        ) as stream:
            for text in stream.text_stream:
                yield text
