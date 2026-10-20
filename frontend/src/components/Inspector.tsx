import { useEffect, useState } from "react";
import { api, Chunk, Trace } from "../api";

export default function Inspector({ traceId }: { traceId: number | null }) {
  const [trace, setTrace] = useState<Trace | null>(null);
  const [chunks, setChunks] = useState<Record<string, Chunk>>({});
  const [open, setOpen] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (traceId === null) return;
    let cancelled = false;
    setError(null);
    setOpen(null);
    api
      .trace(traceId)
      .then((t) => {
        if (!cancelled) setTrace(t);
      })
      .catch((e: Error) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [traceId]);

  async function toggle(id: string) {
    if (open === id) return setOpen(null);
    setOpen(id);
    if (!chunks[id]) {
      try {
        const c = await api.chunk(id);
        setChunks((prev) => ({ ...prev, [id]: c }));
      } catch (e) {
        setError((e as Error).message);
      }
    }
  }

  if (traceId === null) {
    return (
      <aside className="inspector">
        <h3>Trace inspector</h3>
        <p className="muted">Send a message, then click a reply to see exactly why the agent answered or escalated.</p>
      </aside>
    );
  }
  if (error) return <aside className="inspector"><div className="error">{error}</div></aside>;
  if (!trace) return <aside className="inspector"><p className="muted">Loading…</p></aside>;

  const esc = trace.action === "ESCALATE";
  return (
    <aside className="inspector">
      <h3>Trace #{trace.id}</h3>
      <dl>
        <dt>Decision</dt>
        <dd>
          <span className={`badge ${esc ? "warn" : "ok"}`}>{esc ? "ESCALATE" : "AUTO_ANSWER"}</span>
        </dd>
        {esc && (
          <>
            <dt>Why</dt>
            <dd className="reason">{trace.reason}</dd>
          </>
        )}
        <dt>Intent</dt>
        <dd>{trace.intent}</dd>
        <dt>Confidence</dt>
        <dd>
          <div className="bar">
            <div style={{ width: `${trace.confidence * 100}%` }} />
          </div>
          {(trace.confidence * 100).toFixed(0)}%
        </dd>
        <dt>Latency</dt>
        <dd>{trace.latency_ms.toFixed(0)} ms</dd>
        <dt>Model</dt>
        <dd className="mono">{trace.model}</dd>
      </dl>

      <h4>Retrieved context</h4>
      {trace.retrieved.length === 0 && <p className="muted">No retrieval (blocked by a pre-check guardrail).</p>}
      <ul className="retrieved">
        {trace.retrieved.map((r) => {
          const cited = trace.cited.includes(r.id);
          return (
            <li key={r.id}>
              <button className="link" onClick={() => void toggle(r.id)}>
                <span className="mono">{r.id}</span>
                {cited && <span className="badge ok small">cited</span>}
                <span className="score">{r.score.toFixed(2)}</span>
              </button>
              <div className="bar thin">
                <div style={{ width: `${Math.max(0, r.score) * 100}%` }} />
              </div>
              {open === r.id && <pre className="chunk">{chunks[r.id]?.text ?? "Loading…"}</pre>}
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
