import re
from typing import Optional

from app.schemas import AgentDecision, Chunk

INJECTION = [
    r"ignore (all |any |the )?(previous|prior|above|earlier) (instructions|rules|prompts?)",
    r"(reveal|print|show|repeat) .{0,30}(system prompt|your instructions)",
    r"\byou are now\b",
    r"\bjailbreak\b",
    r"\bdeveloper mode\b",
]
# Money disputes, legal threats, security incidents and "get me a human" always go to people.
HIGH_RISK = [
    r"\b(chargeback|charged twice|double charged|dispute)\b",
    r"\b(lawyer|attorney|lawsuit|legal action|sue you)\b",
    r"\b(hacked|breach|unauthori[sz]ed access|compromised)\b",
    r"\b(speak|talk) (to|with) (a |an )?(human|person|manager|agent|representative|someone)\b",
    r"\b(real person|human agent)\b",
]


def pre_check(message: str) -> Optional[str]:
    """Return an escalation reason BEFORE spending an LLM call, or None."""
    low = message.lower()
    if any(re.search(p, low) for p in INJECTION):
        return "prompt_injection_suspected"
    if any(re.search(p, low) for p in HIGH_RISK):
        return "high_risk_topic"
    return None


def check_retrieval(chunks: list[Chunk], min_score: float) -> Optional[str]:
    if not chunks:
        return "empty_knowledge_base"
    if chunks[0].score < min_score:
        return f"low_retrieval_score({chunks[0].score:.2f}<{min_score})"
    return None


def post_check(decision: AgentDecision, chunks: list[Chunk], threshold: float) -> Optional[str]:
    """Validate the model's answer AFTER generation. Any failure -> escalate (fail safe)."""
    if decision.needs_human:
        return "model_requested_human"
    if not decision.answer.strip():
        return "empty_answer"
    valid = {c.id for c in chunks}
    if not decision.cited_sources:
        return "no_citations"
    if any(s not in valid for s in decision.cited_sources):
        return "citation_not_in_retrieved_context"
    if decision.confidence < threshold:
        return f"low_confidence({decision.confidence:.2f}<{threshold})"
    return None
