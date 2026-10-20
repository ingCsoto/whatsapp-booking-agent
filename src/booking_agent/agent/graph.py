"""The conversation as an explicit LangGraph state machine.

classify ──▶ one handler per intent ──▶ END

State is checkpointed per customer (thread_id = phone number), so a booking can span several messages:
the bot offers numbered slots, and the customer answers with a number in the next message.
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from booking_agent.agent.intents import normalize
from booking_agent.domain.models import Intent
from booking_agent.domain.ports import BookingCalendar, IntentClassifier

SLOTS_OFFERED = 3
SILENT = "silent"  # route for conversations handed off to a human: the bot stays quiet


class ConversationState(TypedDict, total=False):
    customer: str
    text: str
    intent: str
    offered: list[str]
    awaiting_slot: bool
    handed_off: bool
    reply: str


class BookingAgent:
    def __init__(
        self,
        classifier: IntentClassifier,
        calendar: BookingCalendar,
        business_name: str,
        business_hours: str,
        checkpointer: BaseCheckpointSaver[Any] | None = None,
    ) -> None:
        self._classifier = classifier
        self._calendar = calendar
        self._name = business_name
        self._hours = business_hours
        self._graph = self._build().compile(checkpointer=checkpointer or MemorySaver())

    def reply(self, customer: str, text: str) -> str | None:
        """Run one turn. Returns the text to send, or None when the bot must stay silent."""
        result = self._graph.invoke(
            {"customer": customer, "text": text},
            config={"configurable": {"thread_id": customer}},
        )
        return result.get("reply") or None

    # --- graph -------------------------------------------------------------------------------------

    def _build(self) -> StateGraph[ConversationState]:
        g: StateGraph[ConversationState] = StateGraph(ConversationState)
        handlers = {
            Intent.GREETING.value: self._greet,
            Intent.BOOK.value: self._offer_slots,
            Intent.CHOOSE_SLOT.value: self._choose_slot,
            Intent.MY_BOOKING.value: self._my_booking,
            Intent.CANCEL.value: self._cancel,
            Intent.HOURS.value: self._hours_info,
            Intent.HUMAN.value: self._handoff,
            Intent.UNKNOWN.value: self._fallback,
            SILENT: self._silent,
        }
        g.add_node("classify", self._classify)
        for name, fn in handlers.items():
            g.add_node(name, fn)
            g.add_edge(name, END)
        g.set_entry_point("classify")
        g.add_conditional_edges("classify", lambda s: s["intent"], {name: name for name in handlers})
        return g

    # --- nodes ---------------------------------------------------------------------------------------

    def _classify(self, state: ConversationState) -> ConversationState:
        text = state["text"]
        if state.get("handed_off"):
            if normalize(text) == "menu":
                return {"handed_off": False, "intent": Intent.GREETING.value}
            return {"intent": SILENT}
        choice = text.strip()
        if (
            state.get("awaiting_slot")
            and choice.isdigit()
            and 1 <= int(choice) <= len(state.get("offered", []))
        ):
            return {"intent": Intent.CHOOSE_SLOT.value}
        intent = self._classifier.classify(text)
        if intent is Intent.CHOOSE_SLOT and not state.get("awaiting_slot"):
            intent = Intent.BOOK  # a slot can only be chosen after slots were offered
        return {"intent": intent.value}

    def _greet(self, state: ConversationState) -> ConversationState:
        return {
            "awaiting_slot": False,
            "reply": (
                f"¡Hola! Soy el asistente de {self._name}. Puedo ayudarte a:\n"
                "• Reservar una cita\n• Consultar o cancelar tu cita\n• Ver horarios\n"
                "Si prefieres hablar con una persona, escribe «asesor»."
            ),
        }

    def _offer_slots(self, state: ConversationState) -> ConversationState:
        existing = self._calendar.booking_of(state["customer"])
        if existing:
            return {
                "awaiting_slot": False,
                "reply": f"Ya tienes una cita el {existing.slot.label()}. "
                "Si quieres cambiarla, primero escribe «cancelar».",
            }
        slots = self._calendar.available(SLOTS_OFFERED)
        if not slots:
            return {
                "awaiting_slot": False,
                "reply": "Por ahora no hay horarios disponibles. "
                "Escribe «asesor» y te ayudamos a encontrar uno.",
            }
        lines = "\n".join(f"{i}. {s.label()}" for i, s in enumerate(slots, start=1))
        return {
            "offered": [s.id for s in slots],
            "awaiting_slot": True,
            "reply": (
                f"Estos son los próximos horarios disponibles:\n{lines}\n"
                "Responde con el número que prefieras."
            ),
        }

    def _choose_slot(self, state: ConversationState) -> ConversationState:
        slot_id = state["offered"][int(state["text"].strip()) - 1]
        booking = self._calendar.reserve(slot_id, state["customer"])
        if booking is None:
            retry = self._offer_slots(state)
            return {**retry, "reply": "Ese horario se acaba de ocupar. " + retry["reply"]}
        return {
            "offered": [],
            "awaiting_slot": False,
            "reply": f"¡Listo! Tu cita quedó para el {booking.slot.label()}. Te esperamos.",
        }

    def _my_booking(self, state: ConversationState) -> ConversationState:
        booking = self._calendar.booking_of(state["customer"])
        if booking is None:
            return {"reply": "No tienes citas reservadas. Escribe «reservar» para agendar una."}
        return {"reply": f"Tu cita es el {booking.slot.label()}."}

    def _cancel(self, state: ConversationState) -> ConversationState:
        booking = self._calendar.cancel(state["customer"])
        if booking is None:
            return {"awaiting_slot": False, "reply": "No encontré una cita para cancelar."}
        return {"awaiting_slot": False, "reply": f"Cancelé tu cita del {booking.slot.label()}."}

    def _hours_info(self, state: ConversationState) -> ConversationState:
        return {"reply": f"Nuestro horario de atención es: {self._hours}."}

    def _handoff(self, state: ConversationState) -> ConversationState:
        return {
            "handed_off": True,
            "awaiting_slot": False,
            "reply": "Te comunico con una persona del equipo. Te responderán en este mismo chat. "
            "Si quieres volver al asistente, escribe «menu».",
        }

    def _fallback(self, state: ConversationState) -> ConversationState:
        return {
            "reply": "No te entendí bien. Puedes escribir «reservar», «mi cita», «cancelar», "
            "«horario» o «asesor»."
        }

    def _silent(self, state: ConversationState) -> ConversationState:
        return {"reply": ""}
