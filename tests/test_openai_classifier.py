from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from booking_agent.agent.intents import RuleBasedClassifier
from booking_agent.domain.models import Intent
from booking_agent.llm.openai_classifier import OpenAIIntentClassifier


class FakeCompletions:
    def __init__(self, content: str | None = None, error: Exception | None = None) -> None:
        self.content = content
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))])


def test_uses_the_model_answer() -> None:
    fake = FakeCompletions('{"intent": "hours"}')
    assert OpenAIIntentClassifier(fake.create, "m", RuleBasedClassifier()).classify("hola") is Intent.HOURS
    assert fake.calls[0]["response_format"]["json_schema"]["strict"] is True
    assert fake.calls[0]["temperature"] == 0


def test_falls_back_to_rules_when_the_call_fails() -> None:
    clf = OpenAIIntentClassifier(FakeCompletions(error=TimeoutError()).create, "m", RuleBasedClassifier())
    assert clf.classify("quiero cancelar") is Intent.CANCEL


def test_falls_back_on_an_unknown_label_or_bad_json() -> None:
    rules = RuleBasedClassifier()
    assert (
        OpenAIIntentClassifier(FakeCompletions('{"intent": "pizza"}').create, "m", rules).classify("hola")
        is Intent.GREETING
    )
    assert (
        OpenAIIntentClassifier(FakeCompletions("not json").create, "m", rules).classify("hola")
        is Intent.GREETING
    )
