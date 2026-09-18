"""Append one ledger line per paid inworld-tts call (skips idempotency keys already logged).

Reads lines.json (`lines[]` with `idem` + `cost`, and `tests[]` for voice tests / superseded takes)
and appends them to the recipe ledger, so build_data.py counts narration in the on-screen total.
Set SESSION to your own session_id when you re-run the recipe.
"""
import json
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.normpath(os.path.join(HERE, '..', '..', 'ledger', 'cost_log_post1.jsonl'))
SESSION = 'post1-freeze-ae42c851-10af-46ca-abd3-c68ab52bef9b'
d = json.load(open(os.path.join(HERE, 'lines.json')))
logged = set()
for raw in open(LEDGER):
    raw = raw.strip()
    if raw:
        logged.add(json.loads(raw).get('idempotency_key'))
rows = [(f"Narration line '{l['key']}': \"{l['text']}\"", l) for l in d['lines'] if l.get('idem')] + \
       [(f"Narration voice test / {t['text']}", t) for t in d['tests']]
with open(LEDGER, 'a') as f:
    for step, l in rows:
        if l['idem'] in logged:
            continue
        f.write(json.dumps(dict(
            ts=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), phase='P6-narration', session_id=SESSION,
            step=step, capability='inworld-tts', model_id='fal-ai/inworld-tts', job_id=None,
            idempotency_key=l['idem'], inputs=f"voice={d['voice']}", cost_usd=l['cost'], status='done',
            local_path=f"explainer/vo/raw/{l.get('key', 'test')}.wav" if l.get('key') else None)) + '\n')
        print('logged', l['idem'], l['cost'])
