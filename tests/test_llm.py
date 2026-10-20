import pytest
from pydantic import BaseModel

from app.config import Settings
from app.llm import LLMClient, LLMError, extract_json


class DummySchema(BaseModel):
    message: str
    code: int


class MockLLMClient(LLMClient):
    """Subclass of LLMClient that returns pre-configured strings without network."""

    def __init__(self, responses: list[str]):
        super().__init__(Settings(llm_api_key="mock", embeddings="hash"))
        self.responses = list(responses)
        self.calls = 0

    def complete(self, system: str, user: str) -> str:
        self.calls += 1
        if not self.responses:
            raise RuntimeError("no more mocked responses")
        return self.responses.pop(0)


def test_extract_json_with_think_and_code_fence():
    raw = "<think>some thought</think>Here is the result:\n```json\n{\"message\": \"hello\", \"code\": 200}\n```"
    data = extract_json(raw)
    assert data == {"message": "hello", "code": 200}


def test_structured_valid_json_passes():
    client = MockLLMClient(['{"message": "success", "code": 1}'])
    res = client.structured("sys", "usr", DummySchema, retries=2)
    assert isinstance(res, DummySchema)
    assert res.message == "success"
    assert res.code == 1
    assert client.calls == 1


def test_structured_retry_then_succeeds():
    client = MockLLMClient([
        "not json at all",
        '{"message": "recovered", "code": 2}'
    ])
    res = client.structured("sys", "usr", DummySchema, retries=2)
    assert res.message == "recovered"
    assert client.calls == 2


def test_structured_invalid_json_retries_and_raises():
    client = MockLLMClient([
        "bad 1",
        "bad 2",
        "bad 3"
    ])
    with pytest.raises(LLMError) as exc:
        client.structured("sys", "usr", DummySchema, retries=2)
    assert "invalid structured output after 3 attempts" in str(exc.value)
    assert client.calls == 3
