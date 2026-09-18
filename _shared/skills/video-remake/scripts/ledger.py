#!/usr/bin/env python3
"""Project cost ledger (cost_log.jsonl) helper. Schema: ../references/ledger-schema.md

  ledger.py add LEDGER --phase P3-draft --step draft_v1 --capability seedance-25-ref2v \
      --job-id mjob_x --session-id S --idem K --cost 3.47 --status done \
      [--units "15 s @480p"] [--output-url URL] [--durable-url URL] [--local-path P] [--note TEXT]
  ledger.py summary LEDGER            # per-capability spend, failed split out, total
  ledger.py receipt LEDGER [--out receipt_lines.json]   # lines for the explainer's cost beat
  ledger.py check LEDGER --report cost_report.json      # reconcile against get_cost_report JSON

Rules: one line per run_capability call INCLUDING failures and timeouts (they bill);
cost_usd is copied from the run result or get_create_media, never estimated.
"""
import argparse, collections, datetime, json, pathlib, sys


def rows(path):
    p = pathlib.Path(path)
    out = []
    for l in (p.read_text().splitlines() if p.exists() else []):
        if not l.strip():
            continue
        r = json.loads(l)
        # summary/total rows do not belong in the ledger; skip them so nothing is double-counted
        if str(r.get("step", "")).upper().startswith("TOTAL") or r.get("capability") in ("-", "", None):
            print(f"warn: skipping non-call row: {r.get('step')!r}", file=sys.stderr)
            continue
        out.append(r)
    return out


def cmd_add(a):
    row = {"ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "phase": a.phase, "step": a.step, "capability": a.capability, "job_id": a.job_id,
           "idempotency_key": a.idem, "session_id": a.session_id, "units": a.units,
           "cost_usd": round(float(a.cost), 4), "status": a.status, "output_url": a.output_url,
           "durable_url": a.durable_url, "local_path": a.local_path, "note": a.note}
    row = {k: v for k, v in row.items() if v is not None}
    with open(a.ledger, "a") as f:
        f.write(json.dumps(row) + "\n")
    print(json.dumps(row))


def paid(r):
    return float(r.get("cost_usd") or 0)


def is_failed(r):
    """failed / timeout / rejected (paid but thrown away at QA) all count as failed runs.
    Older rows without a status: infer from the step text."""
    s = str(r.get("status", "")).lower()
    if s:
        return s not in ("done", "ok", "success", "accepted")
    return "rejected" in str(r.get("step", "")).lower()


def cmd_summary(a):
    rs = rows(a.ledger)
    ok, bad = collections.defaultdict(lambda: [0, 0.0]), collections.defaultdict(lambda: [0, 0.0])
    for r in rs:
        bucket = bad if is_failed(r) else ok
        bucket[r.get("capability", "?")][0] += 1
        bucket[r.get("capability", "?")][1] += paid(r)
    total = sum(paid(r) for r in rs)
    for cap, (n, c) in sorted(ok.items(), key=lambda x: -x[1][1]):
        print(f"{cap:32s} {n:3d} ok      ${c:8.2f}")
    for cap, (n, c) in sorted(bad.items(), key=lambda x: -x[1][1]):
        print(f"{cap:32s} {n:3d} FAILED  ${c:8.2f}")
    print(f"{'TOTAL':32s} {len(rs):3d} calls   ${total:8.2f}")
    if a.cap is not None:
        left = a.cap - total
        print(f"hard stop ${a.cap:.2f} -> ${left:.2f} left" + ("   STOP" if left <= 0 else ""))
    if a.pause is not None and total >= a.pause:
        print(f"PAUSE CHECKPOINT: spent ${total:.2f} >= ${a.pause:.2f}; report to the user before the next paid call")


def cmd_receipt(a):
    rs = rows(a.ledger)
    ok = collections.OrderedDict()
    failed_n, failed_c = 0, 0.0
    for r in rs:
        if paid(r) == 0 and not is_failed(r):
            continue  # uploads, local ffmpeg, free tools
        if is_failed(r):
            failed_n += 1; failed_c += paid(r); continue
        k = r.get("capability", "?")
        e = ok.setdefault(k, {"capability": k, "n": 0, "cost_usd": 0.0, "steps": []})
        e["n"] += 1; e["cost_usd"] += paid(r); e["steps"].append(r.get("step"))
    lines = [dict(v, cost_usd=round(v["cost_usd"], 2)) for v in ok.values()]
    if failed_n:
        lines.append({"capability": "failed runs (billed)", "n": failed_n, "cost_usd": round(failed_c, 2), "failed": True})
    out = {"lines": lines, "n_calls": sum(l["n"] for l in lines),
           "total_usd": round(sum(paid(r) for r in rs), 2)}
    s = json.dumps(out, indent=2)
    if a.out:
        pathlib.Path(a.out).write_text(s + "\n")
    print(s)


def cmd_check(a):
    total = round(sum(paid(r) for r in rows(a.ledger)), 2)
    rep = json.loads(pathlib.Path(a.report).read_text())
    rt = None
    for k in ("total_usd", "total_cost_usd", "total"):
        if isinstance(rep, dict) and k in rep:
            rt = rep[k]; break
    if rt is None:
        sys.exit("could not find a total in the report JSON; compare by hand")
    rt = round(float(rt), 2)
    print(f"ledger ${total:.2f} vs report ${rt:.2f} -> delta ${total - rt:+.2f}")
    if abs(total - rt) >= 0.01:
        print("MISMATCH: write the delta and its cause into receipt_derivation.md and show it on screen")
        sys.exit(2)


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("add"); p.add_argument("ledger")
    for f in ("phase", "step", "capability", "status"):
        p.add_argument("--" + f, required=True)
    p.add_argument("--cost", required=True)
    for f in ("job-id", "session-id", "idem", "units", "output-url", "durable-url", "local-path", "note"):
        p.add_argument("--" + f)
    p.set_defaults(fn=cmd_add)
    p = sp.add_parser("summary"); p.add_argument("ledger")
    p.add_argument("--cap", type=float); p.add_argument("--pause", type=float); p.set_defaults(fn=cmd_summary)
    p = sp.add_parser("receipt"); p.add_argument("ledger"); p.add_argument("--out"); p.set_defaults(fn=cmd_receipt)
    p = sp.add_parser("check"); p.add_argument("ledger"); p.add_argument("--report", required=True); p.set_defaults(fn=cmd_check)
    a = ap.parse_args(); a.fn(a)


if __name__ == "__main__":
    main()
