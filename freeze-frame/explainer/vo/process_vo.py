"""Fetch + trim the narration lines for the explainer.

For every line in lines.json that has a `url` (the durable inworld-tts output):
  1. download it to raw/<key>.wav if it is not there yet,
  2. cut edge silence, shorten internal pauses to <=0.12 s, speed up with atempo (1.15),
  3. write proc/<key>.wav (48 kHz mono) and store the new `dur` / `wps` back into lines.json.

Run from anywhere:  python3 freeze-frame/explainer/vo/process_vo.py
New lines: generate them with inworld-tts (voice "Dennis (en)"), put the returned durable URL in
`url`, then run this. build_data.py only picks up lines that have a proc/ wav and a `dur`.
"""
import json
import os
import subprocess
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LINES = os.path.join(HERE, 'lines.json')
d = json.load(open(LINES))
AF = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.02:"
      "stop_periods=-1:stop_duration=0.08:stop_threshold=-34dB:stop_silence=0.06,"
      "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.06,areverse,"
      f"atempo={d['atempo']}")
os.makedirs(os.path.join(HERE, 'raw'), exist_ok=True)
os.makedirs(os.path.join(HERE, 'proc'), exist_ok=True)
for l in d['lines']:
    if not l.get('url'):
        continue
    raw, out = os.path.join(HERE, 'raw', f"{l['key']}.wav"), os.path.join(HERE, 'proc', f"{l['key']}.wav")
    if not os.path.exists(raw):
        urllib.request.urlretrieve(l['url'], raw)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', raw, '-af', AF, '-ar', '48000', '-ac', '1', out], check=True)
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', out],
                               capture_output=True, text=True).stdout)
    l['dur'] = round(dur, 3); l['wps'] = round(len(l['text'].split()) / dur, 2)
    print(f"{l['key']:<15}{dur:5.2f}s {l['wps']:4.1f}wps  {l['text']}")
json.dump(d, open(LINES, 'w'), indent=1)
print('sum', round(sum((l.get('dur') or 0) for l in d['lines']), 2))
