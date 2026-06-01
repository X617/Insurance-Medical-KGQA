#!/usr/bin/env python3
"""Run golden-query checks against the local demo API."""

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List

import requests


ROOT = Path(__file__).resolve().parents[1]
GOLDEN_PATH = ROOT / "tests" / "golden_queries.json"
REPORT_DIR = ROOT / "reports"


def load_queries(limit: int | None = None) -> List[Dict[str, Any]]:
    data = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    return data[:limit] if limit else data


def rule_ok(query: str, result: Dict[str, Any]) -> bool:
    recs = result.get("recommendations", {}) or {}
    insurance = recs.get("insurance") or []
    nursing = recs.get("nursing_homes") or []
    if "70岁" in query:
        for item in insurance:
            max_age = item.get("max_age")
            min_age = item.get("min_age")
            if max_age is not None and 70 > int(max_age):
                return False
            if min_age is not None and 70 < int(min_age):
                return False
    if "5000" in query:
        for item in nursing:
            price = item.get("price_value")
            if price is not None and int(price) > 5000:
                return False
    return True


def run(api_root: str, limit: int | None = None, timeout: float = 45.0) -> Dict[str, Any]:
    rows = []
    history: List[Dict[str, str]] = []
    for item in load_queries(limit):
        query = item["query"]
        payload_history = history[-6:] if item.get("history_seed") else []
        started = time.perf_counter()
        try:
            resp = requests.post(
                f"{api_root.rstrip('/')}/chat",
                json={"query": query, "history": payload_history},
                timeout=timeout,
            )
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            if resp.status_code != 200:
                rows.append({
                    "id": item["id"],
                    "query": query,
                    "ok": False,
                    "latency_ms": latency_ms,
                    "error": resp.text[:240],
                })
                continue
            result = resp.json()
            graph_hit = bool((result.get("graph") or {}).get("nodes"))
            source_count = len(result.get("sources") or [])
            candidate_count = sum(
                len((result.get("recommendations") or {}).get(key) or [])
                for key in ("insurance", "nursing_homes")
            )
            confidence = (result.get("confidence") or {}).get("overall", 0)
            answer = result.get("answer") or ""
            ok = bool(answer.strip()) and rule_ok(query, result)
            rows.append({
                "id": item["id"],
                "query": query,
                "ok": ok,
                "latency_ms": latency_ms,
                "graph_hit": graph_hit,
                "source_count": source_count,
                "candidate_count": candidate_count,
                "confidence": confidence,
                "retrieval_mode": result.get("retrieval_mode", ""),
                "rule_ok": rule_ok(query, result),
                "answer_preview": answer[:120],
            })
            history.extend([
                {"role": "user", "content": query},
                {"role": "assistant", "content": answer},
            ])
        except Exception as exc:
            rows.append({
                "id": item["id"],
                "query": query,
                "ok": False,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "error": str(exc),
            })

    passed = sum(1 for row in rows if row.get("ok"))
    summary = {
        "total": len(rows),
        "passed": passed,
        "pass_rate": round(passed / max(1, len(rows)), 4),
        "avg_latency_ms": round(sum(row.get("latency_ms", 0) for row in rows) / max(1, len(rows)), 2),
        "graph_hit_rate": round(sum(1 for row in rows if row.get("graph_hit")) / max(1, len(rows)), 4),
        "avg_confidence": round(sum(float(row.get("confidence") or 0) for row in rows) / max(1, len(rows)), 2),
    }
    return {"summary": summary, "rows": rows}


def run_ablation(api_root: str, timeout: float = 180.0) -> Dict[str, Any]:
    resp = requests.post(f"{api_root.rstrip('/')}/eval/ablation", timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def write_reports(report: Dict[str, Any]) -> None:
    REPORT_DIR.mkdir(exist_ok=True)
    (REPORT_DIR / "eval_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Demo Evaluation Report",
        "",
        f"- Total: {report['summary']['total']}",
        f"- Passed: {report['summary']['passed']}",
        f"- Pass rate: {report['summary']['pass_rate']:.2%}",
        f"- Avg latency: {report['summary']['avg_latency_ms']} ms",
        f"- Avg confidence: {report['summary'].get('avg_confidence', 0)}",
        "",
        "| ID | OK | Latency(ms) | Graph | Sources | Candidates | Confidence | Query |",
        "| --- | --- | ---: | --- | ---: | ---: | ---: | --- |",
    ]
    for row in report["rows"]:
        lines.append(
            f"| {row.get('id')} | {row.get('ok')} | {row.get('latency_ms')} | "
            f"{row.get('graph_hit', '')} | {row.get('source_count', '')} | "
            f"{row.get('candidate_count', '')} | {row.get('confidence', '')} | {row.get('query')} |"
        )
    (REPORT_DIR / "eval_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-root", default="http://127.0.0.1:8000")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--ablation", action="store_true", help="Call /eval/ablation and save the ablation report.")
    args = parser.parse_args()
    if args.ablation:
        report = run_ablation(args.api_root)
        REPORT_DIR.mkdir(exist_ok=True)
        (REPORT_DIR / "ablation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report.get("summary", {}), ensure_ascii=False, indent=2))
        print(f"Ablation report written to {REPORT_DIR / 'ablation_report.json'}")
        return
    report = run(args.api_root, args.limit)
    write_reports(report)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Reports written to {REPORT_DIR}")


if __name__ == "__main__":
    main()
