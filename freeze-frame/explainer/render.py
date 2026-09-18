#!/usr/bin/env python3
"""Post 2 ("how this shot was made") renderer.  ONE command, zero manual edits:

    cd freeze-frame/explainer && python3 render.py

All paths are relative to this folder / the recipe folder (freeze-frame/), so it runs from the repo.
What it does, in order (every step is cached and redone only when its input changed):
  1. brand     uses the shipped assets/brand/*.png (Livepeer wordmark + badge). Re-cropped only if
               brand source frames are dropped into assets/brand/src/.
  2. approval  uses the shipped assets/approval/ captures. If you build your own sign-off page, save it
               as explainer/approve/freeze-frame-signoff.html and it is re-captured in headless
               Chromium (Playwright): full-page screenshot, scroll-through frames, the answer block.
  3. data      runs build_data.py  (../ledger/cost_log*.jsonl -> post2_data.json)  and writes
               post2_data.js (window.POST2_DATA) for template.html
  4. clip      final clip -> 1280x720 JPG sequence in assets/clip/ ; while Post 1 is not final
               a looping still from the env sheet is used and the template stamps PLACEHOLDER
  5. frames    template.html render(t) -> one screenshot per frame (30 fps) -> frames/
  6. audio     synthesised bed + ticks on the template's cue list (+ clip audio in hook/outro
               if the real clip has sound) -> audio.wav
  7. encode    H.264 yuv420p + AAC 192k, 1280x720, 30 fps
  8. contact   1-frame-per-second contact sheet (PIL)

Outputs: post2_dryrun.mp4 / post2_dryrun_contact.jpg while any PLACEHOLDER value is present,
         post2_final.mp4  / post2_final_contact.jpg once everything is real.
Options: --out NAME (basename override)  --only-frames  --fps 30  --preview T (one PNG at time T)
Needs: python3 + playwright (chromium), Pillow, ffmpeg.  Local ffmpeg has no drawtext: all text is HTML.
"""
import argparse
import array
import asyncio
import glob
import json
import math
import os
import random
import shutil
import subprocess
import sys
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
S = os.path.dirname(HERE)          # recipe root (freeze-frame/)
A = os.path.join(HERE, "assets")
SR = 48000


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        sys.exit(f"FAILED: {' '.join(cmd)}\n{r.stderr[-2000:]}")
    return r.stdout


def stale(out, *inputs):
    if not os.path.exists(out):
        return True
    m = os.path.getmtime(out)
    return any(os.path.exists(i) and os.path.getmtime(i) > m for i in inputs)


# ---------------------------------------------------------------- 1. brand
def prep_brand():
    from PIL import Image, ImageDraw
    d = os.path.join(A, "brand")
    os.makedirs(d, exist_ok=True)
    # The shipped PNGs are used as-is. To re-crop, put 1280x720 frames showing the wordmark and the
    # badge at these names; the crop boxes below match those frames.
    wm_src = os.path.join(d, "src", "wordmark_frame.png")
    bd_src = os.path.join(d, "src", "badge_frame.png")
    wm, bd = os.path.join(d, "livepeer_wordmark.png"), os.path.join(d, "badge.png")
    if not (os.path.exists(wm_src) and os.path.exists(bd_src)):
        if os.path.exists(wm) and os.path.exists(bd):
            return
        sys.exit("assets/brand/*.png missing and no assets/brand/src/ frames to crop them from")
    if stale(wm, wm_src):
        im = Image.open(wm_src).convert("RGB").crop((418, 276, 862, 349))
        alpha = im.convert("L").point(lambda v: 0 if v < 18 else min(255, int((v - 18) * 1.5)))
        im.putalpha(alpha)
        im.save(wm)
    if stale(bd, bd_src):
        im = Image.open(bd_src).convert("RGB").crop((1189, 629, 1238, 678)).resize((196, 196), Image.LANCZOS)
        mask = Image.new("L", (196, 196), 0)
        ImageDraw.Draw(mask).ellipse((2, 2, 193, 193), fill=255)
        im.putalpha(mask)
        im.save(bd)


