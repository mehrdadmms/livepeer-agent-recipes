import sys, json, librosa, numpy as np
path = sys.argv[1]; start = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
y, sr = librosa.load(path, sr=22050, offset=start, duration=20.0)
tempo, frames = librosa.beat.beat_track(y=y, sr=sr, units="frames")
times = librosa.frames_to_time(frames, sr=sr)
tempo = float(np.atleast_1d(tempo)[0])
# fit a straight grid to the detected beats so cuts stay locked to one tempo
n = np.arange(len(times)); A = np.vstack([n, np.ones_like(n)]).T
period, t0 = np.linalg.lstsq(A, times, rcond=None)[0]
while t0 - period > -0.02: t0 -= period          # earliest grid beat inside the window
t0 = max(t0, 0.0)
print(json.dumps({"bpm": round(60 / period, 2), "beat0": round(float(t0), 3), "librosa_bpm": round(tempo, 2),
                  "first_detected": [round(float(x), 3) for x in times[:6]]}))
