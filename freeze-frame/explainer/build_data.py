#!/usr/bin/env python3
"""Build post2_data.json -- the ONLY content source for template.html.

* Aggregates every  ledger/cost_log*.jsonl  ledger (skips TOTAL/upload lines,
  de-duplicates by job_id) and folds each billed line into ONE on-screen row (ROWS below).
  Retries fold into their parent row; rejected/failed attempts of a real step go on the
  "Failed + rejected attempts" row; moderation refusals go on their own $0 row.
* Total on screen = sum of the ledgers' cost_usd (net). reserved_usd (released holds) is
  reported only in reconciliation, never on screen.
* Finds the final clip (outputs/post1_freeze_frame.mp4) and the prompt file (prompts/prompt_*.txt).
* DRY RUN is automatic: until a billed final Seedance render is in a ledger, the final row
  is the ROWS `est` value marked "placeholder": true; the clip is a looping env-sheet still.

Usage:  python3 build_data.py        (render.py calls it; writes post2_data.json)

Repo layout (all paths are relative to the recipe folder, freeze-frame/):
  ledger/cost_log*.jsonl        every paid call            -> cost rows + total
  prompts/prompt_*.txt          the Seedance call sheet    -> the 5 prompt blocks
  prompts/*_prompt*.txt         sheet / photo prompts      -> the recipe cards
  refs/*.jpg                    location sheet, character sheet, street photo of her
  refs/street_photo.jpg         OPTIONAL: your own input street photo (not shipped; blurred on screen)
  outputs/post1_freeze_frame.mp4  the finished 15 s shot  -> hook / outro clip + thumbnail
  sound/mix.sh                  the "Event times (s):" header line -> the sound timeline
"""
import glob
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
S = os.path.dirname(HERE)                       # recipe root (freeze-frame/)
OUT = os.path.join(HERE, "post2_data.json")
THUMBS = os.path.join(HERE, "assets", "thumbs")
ENV_BLUR_PX = 14            # real-brand blur on images/2.jpg (radius in source pixels); 0 = off

SESSIONS = ["post1-freeze-ae42c851-10af-46ca-abd3-c68ab52bef9b", "sheets-freeze-nyc"]


def rel(p):
    return os.path.relpath(p, HERE) if p else None


def local(p):
    if not p:
        return None
    p = p if os.path.isabs(p) else os.path.join(S, p)
    return p if os.path.exists(p) else None


def existing(*cands):
    return next((c for c in cands if c and os.path.exists(c)), None)


# --------------------------------------------------------------------------
# On-screen rows, in order.  `rule(line, hay)` returns True if the ledger line belongs here.
# First matching rule wins.  hay = lower-cased step + capability + model_id + inputs + note.
# --------------------------------------------------------------------------
def _cap(l):
    return str(l.get("capability", "")).lower()


def _step(l):
    return str(l.get("step", "")).strip().lower()


def _refused(l, hay):
    step = str(l.get("step", ""))
    return "seedance" in _cap(l) and float(l.get("cost_usd") or 0) == 0 and \
        re.search(r"REFUSED|content_policy|moderation_blocked|likeness", step) is not None and \
        re.search(r"not moderation|upstream", step, re.I) is None


def _rejected(l, hay):
    step = str(l.get("step", ""))
    if re.search(r"\bACCEPTED\b", step):
        return False
    return bool(re.search(r"\b(REJECTED|FAILED|TIMED?[ _-]?OUT)\b", step)) or \
        str(l.get("status", "")).lower().startswith(("failed", "error", "timeout", "rejected"))


