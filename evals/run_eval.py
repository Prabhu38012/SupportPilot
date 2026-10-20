"""Run the golden set through the agent and write evals/report.md.
Usage:  python -m evals.run_eval [--golden evals/golden.jsonl] [--out evals/report.md]
The golden set MUST be labelled by a human (you), never by an LLM."""
import argparse
import json
import statistics
from pathlib import Path

from app.main import build_agent
from app.schemas import ChatRequest


def load(path: str) -> list[dict]:
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def pct(a: int, b: int) -> str:
    return f"{a}/{b} = {a / b:.1%}" if b else "n/a (0 cases)"


def compute_metrics(rows: list[dict]) -> dict:
    exp_auto = [r for r in rows if r["expected_action"] == "AUTO_ANSWER"]
    exp_esc = [r for r in rows if r["expected_action"] == "ESCALATE"]
    pred_auto = [r for r in rows if r["action"] == "AUTO_ANSWER"]
    lat = sorted(r["latency_ms"] for r in rows) or [0]
    answered_ok = [r for r in exp_auto if r["action"] == "AUTO_ANSWER"]
    return {
        "n": len(rows),
        "action_accuracy": (sum(r["action"] == r["expected_action"] for r in rows), len(rows)),
        "unsafe_auto_rate": (sum(r["action"] == "AUTO_ANSWER" for r in exp_esc), len(exp_esc)),
        "escalation_recall": (sum(r["action"] == "ESCALATE" for r in exp_esc), len(exp_esc)),
        "over_escalation_rate": (sum(r["action"] == "ESCALATE" for r in exp_auto), len(exp_auto)),
        "auto_precision": (sum(r["expected_action"] == "AUTO_ANSWER" for r in pred_auto), len(pred_auto)),
        "intent_accuracy": (sum(r["intent"] == r["expected_intent"] for r in rows), len(rows)),
        "citation_hit": (sum(any(r["expected_source"] in s for s in r["sources"]) for r in answered_ok), len(answered_ok)),
        "p50_ms": statistics.median(lat),
        "p95_ms": lat[min(len(lat) - 1, int(0.95 * len(lat)))],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--golden", default="evals/golden.jsonl")
    ap.add_argument("--out", default="evals/report.md")
    a = ap.parse_args()
    agent = build_agent()
    rows = []
    for g in load(a.golden):
        res = agent.handle(ChatRequest(message=g["question"], user_id="eval"))
        trace = agent.store.list_traces(1)[0]
        rows.append({**g, "action": res.action, "intent": res.intent, "sources": res.sources,
                     "reason": res.reason or "", "reply": res.reply, "latency_ms": trace["latency_ms"]})
    m = compute_metrics(rows)
    L = ["# SupportPilot eval report", "", f"Model: `{agent.s.llm_model}`  |  cases: {m['n']}", "",
         "| Metric | Result |", "|---|---|"]
    names = [("action_accuracy", "Action accuracy (auto vs escalate)"),
             ("unsafe_auto_rate", "Unsafe auto-answer rate (should have escalated, answered anyway) - LOWER is better"),
             ("escalation_recall", "Escalation recall"), ("over_escalation_rate", "Over-escalation rate (could have answered, escalated) - lower is better"),
             ("auto_precision", "Auto-answer precision"), ("intent_accuracy", "Intent accuracy"),
             ("citation_hit", "Citation hit rate (answered cases cite the expected doc)")]
    for k, label in names:
        L.append(f"| {label} | {pct(*m[k])} |")
    L += [f"| Latency p50 / p95 | {m['p50_ms']:.0f} ms / {m['p95_ms']:.0f} ms |", "", "## Failures", ""]
    bad = [r for r in rows if r["action"] != r["expected_action"]]
    L += [f"- #{r['id']} expected {r['expected_action']}, got {r['action']} ({r['reason'] or 'answered'}): {r['question']}" for r in bad] or ["- none"]
    L += ["", "## What is misleading about these numbers (edit this honestly)", "",
          "- The golden set was written by the same person who wrote the knowledge base, so it is easier than real traffic.",
          "- The set is small, so one case moves a percentage by several points. Report counts, not just percentages.",
          "- Thresholds (retrieval score, confidence) were tuned while looking at this set; re-test on fresh questions.",
          "- Intent labels are subjective for borderline questions."]
    Path(a.out).write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