# ---------------------------------------------------------------- 2. approval page
async def capture_approval():
    from playwright.async_api import async_playwright
    page_path = os.path.join(HERE, "approve", "freeze-frame-signoff.html")
    d = os.path.join(A, "approval")
    meta_p = os.path.join(d, "meta.json")
    if not os.path.exists(page_path):          # repo default: use the shipped captures
        if os.path.exists(meta_p):
            return json.load(open(meta_p))
        sys.exit("no approve/freeze-frame-signoff.html and no cached assets/approval/meta.json")
    if not stale(meta_p, page_path):
        return json.load(open(meta_p))
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(os.path.join(d, "scroll"))
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1280, "height": 720})
        await pg.goto("file://" + page_path, wait_until="networkidle")
        await pg.evaluate("document.fonts.ready.then(()=>1)")
        # grow the answer textarea so the whole pasted block is visible
        await pg.evaluate("""()=>{const t=document.querySelector('#out'); if(t){t.style.height=(t.scrollHeight+4)+'px'}}""")
        info = await pg.evaluate("""()=>{
            const secs=[...document.querySelectorAll('section')].map(s=>({t:(s.querySelector('h2')||{}).textContent||'',y:s.getBoundingClientRect().top+scrollY}));
            return {height:document.documentElement.scrollHeight,width:document.documentElement.clientWidth,secs};}""")
        await pg.screenshot(path=os.path.join(d, "full.png"), full_page=True)
        send = await pg.query_selector(".send") or await pg.query_selector("textarea")
        await send.screenshot(path=os.path.join(d, "answers.png"))
        answers_text = await pg.evaluate("()=>(document.querySelector('#out')||{}).value||''")
        # Only the plan / cost / decisions part of the real page is shown: section 1 carries the
        # sheet images of the unused first character, so everything above "The plan" is cropped off.
        labels = [("plan", "Plan"), ("cost", "Budget"), ("budget", "Budget"), ("decision", "5 decisions")]
        sections, used = [], set()
        for s in info["secs"]:
            for k, lab in labels:
                if k in s["t"].lower() and lab not in used:
                    used.add(lab)
                    sections.append(dict(label=lab, y=round(s["y"])))
                    break
        top = max(0, sections[0]["y"] - 24) if sections else 0
        from PIL import Image
        full = Image.open(os.path.join(d, "full.png"))
        full.crop((0, top, full.size[0], full.size[1])).save(os.path.join(d, "from_plan.png"))
        for s in sections:
            s["y"] -= top
        # smooth scroll-through at 1280x720 (2.5 s @ 30 fps), eased, from "The plan" to the bottom
        maxy = max(0, info["height"] - 720)
        n = 75
        for i in range(n):
            u = i / (n - 1)
            e = u * u * (3 - 2 * u)
            await pg.evaluate(f"window.scrollTo(0,{round(top + e * (maxy - top))})")
            await pg.screenshot(path=os.path.join(d, "scroll", f"{i + 1:04d}.png"))
        await b.close()
    meta = dict(width=info["width"], height=info["height"] - top, crop_top=top, sections=sections,
                answers_text=answers_text, scroll_frames=n)
    json.dump(meta, open(meta_p, "w"), indent=2)
    return meta


# ---------------------------------------------------------------- 4. clip frames
def prep_clip(data):
    c = data["clip"]
    src = os.path.normpath(os.path.join(HERE, c["source"]))
    d = os.path.join(HERE, c["frames_dir"])
    stamp = os.path.join(d, ".source")
    key = f"{src}|{os.path.getmtime(src)}|{c['placeholder']}|{c.get('placeholder_crop')}"
    if os.path.exists(stamp) and open(stamp).read() == key:
        return len(glob.glob(os.path.join(d, "*.jpg")))
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    if c["placeholder"]:
        x0, y0, x1, y1 = c["placeholder_crop"]
        w, h = x1 - x0, y1 - y0
        n = int(c["duration_s"] * c["fps"])
        vf = (f"crop={w}:{h}:{x0}:{y0},scale=3840:-2,"
              f"zoompan=z='1.0+0.06*(0.5-0.5*cos(2*PI*on/{n}))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s=1280x720:fps={c['fps']}")
        run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", src, "-vf", vf, "-frames:v", str(n), "-q:v", "3",
             os.path.join(d, "%04d.jpg")])
    else:
        run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf",
             f"fps={c['fps']},scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720",
             "-q:v", "3", os.path.join(d, "%04d.jpg")])
    open(stamp, "w").write(key)
    return len(glob.glob(os.path.join(d, "*.jpg")))