ROWS = [
    dict(key="notcharged", label="Failed attempts (not charged)", model="{n} runs", capability="seedance-25-*",
         kind="notcharged", rule=lambda l, h: "seedance" in _cap(l) and float(l.get("cost_usd") or 0) == 0 and
         (_refused(l, h) or _rejected(l, h))),
    dict(key="location", label="Location sheet (draft + text fix)", model="GPT Image 2", capability="gpt-image-edit",
         rule=lambda l, h: _step(l).startswith("envsheet")),
    dict(key="char_photo", label="Character street photo", model="Nano Banana", capability="nano-banana",
         rule=lambda l, h: _step(l).startswith("char_v3_single")),
    dict(key="character", label="Character sheet, from text", model="GPT Image 2", capability="gpt-image-edit",
         rule=lambda l, h: _step(l).startswith("charsheet_v3")),
    dict(key="early", label="Early tests (unused character + scene stills)", model="Mixed image models",
         capability="gpt-image-edit · nano-banana · kontext-edit", kind="early",
         rule=lambda l, h: re.match(r"charsheet_(v1|v2|attempt)", _step(l)) is not None
         or re.search(r"nano-banana|kontext|qwen", _cap(l)) is not None),
    dict(key="probes", label="Seedance test clips", model="Seedance 2.5", capability="seedance-25-ref2v",
         rule=lambda l, h: "seedance" in _cap(l) and _step(l).startswith("probe")),
    dict(key="draft", label="15s draft (480p)", model="Seedance 2.5", capability="seedance-25-t2v",
         rule=lambda l, h: "seedance" in _cap(l) and re.search(r"480p|draft", h) is not None and not _rejected(l, h)),
    dict(key="final", label="Final 15s render · 720p", model="Seedance 2.5", capability="seedance-25-t2v",
         est=7.45, rule=lambda l, h: "seedance" in _cap(l) and not _rejected(l, h)),
    dict(key="narration", label="Narration voice", model="Inworld TTS", capability="inworld-tts",
         rule=lambda l, h: _step(l).startswith("narration") or "tts" in _cap(l)),
    dict(key="sound", label="Sound effects", model="{models}", capability="",
         rule=lambda l, h: _step(l).startswith("sound effects")
         or re.search(r"mirelo|sfx|ffmpeg|export|mux|audio-mix|music", _cap(l)) is not None),
    dict(key="qa", label="AI quality checks", model="Nemotron Omni", capability="nemotron-omni-*",
         rule=lambda l, h: "nemotron" in _cap(l)),
]
ROW_ORDER = ["location", "character", "char_photo", "early", "probes", "draft", "final", "sound", "qa",
             "narration", "failed", "notcharged"]
MODEL_NAMES = {"mirelo": "Mirelo SFX", "elevenlabs": "ElevenLabs SFX", "stable-audio": "Stable Audio", "ffmpeg": "ffmpeg",
               "music": "Music", "sfx": "SFX"}
SKIP_CAP = re.compile(r"upload|create_upload_url|^-$", re.I)


def classify(l):
    hay = " ".join(str(l.get(k, "")) for k in ("step", "phase", "capability", "model_id", "inputs", "note")).lower()
    for r in ROWS:
        if r["rule"](l, hay):
            return r["key"]
    # a rejected/failed seedance or unknown billed line of a real step
    if _rejected(l, hay):
        return "failed"
    return "other:" + (l.get("capability") or "unknown")


def read_ledgers():
    paths = sorted(set(glob.glob(os.path.join(S, "ledger", "cost_log*.jsonl"))))
    lines, reported, seen = [], [], set()
    for p in paths:
        with open(p) as f:
            for n, raw in enumerate(f, 1):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    d = json.loads(raw)
                except json.JSONDecodeError:
                    print(f"WARN {p}:{n} not JSON, skipped", file=sys.stderr)
                    continue
                if str(d.get("step", "")).upper().startswith("TOTAL"):
                    reported.append(dict(ledger=rel(p), cost_usd=float(d.get("cost_usd") or 0), note=d.get("step")))
                    continue
                if SKIP_CAP.search(str(d.get("capability", "-")).strip() or "-"):
                    continue
                jid = d.get("job_id")
                if jid and jid in seen:
                    continue
                if jid:
                    seen.add(jid)
                d["_ledger"] = rel(p)
                lines.append(d)
    return paths, lines, reported


def extract_thumb(src, name, t=None):
    if not src or not os.path.exists(src):
        return None
    if src.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        return rel(src)
    os.makedirs(THUMBS, exist_ok=True)
    out = os.path.join(THUMBS, name + ".jpg")
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(src):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t if t is not None else 5.0), "-i", src,
                        "-frames:v", "1", "-vf", "scale=480:-2", out], check=False)
    return rel(out) if os.path.exists(out) else None


def blurred_env_photo(src):
    if not src:
        return None
    if not ENV_BLUR_PX:
        return rel(src)
    from PIL import Image, ImageFilter
    out = os.path.join(HERE, "assets", f"photo_env_blur{ENV_BLUR_PX}.jpg")
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(src):
        Image.open(src).convert("RGB").filter(ImageFilter.GaussianBlur(ENV_BLUR_PX)).save(out, quality=90)
    return rel(out)


