"""Retrieval evaluation harness.

Usage (from backend/):  python -m evaluation.run_eval [--verbose]

Metrics, over the bundled hand-written questions (evaluation/retrieval_cases.json):
  hit@1 / hit@3  an acceptable place is ranked first / within the top three
  MRR            mean reciprocal rank of the first acceptable place
  no-answer      out-of-scope questions correctly return no sources
This is a small regression set written by the maintainers, NOT an independent benchmark.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

CASES = Path(__file__).with_name("retrieval_cases.json")


def evaluate(top_k=4):
    from app.database import initialize
    from app.guide import retrieve

    initialize()
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    answerable = [c for c in cases if c["expect"]]
    out_of_scope = [c for c in cases if not c["expect"]]
    h1 = h3 = 0
    rr = 0.0
    misses, per_lang = [], {}
    for c in answerable:
        ids = [p["id"] for p in retrieve(c["q"], top_k=top_k)]
        rank = next((i for i, x in enumerate(ids, 1) if x in c["expect"]), None)
        lang = per_lang.setdefault(c["lang"], [0, 0])
        lang[1] += 1
        if rank == 1:
            h1 += 1
        if rank and rank <= 3:
            h3 += 1
            lang[0] += 1
        rr += 1 / rank if rank else 0
        if rank != 1:
            misses.append((c["q"], c["expect"], ids))
    no_ans_ok = sum(1 for c in out_of_scope if not retrieve(c["q"], top_k=top_k))
    n = len(answerable)
    return {
        "answerable": n, "hit@1": h1 / n, "hit@3": h3 / n, "mrr": rr / n,
        "no_answer": (no_ans_ok / len(out_of_scope)) if out_of_scope else 1.0,
        "out_of_scope": len(out_of_scope),
        "per_language_hit@3": {k: v[0] / v[1] for k, v in per_lang.items()},
        "misses": misses,
    }


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["DATABASE_PATH"] = str(Path(tmp) / "eval.db")
        r = evaluate()
    print(f"answerable={r['answerable']}  hit@1={r['hit@1']:.2f}  hit@3={r['hit@3']:.2f}  MRR={r['mrr']:.2f}  "
          f"no-answer={r['no_answer']:.2f} ({r['out_of_scope']} cases)")
    print("hit@3 by language:", {k: round(v, 2) for k, v in r["per_language_hit@3"].items()})
    if "--verbose" in sys.argv or "-v" in sys.argv:
        for q, expect, got in r["misses"]:
            print(f"  not-top1: {q!r}\n     expected {expect}\n     got      {got}")
