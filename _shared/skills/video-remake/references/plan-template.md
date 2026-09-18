# PLAN.md skeleton

The planner fills this in; the orchestrator writes §ROLES before dispatching anyone. Section numbers are what the other briefs cite (`PLAN.md §5` etc.), so keep them.

```markdown
# Production plan — "{project_title}" (Post 1) + "How it was made" (Post 2)

Planner: {planner_model} sub-agent · {date} · PLAN ONLY (no paid calls; every number below is from
describe_capability / get_pricing / get_cost_report read-only calls).
Project root: {project_dir}   Session: {session_id}   Ledger: {project_dir}/cost_log.jsonl

## ROLES
The user provides:
- Character: {sheet or reference photo(s) — path/URL}
- Environment: {sheet or reference photo(s) — path/URL}
- Explainer style example: {post URL or file}
- Approvals at every ⛔ gate, via the sign-off page or a SIGN-OFF block pasted in the terminal
- Spend-cap changes (only the user can authorise raising the Livepeer 24 h cap)

The orchestrator (main session) only: dispatches sub-agents, merges their reports, builds the sign-off
page, records DECISIONS.md, runs get_cost_report at phase ends, and talks to the user. It makes no
generation calls itself.

Sub-agents:
| Agent | Model | Does | Writes | Paid calls? |
|---|---|---|---|---|
| Planner | fable | recover prompt, call-sheet prompt, capability picks, pipeline, gates, QA, budget | PLAN.md | no |
| Sheet maker | default | char + env sheets via gpt-image-edit, identity + brand QA | sheets/*, ledger | yes |
| Style analyst | default | fetch + analyse the example post, write the explainer spec | style/POST2_SPEC.md | no |
| Stills | default | scene keyframes from locked sheets | stills/* | yes |
| Video | default | 480p draft, 720p final, audio, export | video/* | yes |
| Explainer | default | receipt data, Playwright capture of sign-off page, HTML render(t) → frames → mp4 | post2/* | tiny |

## 0. Source read-out (INTERNAL ONLY — nothing here may appear in any output)
- Recovered prompt (verbatim OCR, note which frames): > …
- Source metadata: resolution, fps, duration, audio, on-screen overlays/branding to avoid.
- Beat map with timestamps: 0–4 s … · … · …
- Sound design beats: …

## 1. New Seedance call-sheet prompt (five blocks, per the seedance-video skill)
Reference order for image_urls: [...]. Blocks 1, 3, 5 frozen word-for-word across every attempt.
[ASSETS] / [SUMMARY] / [STYLE] / [PLOT] / [REQUIREMENTS]
Call: capability, inputs, duration (string), resolution, aspect_ratio, generate_audio,
timeout (SECONDS), async, session_id, idempotency_key.

## 2. Capability choices (verified today)
| Step | Capability | Verified inputs | Price | p95 → timeout (s) | Health / success rate |

## 3. One take vs multiple shots — decision + fallback ladder

## 4. Pipeline (⛔ = user gate, ∥ = parallel sub-agents)
Phase 0 setup · Gate A sheets (sign-off page) · Phase 1 prompt lock · Phase 2 stills ∥ · Gate B ·
Phase 3 draft · Gate C · Phase 4 final + audio + export · Gate D · Phase 5 explainer · Gate E.

## 5. QA per phase (copy from references/qa-checklist.md, then specialise)

## 6. Budget
| Item | Expected | Worst case |
Expected total $… · Worst $… · Hard stop $… · Pause-and-report at $… (≈70 % of hard stop, and
always before the first 720p render). Current 24 h spend-cap headroom: $… (spend_cap read).

## 7. Assets Post 1 must leave for Post 2 + cost-capture contract

## 8. Sub-agent briefs (fill from references/briefs.md)

## 9. Open questions for the user (≤5, each with a default) → these become the sign-off page's quick decisions
```