# --------------------------------------------------------------------------
# Prompt
# --------------------------------------------------------------------------
BLOCK_NAMES = [("ASSETS", "Asset block"), ("SUMMARY", "Summary"), ("STYLE", "Style"),
               ("PLOT", "Shot-by-shot plot"), ("REQUIREMENTS", "Locked rules")]


def load_prompt():
    """prompts/prompt_*.txt is the call sheet that made the final (prompt_v4_t2v.txt)."""
    cands = sorted(glob.glob(os.path.join(S, "prompts", "prompt_*.txt")))
    if not cands:
        sys.exit("no prompts/prompt_*.txt found")
    p = cands[-1]
    return open(p).read(), rel(p), False


def clean(s):
    s = re.sub(r"\{\{[^}]*\}\}", "", s)
    return re.sub(r"\s+", " ", s).strip()


def short(s, words=11):
    w = clean(s).split(" ")
    return " ".join(w[:words]) + ("…" if len(w) > words else "")


def first_clause(s):
    return re.split(r"(?<=[a-z0-9\"”])[.;,](\s|$)", clean(s), maxsplit=1)[0]


ACTION = re.compile(r"click|snap|sip|drink|mouthful|freez|motionless|stops?\b|fade|resum|undoes", re.I)


def sentences(s):
    return [x for x in re.split(r"(?<=[.!?])\s+", clean(s)) if x]


def action_clause(s):
    for sent in sentences(s):
        if ACTION.search(sent):
            for c in re.split(r"[,;]\s*", sent.rstrip(".")):
                if ACTION.search(c):
                    return c
    return first_clause(s)


def parse_prompt(text):
    parts = re.split(r"^\[(ASSETS|SUMMARY|STYLE|PLOT|REQUIREMENTS)\]\s*$", text, flags=re.M)
    blocks = {parts[i]: parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}
    out = []
    for tag, name in BLOCK_NAMES:
        body = blocks.get(tag, "")
        lines = [l.strip() for l in body.splitlines() if l.strip() and not l.strip().startswith("{{")]
        keys, hi = [], 0
        if tag == "ASSETS":
            for l in lines:
                m = re.match(r"(@Image\d\s*[—-]\s*)?([A-Z][A-Z \-]+?)(\s*[—-]\s*\"[^\"]+\")?\s*:\s*(.*)", l)
                if m:
                    label = (m.group(1) or "").strip(" —-") + " " + m.group(2).strip() + (m.group(3) or "").replace("—", "").replace(" -", "")
                    keys.append(dict(tag=clean(label), text=short(m.group(4), 12)))
            if tag == "ASSETS" and keys:
                name = "Asset binding" if any("@Image" in k["tag"] for k in keys) else "Cast + location, in words"
        elif tag == "SUMMARY":
            ss = sentences(body)
            pick = next((x for x in ss if ACTION.search(x)), ss[0] if ss else "")
            keys.append(dict(text=short(pick, 16)))
        elif tag == "STYLE":
            m = re.search(r"(single|one)\s+(unbroken|continuous)\s+take", body, re.I)
            if m:
                keys.append(dict(text=m.group(0)[0].upper() + m.group(0)[1:]))
            frags = [f.strip() for f in re.split(r"[.,;:]", clean(body)) if 2 <= len(f.split()) <= 4]
            for f in frags:
                if len(keys) >= 6:
                    break
                if not any(f.lower() in k["text"].lower() for k in keys):
                    keys.append(dict(text=f[0].upper() + f[1:]))
        elif tag == "PLOT":
            for l in lines:
                m = re.match(r"(\d+\s*[–-]\s*\d+\s*s)\s*:\s*(.*)", l)
                if m:
                    c = action_clause(re.sub(r"Sound:.*", "", m.group(2)))
                    keys.append(dict(tag=m.group(1).replace(" ", ""), text=short(c[0].upper() + c[1:], 9)))
            hi = next((i for i, k in enumerate(keys) if re.search(r"click|snap", k["text"], re.I)), 0)
        elif tag == "REQUIREMENTS":
            bullets = [re.sub(r"^-\s*", "", l) for l in lines if l.startswith("-")]
            pri = [b for b in bullets if re.search(r"unbroken|continuous take|nothing moves|COMPLETELY", b, re.I)]
            pri += [b for b in bullets if re.search(r"cup|real filmed", b, re.I) and b not in pri]
            pri = pri or bullets[:3]
            keys = [dict(text=short(re.split(r"[;:]", sentences(b)[0])[0].rstrip("."), 10)) for b in pri[:3]]
        out.append(dict(tag=tag, name=name, keys=keys, highlight=hi,
                        n_lines=len(lines), n_words=len(clean(body).split())))
    return out, blocks


