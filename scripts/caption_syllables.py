#!/usr/bin/env python3
"""Syllable timing for the sing-along ball (owner's request: the ball should bounce on every syllable, the way the old
follow-the-bouncing-ball sing-alongs did).

Third step after scripts/caption_words.py and scripts/caption_words_refine.py. Each sung word of more than one
syllable is split (Pyphen's English hyphenation, which follows syllable breaks), and the start of each syllable after
the first is found in the isolated vocals: within the word, the voice's onsets (librosa's onset strength) are looked
for near where each syllable would start if the word's length were shared out by letters; the strongest onset near
that point is taken, or that point itself where the voice glides on without a fresh attack. The result is written
onto the word as a fifth item: [[syllable, start], ...] (the first syllable starts with the word).

  python3 scripts/caption_syllables.py <demucs output folder, holding htdemucs/<video>/vocals.wav> "Video Files/Captions"

Needs librosa, soundfile and pyphen (not part of the site's build).
"""
import json, os, re, sys
import numpy as np, soundfile as sf, librosa, pyphen

SEP, D = sys.argv[1], sys.argv[2]
HY = pyphen.Pyphen(lang='en_US', left=1, right=2)
HOP = 0.005

def syllables(word):
    """The word as sung syllables, keeping its punctuation on the outer pieces ('shoulder,' -> ['shoul', 'der,'])."""
    m = re.match(r"^([^A-Za-z']*)([A-Za-z'’-]+)([^A-Za-z']*)$", word)
    if not m: return [word]
    pre, core, post = m.groups()
    parts = [p for p in HY.inserted(core.lower()).split('-') if p]
    # a piece with no vowel sound is no syllable: it joins its neighbour ("s-mil-ing" -> "smil-ing")
    k = 0
    while k < len(parts) and len(parts) > 1:
        if not re.search(r'[aeiouy]', parts[k]):
            if k + 1 < len(parts): parts[k + 1] = parts[k] + parts[k + 1]
            else: parts[k - 1] += parts[k]
            parts.pop(k)
        else: k += 1
    if len(parts) < 2: return [word]
    # back to the word's own letters (its capitals)
    out, i = [], 0
    for p in parts: out.append(core[i:i + len(p)]); i += len(p)
    parts = out
    parts[0] = pre + parts[0]; parts[-1] = parts[-1] + post
    return parts

for f in sorted(x for x in os.listdir(D) if x.endswith('.words.json')):
    path = os.path.join(D, f); d = json.load(open(path)); name = d['title']
    y, sr = sf.read(os.path.join(SEP, 'htdemucs', name, 'vocals.wav'), always_2d=True); y = y.mean(1).astype(np.float32)
    hop = int(sr * HOP)
    env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop, aggregate=np.median)
    env = env / (np.percentile(env, 99) + 1e-9)
    # loudness (dB, 5 ms steps, lightly smoothed): the consonant between two sung vowels is a dip in it
    n = len(y) // hop
    db = 10 * np.log10(np.add.reduceat(y[:n * hop] ** 2, np.arange(0, n * hop, hop)) / hop + 1e-10)
    db = np.convolve(db, np.ones(5) / 5, 'same')
    split = found = 0
    for line in d['lines']:
        for w in line['w']:
            if len(w) > 4: w[:] = w[:4]   # (rerun: drop the old syllables)
            parts = syllables(w[0])
            if len(parts) < 2: continue
            t0, t1 = w[1], max(w[2], w[1] + 0.12 * len(parts))
            dur = t1 - t0
            letters = [max(1, len(re.sub(r"[^A-Za-z]", '', p))) for p in parts]
            cum = np.cumsum([0] + letters[:-1]) / sum(letters)
            times = [t0]
            for k in range(1, len(parts)):
                guess = t0 + dur * cum[k]
                win = dur / len(parts) * 0.45
                lo = max(times[-1] + 0.07, guess - win); hi = min(t1 - 0.05, guess + win)
                best = guess
                if hi > lo:
                    a, b = int(lo / HOP), int(hi / HOP) + 1
                    dseg = db[a:b]
                    # first choice: the deepest dip in loudness between the syllables (at least 4 dB under the louder
                    # sound either side of it) - the syllable starts as the voice comes up out of it
                    if len(dseg) > 4:
                        j = int(np.argmin(dseg)); m = a + j
                        left = db[max(int(t0 / HOP), m - 40):m + 1].max(); right = db[m:min(int(t1 / HOP) + 1, m + 40)].max()
                        if 0 < j < len(dseg) - 1 and min(left, right) - db[m] >= 4:
                            best = m * HOP; found += 1
                            a = b   # (done: skip the onset search)
                    seg = env[a:b]
                    if len(seg) and best == guess:
                        j = int(np.argmax(seg))
                        if seg[j] > 0.25 and 0 < j < len(seg) - 1:   # else: a fresh attack in the voice
                            best = (a + j) * HOP; found += 1
                best = max(best, times[-1] + 0.07)
                times.append(round(float(best), 3))
            w.append([[p, t] for p, t in zip(parts, times)])
            split += 1
    json.dump(d, open(path, 'w'), ensure_ascii=False, separators=(',', ':'))
    n = sum(len(l['w']) for l in d['lines'])
    print(f'{name}: {n} words, {split} split into syllables, {found} syllable starts found in the voice')
