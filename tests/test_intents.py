from __future__ import annotations

import pytest

from booking_agent.agent.intents import RuleBasedClassifier
from booking_agent.domain.models import Intent


@pytest.mark.parametrize(
    ("text", "intent"),
    [
        ("Hola", Intent.GREETING),
        ("Quiero reservar una cita", Intent.BOOK),
        ("¿Cuándo es mi cita?", Intent.MY_BOOKING),
        ("Necesito cancelar mi cita", Intent.CANCEL),  # cancel wins over book
        ("¿Qué horario tienen?", Intent.HOURS),
        ("¿Dónde quedan? quiero la dirección", Intent.HOURS),
        ("Quiero hablar con un asesor", Intent.HUMAN),
        ("asdf qwerty", Intent.UNKNOWN),
    ],
)
def test_rules(text: str, intent: Intent) -> None:
    assert RuleBasedClassifier().classify(text) is intent


def test_keywords_match_whole_words_only() -> None:
    # "hi" must not match inside another word
    assert RuleBasedClassifier().classify("chile") is Intent.UNKNOWN