def clip_has_audio(data):
    if data["clip"]["placeholder"]:
        return False
    src = os.path.normpath(os.path.join(HERE, data["clip"]["source"]))
    out = run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", src])
    return bool(out.strip())


# ---------------------------------------------------------------- 5. frames
async def render_frames(fps, frames_dir, preview=None):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--allow-file-access-from-files"])
        pg = await b.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
        await pg.goto("file://" + os.path.join(HERE, "template.html"))
        await pg.evaluate("window.READY")
        if errs:
            sys.exit("template errors:\n" + "\n".join(errs))
        tl = await pg.evaluate("({duration:TIMELINE.duration,cues:TIMELINE.cues,clip:TIMELINE.clip,segments:TIMELINE.segments,vo:TIMELINE.vo||[]})")
        if preview is not None:
            for t in preview:
                await pg.evaluate(f"render({t})")
                out = os.path.join(HERE, f"preview_{t:05.2f}.png")
                await pg.screenshot(path=out)
                print("preview", out)
            await b.close()
            return tl
        shutil.rmtree(frames_dir, ignore_errors=True)
        os.makedirs(frames_dir)
        n = int(round(tl["duration"] * fps))
        for i in range(n):
            await pg.evaluate(f"render({i / fps})")
            await pg.screenshot(path=os.path.join(frames_dir, f"{i + 1:05d}.jpg"), type="jpeg", quality=94)
            if i % 150 == 0:
                print(f"  frame {i}/{n}", flush=True)
        await b.close()
        if errs:
            print("WARN page errors:", errs[:5])
    return tl


# ---------------------------------------------------------------- 6. audio
VO_DUCK = 10 ** (-10 / 20)      # music bed sits 10 dB lower while the narrator speaks


def vo_gain(t, vo, depth=VO_DUCK, ramp=0.12):
    g = 1.0
    for c in vo:
        a, b = c["t"], c["t"] + c["dur"]
        if a - ramp < t < b + ramp:
            k = min(1.0, (t - (a - ramp)) / ramp, ((b + ramp) - t) / ramp)
            g = min(g, 1 - (1 - depth) * k)
    return g


def synth_audio(tl, path, duck=(), vo=()):
    dur = tl["duration"]
    n = int(dur * SR) + 1
    buf = array.array("f", [0.0]) * n
    rnd = random.Random(7)
    # bed: soft low drone + filtered air, gentle swell, ducked under real clip audio
    lp = 0.0
    for i in range(n):
        t = i / SR
        env = min(1.0, t / 1.5, (dur - t) / 1.2)
        d = 1.0
        for a, b in duck:
            if a - .3 < t < b + .3:
                d = 0.25
        lp += 0.02 * (rnd.uniform(-1, 1) - lp)
        v = (0.035 * math.sin(2 * math.pi * 55 * t) + 0.022 * math.sin(2 * math.pi * 82.41 * t)
             + 0.018 * math.sin(2 * math.pi * 110 * t + 0.4 * math.sin(2 * math.pi * 0.2 * t))) * (0.8 + 0.2 * math.sin(2 * math.pi * t / 7.0))
        buf[i] = (v + 0.10 * lp) * env * d * (vo_gain(t, vo) if vo else 1.0)

    def add(t0, f, length, amp, decay, noise=0.0, sweep=0.0):
        i0 = int(t0 * SR)
        lpn = 0.0
        for k in range(int(length * SR)):
            i = i0 + k
            if i >= n:
                break
            tt = k / SR
            e = math.exp(-tt * decay) * min(1.0, tt * 400)
            s = math.sin(2 * math.pi * (f + sweep * tt) * tt)
            if noise:
                lpn += 0.08 * (rnd.uniform(-1, 1) - lpn)
                s = (1 - noise) * s + noise * lpn * 6
            buf[i] += amp * e * s

    for c in tl["cues"]:
        k, t = c["kind"], c["t"]
        if k == "tick":
            add(t, 1760, 0.06, 0.16, 70)
            add(t, 3520, 0.03, 0.04, 120)
        elif k == "tickLow":
            add(t, 520, 0.12, 0.2, 35)
        elif k == "whoosh":
            # rising filtered noise ending on the cut
            i0 = int((t - 0.35) * SR)
            lpn = 0.0
            for kk in range(int(0.5 * SR)):
                i = i0 + kk
                if 0 <= i < n:
                    tt = kk / SR
                    e = math.sin(math.pi * min(1.0, tt / 0.5)) ** 2
                    lpn += (0.02 + 0.1 * tt) * (rnd.uniform(-1, 1) - lpn)
                    buf[i] += 0.35 * e * lpn
        elif k == "thump":
            add(t, 62, 0.6, 0.35, 7, sweep=-20)
    peak = max(1e-6, max(abs(x) for x in buf))
    g = (0.5 if vo else 0.89) / peak     # with VO: leave headroom, loudnorm sets the final level
    pcm = array.array("h", (int(max(-1, min(1, x * g)) * 32767) for x in buf))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def vo_track(tl, path):
    """Place every processed narration line at its cue time (mono, 48 kHz)."""
    n = int(tl["duration"] * SR) + 1
    buf = array.array("h", [0]) * n
    for c in tl["vo"]:
        with wave.open(os.path.join(HERE, c["file"])) as w:
            assert w.getframerate() == SR and w.getnchannels() == 1 and w.getsampwidth() == 2
            pcm = array.array("h", w.readframes(w.getnframes()))
        i0 = int(round(c["t"] * SR))
        if i0 + len(pcm) > n:
            sys.exit(f"VO line {c['key']} runs past the end of the video")
        buf[i0:i0 + len(pcm)] = pcm
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(buf.tobytes())