# --------------------------------------------------------------------------
def main():
    ledgers, lines, reported = read_ledgers()
    rowdef = {r["key"]: r for r in ROWS}
    groups = {}
    for l in lines:
        k = classify(l)
        g = groups.setdefault(k, dict(cost=0.0, n=0, lines=[], reserved=0.0))
        g["cost"] += float(l.get("cost_usd") or 0)
        g["reserved"] += float(l.get("reserved_usd") or 0)
        g["n"] += 1
        g["lines"].append(l)

    final_real = "final" in groups and groups["final"]["cost"] > 0
    clip = local("outputs/post1_freeze_frame.mp4")
    charsheet = os.path.join(S, "refs", "charsheet_v3.jpg")
    char_single = os.path.join(S, "refs", "char_v3_single.jpg")
    envsheet = os.path.join(S, "refs", "envsheet_v1.jpg")
    # Your own input street photo (not shipped in the repo). Without it the location sheet stands in.
    env_photo = existing(*(os.path.join(S, "refs", f"street_photo.{e}") for e in ("jpg", "jpeg", "png")))

    def thumb_for(key, g):
        if key == "location":
            return rel(envsheet)
        if key == "character":
            return rel(charsheet)
        if key == "char_photo":
            return rel(char_single)
        if key in ("early", "refused"):
            return None                         # never show the unused character
        if key == "failed":
            return None                         # rejected sheet carries real signage: no thumb
        if key in ("final", "draft") and clip:
            return extract_thumb(clip, key, 4.6)
        if key == "probes":            # the probe clip is not shipped; the cached thumb is
            p = os.path.join(THUMBS, "probes.jpg")
            return rel(p) if os.path.exists(p) else None
        return None

    steps = []
    keys = ROW_ORDER + sorted(k for k in groups if k not in ROW_ORDER)
    for k in keys:
        g = groups.get(k)
        r = rowdef.get(k, dict(key=k, label=k.split(":")[-1], model=k.split(":")[-1], capability=k.split(":")[-1]))
        if not g and not (k == "final" and not final_real):
            continue
        ph = k == "final" and not final_real
        n = g["n"] if g else 1
        cost = g["cost"] if g and not ph else r.get("est", 0.0) if ph else 0.0
        caps = sorted(set(str(l.get("capability")) for l in (g["lines"] if g else [])))
        models = " · ".join(dict.fromkeys(next((v for k2, v in MODEL_NAMES.items() if k2 in c.lower()), c) for c in caps))
        steps.append(dict(
            key=k, label=r["label"].replace("{n}", str(n)),
            model=r["model"].replace("{models}", models).replace("{n} runs", f"{n} run" + ("s" if n != 1 else "")).replace("{n}", str(n)),
            capability=r["capability"] or " · ".join(caps), cost_usd=round(cost, 2), n_calls=n,
            thumb=thumb_for(k, g), status=r.get("kind", "ok"), placeholder=ph,
            reserved_usd=round(g["reserved"], 4) if g else 0.0))

    exact = {s["key"]: (groups[s["key"]]["cost"] if s["key"] in groups and not s["placeholder"] else s["cost_usd"])
             for s in steps}
    total = round(sum(exact.values()) + 1e-9, 2)
    cents = {k: int(v * 100 + 1e-9) for k, v in exact.items()}
    left = int(round(total * 100)) - sum(cents.values())
    for k in sorted(exact, key=lambda k: -(exact[k] * 100 - cents[k]))[:max(0, left)]:
        cents[k] += 1
    for st in steps:
        st["cost_usd"] = cents[st["key"]] / 100
        st["exact_usd"] = round(exact[st["key"]], 4)
    n_calls = sum(s["n_calls"] for s in steps if not s["placeholder"]) + (1 if not final_real else 0)
    ledger_net = round(sum(float(l.get("cost_usd") or 0) for l in lines), 4)
    reserved = round(sum(float(l.get("reserved_usd") or 0) for l in lines), 4)
    per_ledger = {}
    for l in lines:
        per_ledger[l["_ledger"]] = round(per_ledger.get(l["_ledger"], 0.0) + float(l.get("cost_usd") or 0), 4)
    checks = []
    for r in reported:
        items = round(per_ledger.get(r["ledger"], 0.0), 2)
        checks.append(dict(r, line_items_usd=items, match=abs(items - r["cost_usd"]) < 0.005))
    recon = dict(ledger_net_usd=ledger_net, rows_sum_usd=total, released_reservations_usd=reserved,
                 per_ledger=per_ledger, ledger_total_lines=checks, sessions=SESSIONS,
                 note="On screen = ledger net cost_usd. Compare with get_cost_report(scope=session) for SESSIONS; "
                      "that report shows gross (released moderation holds not netted).")
    if final_real and abs(ledger_net - total) > 0.01:
        print(f"WARN rows ${total} != ledger net ${ledger_net}", file=sys.stderr)

    ptext, psrc, pdraft = load_prompt()
    blocks, raw_blocks = parse_prompt(ptext)
    char_desc = ""
    m = re.search(r"CHARACTER[^:]*:\s*(.*)", raw_blocks.get("ASSETS", ""))
    if m:
        body = m.group(1)
        who = sentences(body)[0]
        look = re.search(r"Her look never changes:\s*([^.]*)", body)
        char_desc = who + (" " + look.group(1)[0].upper() + look.group(1)[1:] + "." if look else "")
    refused_n = 0     # v3: the safety-check beat is gone
    recipe = build_recipe(lines, raw_blocks)

    vo = None
    vo_p = os.path.join(HERE, "vo", "lines.json")
    if os.path.exists(vo_p):
        v = json.load(open(vo_p))
        vo = dict(voice=v["voice"], capability=v["capability"], gap=0.2,
                  lines=[dict(key=l["key"], text=l["text"], file=f"vo/proc/{l['key']}.wav", dur=l.get("dur"))
                         for l in v["lines"] if l.get("dur") and os.path.exists(os.path.join(HERE, "vo", "proc", l["key"] + ".wav"))])
    # The narrated total must say exactly what the screen shows.
    said = next((l["text"] for l in (vo or {}).get("lines", []) if l["key"] == "total"), None)
    if said is not None and spoken_money(total) not in said.lower():
        print(f"WARN spoken total {said!r} != on-screen ${total:.2f} ({spoken_money(total)}): "
              f"re-generate the 'total' narration line", file=sys.stderr)
    ap = os.path.join(HERE, "assets", "approval")
    data = dict(
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        dryrun=not (final_real and clip),
        ledgers=[rel(p) for p in ledgers],
        total_usd=total, total_placeholder=not final_real, n_calls=n_calls,
        reconciliation=recon,
        total_spoken=spoken_money(total),
        vo=vo,
        steps=steps,
        assets=dict(
            photo_env=blurred_env_photo(env_photo) or rel(envsheet),
            charsheet=rel(charsheet), char_single=rel(char_single), envsheet=rel(envsheet),
            wordmark="assets/brand/livepeer_wordmark.png", badge="assets/brand/badge.png",
        ),
        character_text=clean(char_desc),
        recipe=recipe,
        clip=dict(source=rel(clip) if clip else rel(envsheet), placeholder=not bool(clip),
                  placeholder_crop=[0, 20, 1036, 603], frames_dir="assets/clip", fps=30, duration_s=15.0,
                  hook_start_s=3.2, outro_start_s=9.0),
        prompt=dict(source=psrc, placeholder=pdraft, model="Seedance 2.5",
                    capability="seedance-25-t2v", blocks=blocks),
        approval=dict(page=rel(os.path.join(S, "explainer", "approve", "freeze-frame-signoff.html")),
                      full=rel(os.path.join(ap, "from_plan.png")), answers=rel(os.path.join(ap, "answers.png"))),
        text=dict(
            hook="One 15-second shot. Made entirely by AI.",
            photos="It starts with a photo and a description.",
            sheets="AI turns them into reference images.",
            prompt_intro="One prompt, written like a call sheet.",
            costs="Every model call, and what it cost.",
            total_sub="{n} model calls · one finished shot",
            outro_url="earlyaccess.livepeer.org",
            loop=["AI plans", "Human approves", "AI executes"],
            blocks=dict(ASSETS="1 · Cast and location, in words.",
                        SUMMARY="2 · The whole story in one line.",
                        STYLE="3 · Camera, light, grade. Never changes.",
                        PLOT="4 · Second by second, what happens.",
                        REQUIREMENTS="5 · Hard rules. Every defect adds one."),
        ),
    )
    with open(OUT, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    if "-v" in sys.argv:
        for l in lines:
            print(f"    {classify(l):<10} ${float(l.get('cost_usd') or 0):6.3f}  {str(l.get('step'))[:90]}")
    print(f"wrote {OUT}  mode: {'DRY RUN' if data['dryrun'] else 'FINAL'}  prompt: {psrc}")
    for s in steps:
        print(f"  {'PH ' if s['placeholder'] else '   '}{s['label']:<48} {s['model']:<34} ${s['cost_usd']:>6.2f}  x{s['n_calls']}")
    print(f"  TOTAL ${total:.2f}  ({n_calls} calls)  ledger net ${ledger_net:.4f}  released holds ${reserved:.2f}")


ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def words(n):
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10] + ("-" + ONES[n % 10] if n % 10 else "")
    return ONES[n // 100] + " hundred" + (" and " + words(n % 100) if n % 100 else "")


def spoken_money(v):
    c = int(round(v * 100))
    d, c = divmod(c, 100)
    out = f"{words(d)} dollar{'s' if d != 1 else ''}"
    if c:
        out += f" and {words(c)} cent{'s' if c != 1 else ''}"
    return out


def read_recipe(name):
    p = os.path.join(S, "prompts", name)
    if not os.path.exists(p):
        return None
    head, _, body = open(p).read().partition("\n")
    return dict(meta=[x.strip() for x in head.split("|")], text=body.strip(), file=rel(p))


def build_recipe(lines, raw_blocks):
    fin = next((l for l in reversed(lines) if "seedance-25-t2v" in _cap(l) and float(l.get("cost_usd") or 0) > 0), None)
    render = None
    if fin:
        mins = round(float(fin.get("duration_s") or 0) / 60)
        render = dict(capability=fin["capability"], model="Seedance 2.5 · text-to-video",
                      settings=['prompt: the 5 blocks, as one text', 'duration: "15"', 'resolution: "720p"', 'aspect_ratio: "16:9"',
                                'generate_audio: true', 'async: true → poll get_create_media'],
                      time=f"~{mins} min render" if mins else "", cost=round(float(fin["cost_usd"]), 2))
    sfx = [l for l in lines if _step(l).startswith("sound effects")]
    one = []
    for l in sfx:
        if "v2v" in _cap(l):
            continue
        lab = re.sub(r"^Sound effects:\s*", "", l["step"])
        used = not re.search(r"unused", lab, re.I)
        lab = re.sub(r"\s*\((?:[^()]|\([^)]*\))*\)", "", lab).strip()
        dur = (re.search(r"duration=(\d+)s", str(l.get("inputs", ""))) or [None, "?"])[1]
        one.append(dict(text=lab, dur=dur, cost=float(l.get("cost_usd") or 0), used=used))
    v2v = next((l for l in sfx if "v2v" in _cap(l)), None)
    events = None
    mix = os.path.join(S, "sound", "mix.sh")
    if os.path.exists(mix):
        m = re.search(r"Event times \(s\):\s*(.*)", open(mix).read())
        events = m.group(1) if m else None
    sound = dict(oneshots=one, cost=round(sum(float(l.get("cost_usd") or 0) for l in sfx), 2), n=len(sfx),
                 v2v=dict(capability="mirelo-sfx-v2v", text=re.sub(r"^Sound effects:\s*", "", v2v["step"]),
                          dur=(re.search(r"duration=(\d+)s", str(v2v.get("inputs", ""))) or [None, "15"])[1]) if v2v else None,
                 events=events,
                 timeline=[dict(t=3.95, label="snap 1"), dict(t=3.96, t2=12.13, label="freeze · native audio −30 dB · 6.2 kHz ring"),
                           dict(t=9.85, label="sip"), dict(t=12.13, label="snap 2"), dict(t=14.17, t2=15.0, label="fade")],
                 mix="ffmpeg: adelay each hit → amix normalize=0 → alimiter → loudnorm −14 LUFS")
    return dict(location=read_recipe("envsheet_prompt.txt"), location_screen=read_recipe("envsheet_prompt_onscreen.txt"), location_fix=read_recipe("envsheet_fix_prompt.txt"),
                character=read_recipe("charsheet_v3_prompt.txt"), single=read_recipe("char_v3_single_prompt.txt"),
                blocks_full={k: v.strip() for k, v in raw_blocks.items()}, render=render, sound=sound)


def first_glob(pat):
    g = sorted(glob.glob(pat))
    return g[0] if g else None


if __name__ == "__main__":
    main()
