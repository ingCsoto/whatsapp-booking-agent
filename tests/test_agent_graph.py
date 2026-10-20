from __future__ import annotations

from booking_agent.agent.graph import BookingAgent
from booking_agent.domain.calendar import InMemoryCalendar

ANA = "15550001111"
LUIS = "15550002222"


def test_full_booking_conversation(agent: BookingAgent, calendar: InMemoryCalendar) -> None:
    assert "asistente de Studio Demo" in (agent.reply(ANA, "hola") or "")

    offer = agent.reply(ANA, "quiero reservar") or ""
    assert "1." in offer and "3." in offer and "4." not in offer

    confirmation = agent.reply(ANA, "2") or ""
    assert confirmation.startswith("¡Listo!")
    booking = calendar.booking_of(ANA)
    assert booking is not None and booking.slot.starts_at.hour == 11
    assert "lun 2 mar · 11:00" in confirmation  # 2026-03-02 is a Monday; label is locale-independent

    assert "Tu cita es el" in (agent.reply(ANA, "¿cuándo es mi cita?") or "")
    assert "Ya tienes una cita" in (agent.reply(ANA, "quiero reservar otra") or "")

    assert "Cancelé tu cita" in (agent.reply(ANA, "cancelar") or "")
    assert calendar.booking_of(ANA) is None


def test_a_number_without_an_offer_is_not_a_booking(agent: BookingAgent, calendar: InMemoryCalendar) -> None:
    assert "No te entendí" in (agent.reply(ANA, "2") or "")
    assert calendar.booking_of(ANA) is None


def test_out_of_range_choice_does_not_book(agent: BookingAgent, calendar: InMemoryCalendar) -> None:
    agent.reply(ANA, "reservar")
    assert "No te entendí" in (agent.reply(ANA, "9") or "")
    assert calendar.booking_of(ANA) is None


def test_slot_taken_between_offer_and_choice(agent: BookingAgent, calendar: InMemoryCalendar) -> None:
    agent.reply(ANA, "reservar")
    agent.reply(LUIS, "reservar")
    agent.reply(LUIS, "1")  # Luis takes the first slot

    reply = agent.reply(ANA, "1") or ""
    assert reply.startswith("Ese horario se acaba de ocupar")
    assert calendar.booking_of(ANA) is None
    assert "1." in reply  # Ana gets a fresh list


def test_conversations_are_isolated_per_customer(agent: BookingAgent, calendar: InMemoryCalendar) -> None:
    agent.reply(ANA, "reservar")
    # Luis never received an offer, so "1" means nothing for him
    assert "No te entendí" in (agent.reply(LUIS, "1") or "")


def test_handoff_silences_the_bot_until_menu(agent: BookingAgent) -> None:
    assert "persona del equipo" in (agent.reply(ANA, "quiero un asesor") or "")
    assert agent.reply(ANA, "hola?") is None
    assert agent.reply(ANA, "reservar") is None
    assert "asistente de Studio Demo" in (agent.reply(ANA, "Menú") or "")
    assert "1." in (agent.reply(ANA, "reservar") or "")


def test_no_slots_left() -> None:
    empty = BookingAgent(
        __import__("booking_agent.agent.intents", fromlist=["x"]).RuleBasedClassifier(),
        InMemoryCalendar([]),
        "Studio Demo",
        "9 a 18",
    )
    assert "no hay horarios disponibles" in (empty.reply(ANA, "reservar") or "")