def final_mix(data, tl, bed, vo_wav, out):
    """bed+ticks (already ducked) + VO + clip audio (ducked under VO) -> -14 LUFS / -1.5 dBTP."""
    src = os.path.normpath(os.path.join(HERE, data["clip"]["source"]))
    has = clip_has_audio(data)
    inputs, filt, labels = ["-i", bed, "-i", vo_wav], [], []
    labels = ["[0:a]", "[v]"]
    filt.append("[1:a]volume=1.0[v]")
    if has:
        for j, c in enumerate(tl["clip"]):
            inputs += ["-ss", str(c["from"]), "-t", str(c["dur"] + 0.3), "-i", src]
            ms = int(c["at"] * 1000)
            # duck terms for VO lines that fall inside this clip segment (times relative to the segment)
            terms = []
            for v in tl["vo"]:
                a, b = v["t"] - c["at"], v["t"] + v["dur"] - c["at"]
                if b > 0 and a < c["dur"]:
                    terms.append(f"(1-0.75*max(0,min(1,min((t-({a:.3f}-0.15))/0.15,(({b:.3f}+0.2)-t)/0.2))))")
            duck = "*".join(terms) if terms else "1"
            filt.append(f"[{j + 2}:a]aformat=sample_rates={SR}:channel_layouts=mono,afade=t=in:d=0.15,"
                        f"afade=t=out:st={c['dur'] - 0.1}:d=0.35,volume='1.4*{duck}':eval=frame,adelay={ms}|{ms}[c{j}]")
            labels.append(f"[c{j}]")
    filt.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=first,"
                f"alimiter=limit=0.35:attack=2:release=60:level=false,pan=stereo|c0=c0|c1=c0[m]")
    pre = out.replace(".wav", "_pre.wav")
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(filt), "-map", "[m]", "-ar", str(SR), pre])
    # two-pass loudnorm
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", pre, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    m = json.loads(r[r.rindex("{"):r.rindex("}") + 1])
    ln = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    run(["ffmpeg", "-v", "error", "-y", "-i", pre, "-af", ln + f",aresample={SR}", "-ar", str(SR), out])
    print("  loudnorm pass-1:", {k: m[k] for k in ("input_i", "input_tp", "target_offset")})


