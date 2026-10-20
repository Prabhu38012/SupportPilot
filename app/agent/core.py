import time

from app.agent import guardrails
from app.agent.prompts import SYSTEM_PROMPT, build_user_prompt
from app.config import Settings
from app.schemas import AgentDecision, ChatRequest, ChatResponse
from app.store import Store

ESCALATION_REPLY = (
    "Thanks for reaching out. I want a teammate to look at this to make sure you get the right answer, "
    "so I've passed it to our support team (ticket #{ticket}). They'll reply as soon as possible."
)


class SupportAgent:
    """Orchestrates: pre-check -> retrieve -> retrieval gate -> LLM (structured) -> post-check -> answer or ticket."""

    def __init__(self, settings: Settings, retriever, llm, store: Store):
        self.s, self.retriever, self.llm, self.store = settings, retriever, llm, store

    def handle(self, req: ChatRequest) -> ChatResponse:
        t0 = time.perf_counter()
        reason, decision, chunks = guardrails.pre_check(req.message), None, []

        if reason is None:
            chunks = self.retriever.search(req.message, self.s.top_k)
            reason = guardrails.check_retrieval(chunks, self.s.min_retrieval_score)

        if reason is None:
            try:
                decision = self.llm.structured(SYSTEM_PROMPT, build_user_prompt(req.message, chunks), AgentDecision)
                reason = guardrails.post_check(decision, chunks, self.s.confidence_threshold)
            except Exception as e:  # fail safe: any LLM/network/parsing error -> human
                reason = f"llm_error: {type(e).__name__}: {str(e)[:120]}"

        escalate = reason is not None
        intent = decision.intent if decision else "other"
        conf = decision.confidence if decision else 0.0
        cited = decision.cited_sources if decision else []
        ticket_id = None
        if escalate:
            ticket_id = self.store.add_ticket(req.user_id, req.message, reason, intent)
            reply = ESCALATION_REPLY.format(ticket=ticket_id)
        else:
            reply = decision.answer

        trace_id = self.store.add_trace(
            user_id=req.user_id, message=req.message, intent=intent,
            action="ESCALATE" if escalate else "AUTO_ANSWER", confidence=conf, reason=reason,
            retrieved=[{"id": c.id, "score": c.score} for c in chunks], cited=cited,
            latency_ms=round((time.perf_counter() - t0) * 1000, 1), model=self.s.llm_model,
        )
        return ChatResponse(
            action="ESCALATE" if escalate else "AUTO_ANSWER", reply=reply, intent=intent,
            confidence=conf, sources=cited, reason=reason, trace_id=trace_id, ticket_id=ticket_id,
        )
