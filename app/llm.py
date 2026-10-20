import json
import re
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from app.config import Settings

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    pass


def extract_json(raw: str) -> dict:
    """Pull the first JSON object out of a model reply (tolerates <think> blocks and code fences)."""
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.S)
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON object found in reply")
    return json.loads(raw[start : end + 1])


class LLMClient:
    """Thin wrapper over any OpenAI-compatible chat endpoint with validated structured output."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = None

    def _get(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(
                api_key=self.settings.llm_api_key or "missing",
                base_url=self.settings.llm_base_url,
                timeout=30,
            )
        return self._client

    def complete(self, system: str, user: str) -> str:
        r = self._get().chat.completions.create(
            model=self.settings.llm_model,
            temperature=0,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        return r.choices[0].message.content or ""

    def structured(self, system: str, user: str, schema: Type[T], retries: int = 2) -> T:
        prompt, last = user, None
        for _ in range(retries + 1):
            raw = self.complete(system, prompt)
            try:
                return schema.model_validate(extract_json(raw))
            except (ValueError, ValidationError) as e:
                last = e
                prompt = (
                    f"{user}\n\nYour previous reply was invalid: {e}\n"
                    "Return ONLY one valid JSON object that matches the schema."
                )
        raise LLMError(f"invalid structured output after {retries + 1} attempts: {last}")