def mix_clip_audio(data, tl, bed, out):
    """Lay the real clip's own sound under the hook and outro segments."""
    src = os.path.normpath(os.path.join(HERE, data["clip"]["source"]))
    inputs, filt, labels = ["-i", bed], [], ["[0:a]"]
    for j, c in enumerate(tl["clip"]):
        inputs += ["-ss", str(c["from"]), "-t", str(c["dur"] + 0.3), "-i", src]
        ms = int(c["at"] * 1000)
        filt.append(f"[{j + 1}:a]aformat=sample_rates={SR}:channel_layouts=mono,afade=t=in:d=0.15,"
                    f"afade=t=out:st={c['dur'] - 0.1}:d=0.35,volume=1.8,adelay={ms}|{ms}[c{j}]")
        labels.append(f"[c{j}]")
    filt.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=first,alimiter=limit=0.95[a]")
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(filt), "-map", "[a]", out])


# ---------------------------------------------------------------- 8. contact sheet
def contact_sheet(frames_dir, fps, out, cols=6, every=1.0):
    from PIL import Image, ImageDraw, ImageFont
    files = sorted(glob.glob(os.path.join(frames_dir, "*.jpg")))
    picks = [(i, f) for i, f in enumerate(files) if i % int(round(fps * every)) == int(fps * every * 0.5)]
    tw, th = 400, 225
    rows = math.ceil(len(picks) / cols)
    sheet = Image.new("RGB", (cols * (tw + 6) + 6, rows * (th + 28) + 6), (20, 20, 20))
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
    dr = ImageDraw.Draw(sheet)
    for k, (i, f) in enumerate(picks):
        x, y = 6 + (k % cols) * (tw + 6), 6 + (k // cols) * (th + 28)
        sheet.paste(Image.open(f).resize((tw, th), Image.LANCZOS), (x, y + 22))
        dr.text((x + 2, y + 2), f"{i / fps:5.1f}s", fill=(0, 236, 155), font=font)
    sheet.save(out, quality=88)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--only-frames", action="store_true")
    ap.add_argument("--preview", type=float, nargs="*")
    a = ap.parse_args()

    print("1. brand");    prep_brand()
    print("2. approval"); meta = asyncio.run(capture_approval())
    print("3. data");     run([sys.executable, os.path.join(HERE, "build_data.py")])
    data = json.load(open(os.path.join(HERE, "post2_data.json")))
    data["approval"]["meta"] = meta
    print("4. clip");     data["clip"]["n_frames"] = prep_clip(data)
    with open(os.path.join(HERE, "post2_data.js"), "w") as f:
        f.write("window.POST2_DATA = " + json.dumps(data, ensure_ascii=False) + ";\n")

    if a.preview is not None:
        asyncio.run(render_frames(a.fps, None, preview=a.preview or [1.0]))
        return
    base = a.out or ("post2_dryrun" if data["dryrun"] else "post2_final")
    frames_dir = os.path.join(HERE, "frames")
    print("5. frames");   tl = asyncio.run(render_frames(a.fps, frames_dir))
    if a.only_frames:
        return
    print("6. audio")
    bed = os.path.join(HERE, "audio_bed.wav")
    has = clip_has_audio(data)
    synth_audio(tl, bed, duck=[(c["at"], c["at"] + c["dur"]) for c in tl["clip"]] if has else (), vo=tl["vo"])
    audio = os.path.join(HERE, "audio.wav")
    if tl["vo"]:
        vo_wav = os.path.join(HERE, "audio_vo.wav")
        vo_track(tl, vo_wav)
        final_mix(data, tl, bed, vo_wav, audio)
    elif has:
        mix_clip_audio(data, tl, bed, audio)
    else:
        shutil.copy(bed, audio)
    print("7. encode")
    mp4 = os.path.join(HERE, base + ".mp4")
    run(["ffmpeg", "-v", "error", "-y", "-framerate", str(a.fps), "-i", os.path.join(frames_dir, "%05d.jpg"),
         "-i", audio, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-vf", "scale=in_range=pc:out_range=tv,format=yuv420p", "-color_range", "tv",
         "-r", str(a.fps), "-c:a", "aac", "-b:a", "192k", "-ar", str(SR), "-ac", "2", "-shortest",
         "-movflags", "+faststart", mp4])
    print("8. contact")
    contact = os.path.join(HERE, base + "_contact.jpg")
    contact_sheet(frames_dir, a.fps, contact)
    print(run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_name,width,height,r_frame_rate",
               "-of", "compact", mp4]))
    print("done:", mp4, contact, "| DRY RUN" if data["dryrun"] else "| FINAL")


if __name__ == "__main__":
    main()
