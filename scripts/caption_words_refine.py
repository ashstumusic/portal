#!/usr/bin/env python3
# Second step after scripts/caption_words.py: python scripts/caption_words_refine.py sep "Video Files/Captions"
"""Onset refinement: forced alignment tends to mark a word a little after its first sound. Where a word follows a pause
(the voice was quiet just before), its start is moved back to the moment the voice actually rises (within 180 ms)."""
import sys, os, json, numpy as np, soundfile as sf
SEP, D = sys.argv[1], sys.argv[2]
for f in sorted(x for x in os.listdir(D) if x.endswith('.words.json')):
    d = json.load(open(os.path.join(D, f))); name = d['title']
    y, sr = sf.read(os.path.join(SEP, 'htdemucs', name, 'vocals.wav'), always_2d=True); y = y.mean(1)
    hop = int(sr * .005); n = len(y) // hop
    db = 10 * np.log10(np.add.reduceat(y[:n * hop] ** 2, np.arange(0, n * hop, hop)) / hop + 1e-10)
    db = np.convolve(db, np.ones(3) / 3, 'same'); peak = np.percentile(db, 99); quiet = peak - 38; loud = peak - 26
    moved = 0; prev_end = -1
    for l in d['lines']:
        for w in l['w']:
            i = int(w[1] / .005); lo = max(0, i - 36)
            seg = db[lo:i + 1]
            if len(seg) < 3: continue
            # a pause just before? find the last quiet frame before the word, then the first frame after it that is loud
            q = np.where(seg < quiet)[0]
            if len(q):
                j = lo + q[-1]
                r = np.where(db[j:i + 1] > loud)[0]
                if len(r):
                    k = j + r[0]
                    # walk back to where the rise began (still above the quiet floor)
                    while k > j and db[k - 1] > quiet + 3: k -= 1
                    nt = round(k * .005, 3)
                    if nt < w[1] - .015 and nt > prev_end: w[1] = nt; moved += 1
            prev_end = w[1]
        l['s'] = l['w'][0][1]
    json.dump(d, open(os.path.join(D, f), 'w'), ensure_ascii=False, separators=(',', ':'))
    print(name, 'moved', moved, 'of', sum(len(l['w']) for l in d['lines']))
