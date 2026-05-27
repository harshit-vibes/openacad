"""Print the comparison table + amortization curve from accumulated ComparisonResults."""

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openacad import eval_report as eval_service

from openacad.runtime import db
def main() -> None:
    results = db.list_comparisons()
    if not results:
        print("no comparison runs yet. run `make eval` after setting an API key.")
        sys.exit(0)

    by_q_then_pipe: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for r in results:
        by_q_then_pipe[r.question][r.pipeline].append(r)

    print("## per-question metrics")
    print()
    print(f"{'question':<60} {'pipeline':<5} {'tokens_in':>10} {'tokens_out':>11} {'latency_ms':>11} {'units':>6}")
    print("-" * 110)
    for q, pipes in by_q_then_pipe.items():
        for pipeline in ("B0", "B1", "A"):
            for r in pipes.get(pipeline, []):
                qshort = q[:58] + ".." if len(q) > 58 else q
                print(f"{qshort:<60} {pipeline:<5} {r.tokens_in:>10} {r.tokens_out:>11} {r.latency_ms:>11} {r.n_units_retrieved:>6}")

    # cumulative
    cumulative: dict[str, list[int]] = defaultdict(list)
    questions_order: list[str] = []
    for q in by_q_then_pipe:
        questions_order.append(q)
        for pipeline in ("B0", "B1", "A"):
            for r in by_q_then_pipe[q].get(pipeline, []):
                prior = cumulative[pipeline][-1] if cumulative[pipeline] else 0
                cumulative[pipeline].append(prior + r.tokens_in + r.tokens_out)

    print()
    print("## cumulative token cost (input + output)")
    print()
    print(f"{'q#':<4} {'B0':>10} {'B1':>10} {'A':>10}")
    for i, q in enumerate(questions_order, start=1):
        b0 = cumulative["B0"][i - 1] if i <= len(cumulative["B0"]) else "—"
        b1 = cumulative["B1"][i - 1] if i <= len(cumulative["B1"]) else "—"
        a = cumulative["A"][i - 1] if i <= len(cumulative["A"]) else "—"
        print(f"{i:<4} {b0:>10} {b1:>10} {a:>10}")

    # eval metrics
    print()
    print("## eval metrics")
    print(eval_service.metrics())


if __name__ == "__main__":
    main()
