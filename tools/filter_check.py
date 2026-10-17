"""Check that each X search filter narrows the results, using the same client as the app.

usage: python3 tools/filter_check.py --query bitcoin --count 10 --out runs/filter-check
Each check is one paid GET /twitter call (billed per returned post). The summary is written to
<out>/summary.json and every call (key redacted) to <out>/raw/ and <out>/calls.jsonl.
"""
import argparse, json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import app, core  # noqa: E402

CHECKS = [
    ("latest", {}),
    ("top", {"sort": "Top"}),
    ("lang-es", {"lang": "es"}),
    ("min-likes-100", {"sort": "Top", "min_likes": 100}),
    ("verified", {"verified": "true"}),
    ("blue-verified", {"blue_verified": "true"}),
    ("is-image", {"is_image": "true"}),
    ("is-video", {"is_video": "true"}),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", default="bitcoin")
    ap.add_argument("--count", type=int, default=10)
    ap.add_argument("--out", default="runs/filter-check")
    ap.add_argument("--only", help="comma separated check names")
    ap.add_argument("--start-date", help="add a YYYY-MM-DD window check from this date")
    ap.add_argument("--end-date")
    a = ap.parse_args()
    checks = list(CHECKS)
    if a.start_date:
        w = {"start_date": a.start_date}
        if a.end_date:
            w["end_date"] = a.end_date
        checks.append(("date-window", w))
    if a.only:
        keep = set(a.only.split(","))
        checks = [c for c in checks if c[0] in keep]
    client = app.Client(app.api_key(), a.out)
    summary = {}
    for name, extra in checks:
        params = {"query": a.query, "sort": "Latest", "count": a.count, **extra}
        st, body, rec = client.search(params, tag=name)
        rows = [core.row(p) for p in core.posts_of(body)]
        years = sorted({r["created_utc"][:4] for r in rows if r["created_utc"]})
        summary[name] = {"params": params, "status": st, "requested": a.count, "returned": len(rows),
                         "latency_s": rec["latency_s"], "billing_headers": rec["billing_headers"],
                         "violations": core.check_filters(params, rows),
                         "langs": sorted({r["lang"] for r in rows}), "years": years}
    summary["_total_cost_usd"] = round(client.total, 6)
    summary["_calls"] = client.n
    client._write(pathlib.Path(a.out) / "summary.json", json.dumps(summary, indent=1))
    print(json.dumps({k: (v if k.startswith("_") else {x: v[x] for x in ("status", "returned", "violations")})
                      for k, v in summary.items()}, indent=1))


if __name__ == "__main__":
    main()
