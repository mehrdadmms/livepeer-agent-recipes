# Cost ledger — `cost_log.jsonl`

One file per project at `{project_dir}/cost_log.jsonl`. Every sub-agent appends to the same file. It is the only source for the numbers in the explainer post.

## Line format (one JSON object per line)

```json
{"ts":"2026-09-18T10:12:03Z","phase":"P2-stills","step":"kf2_freeze","capability":"nano-banana",
 "model_id":"fal-ai/nano-banana","job_id":"mjob_…","idempotency_key":"…","session_id":"{session_id}",
 "units":"1 image","cost_usd":0.084,"duration_s":24.1,"status":"done",
 "output_url":"https://…provider…","durable_url":"https://agent.livepeer.org/a/…",
 "local_path":"{project_dir}/stills/kf2_v1.png","note":"attempt 1"}
```

| Field | Required | Notes |
|---|---|---|
| `ts` | yes | UTC ISO time |
| `phase` | yes | `P0-sheets`, `P2-stills`, `P3-draft`, `P4-final`, `P4-audio`, `P5-explainer`, `QA` |
| `step` | yes | short name: `charsheet_v1`, `kf3_sip`, `draft_v2` |
| `capability` | yes | exact Livepeer capability name (`seedance-25-ref2v`), or `upload` / `create_upload_url` |
| `job_id` | if any | from the run result |
| `idempotency_key` | yes for paid | new key per attempt |
| `session_id` | yes | the project `{session_id}`, the same one passed to `run_capability` |
| `cost_usd` | yes | copied from the run result or `get_create_media({job_id})`, never estimated; 0 for free tools |
| `status` | yes | `done` · `failed` (error, billed) · `timeout` (billed) · `rejected` (succeeded but thrown away at QA) |
| `durable_url` | outputs | from `persist:true` / `upload`; downstream steps use this, never `output_url` |
| `output_url` | optional | provider URL, recorded for debugging only |
| `local_path` | outputs | where the file was saved |
| `note` | optional | attempt number, QA reason for a rejection, what changed in block 5 |

## Rules

1. One line per `run_capability` call, **including failures, timeouts and QA rejections**: they are billed and they get their own line on the receipt.
2. Never write summary or `TOTAL` rows into the ledger. `scripts/ledger.py` skips them with a warning, but they confuse everything else.
3. Use one `session_id` from the very first paid call, including the sheet maker's. (On the first run the sheet agent used its own session, so the session report missed $0.69 and the ledger had to be reconciled by hand.)
4. At the end of each phase the orchestrator runs `get_cost_report({scope:"session", session_id, group_by:"capability"})`, saves the JSON as `cost/report_{phase}.json` and runs `scripts/ledger.py check cost_log.jsonl --report cost/report_{phase}.json`. At the end it runs one more with `group_by:"status"` to split done from failed spend.
5. Any ledger vs report delta gets written to `post2/receipt_derivation.md` with its cause, and is shown on screen in the explainer if it survives.

## Helper

```bash
S=~/.claude/skills/video-remake/scripts
python3 $S/ledger.py add cost_log.jsonl --phase P3-draft --step draft_v1 --capability seedance-25-ref2v \
   --job-id mjob_x --session-id "$SESSION" --idem "$KEY" --cost 3.47 --status done \
   --units "15 s @480p" --durable-url https://agent.livepeer.org/a/… --local-path video/draft_v1.mp4
python3 $S/ledger.py summary cost_log.jsonl --cap 35 --pause 25   # prints PAUSE CHECKPOINT / STOP
python3 $S/ledger.py receipt cost_log.jsonl --out post2/receipt_lines.json
python3 $S/ledger.py check cost_log.jsonl --report cost/report_final.json
```

`receipt` groups successful paid calls by capability and puts every failed, timed-out or rejected run on its own "failed runs (billed)" line. The total includes them.
