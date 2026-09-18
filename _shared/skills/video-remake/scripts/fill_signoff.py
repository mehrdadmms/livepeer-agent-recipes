#!/usr/bin/env python3
"""Fill assets/signoff_template.html from a JSON spec and emit one self-contained page.

Usage:
  python3 fill_signoff.py spec.json out.html [--max-width 1600] [--quality 82]

Images are downscaled (Pillow, if installed) and embedded as base64 JPEG so the
page has no external image dependencies. Spec shape: see ../assets/signoff_example.json.
Every string is HTML-escaped except fields named *_html (plan items may use <b>).
"""
import argparse, base64, html, io, json, mimetypes, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "assets" / "signoff_template.html"
e = lambda s: html.escape(str(s), quote=True)
slug = lambda s: re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "x"


def embed(path, max_w, quality):
    p = pathlib.Path(path).expanduser()
    if not p.is_file():
        sys.exit(f"image not found: {p}")
    try:
        from PIL import Image
        im = Image.open(p).convert("RGB")
        if im.width > max_w:
            im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=quality, optimize=True)
        return "image/jpeg", base64.b64encode(buf.getvalue()).decode()
    except ImportError:
        mime = mimetypes.guess_type(p.name)[0] or "image/png"
        return mime, base64.b64encode(p.read_bytes()).decode()


def sheet_html(s, max_w, q):
    mime, b64 = embed(s["image"], max_w, q)
    sid = s["id"]
    return f"""      <figure>
        <img src="data:{mime};base64,{b64}" alt="{e(s.get('alt', s['label']))}">
        <figcaption>
          <div><b>{e(s['label'])}</b><small>{e(s.get('note', ''))}</small></div>
          <div class="seg" role="radiogroup" aria-label="{e(s['label'])}">
            <input type="radio" name="{sid}" id="{sid}-ok" value="approve" checked><label class="yes" for="{sid}-ok">Approve</label>
            <input type="radio" name="{sid}" id="{sid}-no" value="redo"><label class="no" for="{sid}-no">Redo</label>
          </div>
          <input class="note" id="{sid}-note" placeholder="What to change?" hidden>
        </figcaption>
      </figure>"""


def plan_html(items):
    out, letter = [], 0
    for it in items:
        gate = it.get("gate", False)
        dot = "▲" if gate else "abcdefghij"[letter]
        if not gate:
            letter += 1
        body = it["html"] if "html" in it else e(it["text"])
        if gate and "html" not in it:
            body = f"<b>{body}</b>"
        cls = ' class="you"' if gate else ""
        out.append(f'      <li{cls}><span class="dot">{dot}</span><span>{body}</span></li>')
    return "\n".join(out)


def money_html(m):
    tiles = [("spent", m["spent"], m.get("spent_label", "spent so far")),
             ("", m["expected"], m.get("expected_label", "expected total")),
             ("", m["worst"], m.get("worst_label", "worst case with retries")),
             ("", m["hard_stop"], m.get("hard_stop_label", "hard stop"))]
    return "\n".join(f'      <div{" class=%s" % c if c else ""}><div class="v">{e(v)}</div><div class="k">{e(k)}</div></div>'
                     for c, v, k in tiles)


def beats_html(beats):
    return "\n".join(f'      <div><b>{e(b["t"])}</b>{e(b["what"])}</div>' for b in beats)


def questions_html(qs):
    out = []
    for q in qs:
        qid = q["id"]
        hint = f' <small>{e(q["hint"])}</small>' if q.get("hint") else ""
        default = q.get("default", 0)
        opts = []
        for i, o in enumerate(q["options"]):
            label, value = (o, o) if isinstance(o, str) else (o["label"], o.get("value", o["label"]))
            chk = " checked" if i == default else ""
            opts.append(f'          <input type="radio" name="{qid}" id="{qid}{i}" value="{e(value)}"{chk}><label for="{qid}{i}">{e(label)}</label>')
        out.append(f'      <div class="q"><p>{e(q["question"])}{hint}</p>\n        <div class="opts">\n' + "\n".join(opts) + "\n        </div></div>")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec"); ap.add_argument("out")
    ap.add_argument("--max-width", type=int, default=1600)
    ap.add_argument("--quality", type=int, default=82)
    ap.add_argument("--allow-source-words", action="store_true")
    a = ap.parse_args()
    spec = json.loads(pathlib.Path(a.spec).read_text())
    base = pathlib.Path(a.spec).resolve().parent

    for s in spec["sheets"]:
        s.setdefault("id", slug(s["label"]))
        if not pathlib.Path(s["image"]).is_absolute():
            s["image"] = str(base / s["image"])
    for q in spec["questions"]:
        q.setdefault("id", slug(q.get("label", q["question"]))[:24])
        q.setdefault("label", q["question"])
    # The page is captured inside the public explainer: it must not reveal a source video.
    banned = re.compile(r"\b(remake|remade|recreat\w*|inspired by|original (video|clip|prompt)|source (video|clip|prompt)|higgsfield)\b", re.I)
    hits = sorted({m.group(0) for m in banned.finditer(json.dumps({k: v for k, v in spec.items() if not k.startswith("_")}))})
    if hits and not a.allow_source_words:
        sys.exit(f"source-revealing words in spec (page is shown in the explainer): {hits}. Reword, or pass --allow-source-words for a private-only page.")
    if len(spec["questions"]) > 5:
        print("warn: more than 5 quick decisions; the user asked for <=5", file=sys.stderr)
    if len(spec["plan"]) > 7:
        print("warn: plan is long; keep it to <=5 steps plus gates", file=sys.stderr)

    cfg = {"sheets": [{"id": s["id"], "label": s["label"]} for s in spec["sheets"]],
           "questions": [{"id": q["id"], "label": q["label"]} for q in spec["questions"]],
           "footer": spec.get("footer", [f"Plan + budget ({spec['money']['hard_stop']} hard stop): approved"])}

    t = TEMPLATE.read_text()
    fills = {
        "TITLE": e(spec["title"]),
        "TITLE_ACCENT": e(spec.get("title_accent", "Sign-off")),
        "LEDE": e(spec["lede"]),
        "SHEETS": "\n".join(sheet_html(s, a.max_width, a.quality) for s in spec["sheets"]),
        "PLAN": plan_html(spec["plan"]),
        "MONEY": money_html(spec["money"]),
        "BEATS_HEADING": e(spec.get("beats_heading", "Post 2 at a glance")),
        "BEATS": beats_html(spec["beats"]),
        "BEATS_NOTE": e(spec.get("beats_note", "")),
        "QUESTIONS": questions_html(spec["questions"]),
        "CONFIG_JSON": json.dumps(cfg).replace("</", "<\\/"),
    }
    # strip the maintainer comment block from the emitted page
    t = re.sub(r"\A<!--.*?-->\s*", "", t, flags=re.S)
    for k, v in fills.items():
        t = t.replace("{{" + k + "}}", v)
    left = re.findall(r"\{\{[A-Z_]+\}\}", t)
    if left:
        sys.exit(f"unfilled placeholders: {sorted(set(left))}")
    pathlib.Path(a.out).write_text(t)
    print(f"wrote {a.out} ({len(t)/1e6:.2f} MB)")


if __name__ == "__main__":
    main()
