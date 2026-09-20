# Livepeer agent recipes

These are AI media pieces made with the Livepeer agent (the Livepeer MCP), each packaged so anyone can reproduce it **exactly**.

Every piece has its own folder. Each folder is a Claude Code **skill**:
- a `SKILL.md` runbook listing the exact capabilities, inputs, settings, prompts, costs and QA checks,
- all the prompts and design references,
- the finished outputs,
- the scripts for sound and explainer videos,
- the real cost ledger.

## Recipes

| Recipe | What it is | Length | Cost | Skill triggers |
|---|---|---|---|---|
| [`freeze-frame/`](freeze-frame/) | A 15 s ultra-realistic single take: a woman snaps her fingers and a rainy, dystopian 1980s Times Square freezes. She sips a frozen stranger's coffee, snaps again, and the city resumes. Plus a 66 s narrated "full recipe" explainer. | 15 s + 66 s | $13.19 | "make the freeze-frame video", "time freeze snap video", "reproduce freeze frame" |
| [`desert-chase/`](desert-chase/) | Assets for a 20 s photoreal desert car chase blocked out in Blender and rendered with Seedance 2.5: the three character sheets (two cars, one location) and the exact v1 prompt. Assets only, not a full runbook yet. | 20 s | n/a | n/a |
`_shared/skills/` holds the generic skills the recipes build on. Install them too:
- [`seedance-video`](_shared/skills/seedance-video/): the five-block Seedance 2.5 "call sheet" prompt, the likeness-check workaround, timeouts and durable URLs.
- [`video-remake`](_shared/skills/video-remake/): the multi-agent production process, the one-page human sign-off, the cost ledger schema and the QA checklist.

## Requirements

- [Claude Code](https://claude.com/claude-code).
- **The Livepeer MCP connected** (`https://agent.livepeer.org/api/mcp`) with an active key and a spend cap that covers the recipe. All generation goes through it: no other media MCP servers.
- **ffmpeg** and ffprobe on your PATH, for sound mixing, mastering and encoding.
- **python3** with Pillow, plus **playwright** with Chromium for the explainer videos:
  ```
  pip install pillow playwright && playwright install chromium
  ```

## Install a recipe as a skill

A recipe folder is a skill folder. Symlink it (to stay up to date with the repo) or copy it into your skills directory:

```bash
git clone <this repo> ~/src/livepeer-agent-recipes
cd ~/src/livepeer-agent-recipes

# for all your projects
ln -s "$PWD/freeze-frame"                    ~/.claude/skills/freeze-frame
ln -s "$PWD/_shared/skills/seedance-video"   ~/.claude/skills/seedance-video
ln -s "$PWD/_shared/skills/video-remake"     ~/.claude/skills/video-remake

# or just for one project
mkdir -p .claude/skills && cp -R ~/src/livepeer-agent-recipes/freeze-frame .claude/skills/
```

Restart Claude Code and say one of the triggers (for example "make the freeze-frame video"). Claude loads the `SKILL.md` and runs it step by step, stopping at the human approval gates.

The scripts inside a recipe use paths relative to the recipe folder, so they run the same from the repo, a symlink or a copy.

## Add a new recipe

Keep every new project to this layout so it installs and runs like the others:

```
<recipe-name>/                 kebab-case; also the skill name
  SKILL.md       runbook with frontmatter: name: <recipe-name>, description with the trigger phrases.
                 Per step: exact capability, exact inputs/settings, prompt file path, expected cost, QA check.
                 Plus: the hard rules, the approval gates and the final cost breakdown.
  README.md      short human overview: what it is, final numbers, links to outputs/
  prompts/       every prompt verbatim; first line = "capability | source | settings | $" metadata
  refs/          locked design references (sheets, stills); JPG, 1600 px wide or less
  outputs/       the finished, published media
  explainer/     the "how it was made" renderer (template.html + render.py + build_data.py + vo/), if any
  sound/         mix/master scripts with relative or parameterised paths (no wavs; list SFX URLs instead)
  ledger/        cost_log*.jsonl, one line per paid call (schema: _shared/skills/video-remake/references/ledger-schema.md)
```

Rules for a new recipe:
- Every path is relative to the recipe folder. Never use absolute or scratch paths.
- Keep only **durable** asset URLs (`agent.livepeer.org/a/…` or public re-hosts). **Never commit credentials**: signed upload URLs, `authorization` headers, API keys or tokens. Before committing, run:
  ```
  grep -rniE "bearer|vercel_blob_client|api[_-]?key|secret|token|authorization|sk-[a-z0-9]" .
  ```
- Leave out third-party inputs (photos, reference videos). Tell users to bring their own.
- Public-facing docs and outputs stand alone. They never say the piece derives from another video.
- Don't commit frame dumps, intermediate wavs or base64 dumps (see `.gitignore`).
- Add a row to the recipe table above.
