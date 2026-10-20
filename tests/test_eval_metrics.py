from evals.run_eval import compute_metrics


def row(exp, act, intent="other", src="", cited=()):
    return dict(expected_action=exp, action=act, expected_intent="other", intent=intent,
                expected_source=src, sources=list(cited), latency_ms=100.0)


def test_metrics():
    rows = [row("AUTO_ANSWER", "AUTO_ANSWER", src="a.md", cited=["a.md#1"]),
            row("AUTO_ANSWER", "ESCALATE"),
            row("ESCALATE", "ESCALATE"),
            row("ESCALATE", "AUTO_ANSWER")]
    m = compute_metrics(rows)
    assert m["action_accuracy"] == (2, 4)
    assert m["unsafe_auto_rate"] == (1, 2)
    assert m["over_escalation_rate"] == (1, 2)
    assert m["auto_precision"] == (1, 2)
    assert m["citation_hit"] == (1, 1)
