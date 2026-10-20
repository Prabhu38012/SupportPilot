import html
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from app.agent.core import SupportAgent
from app.config import Settings
from app.kb.retriever import Retriever
from app.llm import LLMClient
from app.schemas import ChatRequest, ChatResponse
from app.store import Store


def build_agent(settings: Optional[Settings] = None, llm=None) -> SupportAgent:
    s = settings or Settings.from_env()
    retriever = Retriever(s)
    if retriever.count() == 0:
        retriever.ingest()
    return SupportAgent(s, retriever, llm or LLMClient(s), Store(s.db_path))


def create_app(settings: Optional[Settings] = None, llm=None) -> FastAPI:
    app = FastAPI(title="SupportPilot", version="0.1.0")
    agent = build_agent(settings, llm)

    @app.get("/health")
    def health():
        return {"status": "ok", "kb_chunks": agent.retriever.count(), "model": agent.s.llm_model}

    @app.post("/chat", response_model=ChatResponse)
    def chat(req: ChatRequest):
        return agent.handle(req)

    @app.post("/ingest")
    def ingest():
        return {"chunks_indexed": agent.retriever.ingest()}

    @app.get("/traces")
    def traces(limit: int = 50):
        return agent.store.list_traces(limit)

    @app.get("/traces/{trace_id}")
    def get_trace(trace_id: int):
        t = agent.store.get_trace(trace_id)
        if not t:
            raise HTTPException(status_code=404, detail="Trace not found")
        return t

    @app.get("/chunks/{chunk_id:path}")
    def get_chunk(chunk_id: str):
        c = agent.retriever.get_chunk(chunk_id)
        if not c:
            raise HTTPException(status_code=404, detail="Chunk not found")
        return c

    @app.get("/tickets")
    def tickets(limit: int = 50):
        return agent.store.list_tickets(limit)

    @app.get("/stats")
    def stats():
        return agent.store.stats()

    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard():
        st, rows = agent.store.stats(), agent.store.list_traces(100)
        e = lambda v: html.escape(str(v))
        body = "".join(
            f"<tr class='{r['action']}'><td>{r['id']}</td><td>{e(r['message'][:80])}</td><td>{e(r['intent'])}</td>"
            f"<td>{e(r['action'])}</td><td>{r['confidence']:.2f}</td><td>{e(r['reason'] or '')}</td>"
            f"<td>{r['latency_ms']:.0f} ms</td></tr>"
            for r in rows
        )
        return f"""<!doctype html><meta charset=utf-8><title>SupportPilot</title>
<style>body{{font:14px system-ui;margin:24px}}table{{border-collapse:collapse;width:100%}}
td,th{{border-bottom:1px solid #ddd;padding:6px;text-align:left}}.ESCALATE{{background:#fff4f4}}
.cards span{{display:inline-block;margin-right:24px}}</style>
<h2>SupportPilot traces</h2>
<p class=cards><span>Total <b>{st['total']}</b></span><span>Auto-answered <b>{st['auto_answered']}</b></span>
<span>Escalated <b>{st['escalated']}</b></span><span>Auto rate <b>{st['auto_rate']:.0%}</b></span>
<span>Avg latency <b>{st['avg_latency_ms']} ms</b></span></p>
<table><tr><th>#</th><th>Message</th><th>Intent</th><th>Action</th><th>Conf</th><th>Reason</th><th>Latency</th></tr>{body}</table>"""

    return app
