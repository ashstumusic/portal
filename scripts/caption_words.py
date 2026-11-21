#!/usr/bin/env python3
"""Word-by-word timing for the videos' sing-along captions (Video Files/Captions/<video>.words.json), used by the video
player's bouncing ball (kkTick in index-src.html).

How it is made (run by hand when a video or its captions change; needs torch, torchaudio, demucs, soundfile - not part of
the site's build):
  1. the video's sound:          ffmpeg -i "Video Files/<video>.mp4" -vn -ac 2 -ar 44100 wav/<video>.wav
  2. the voice alone (Demucs):   python -m demucs --two-stems=vocals -n htdemucs -o sep wav/*.wav
  3. this file:                  python scripts/caption_words.py "Video Files/Captions" sep "Video Files/Captions"
  4. onsets:                     python scripts/caption_words_refine.py sep "Video Files/Captions"
Each caption line's words are force-aligned (torchaudio MMS_FA, CTC forced alignment) against the isolated voice inside
that line's own window, so every word gets the moment it starts and ends (to a few hundredths of a second).
"""
import sys, os, re, json, unicodedata
import torch, torchaudio, soundfile as sf
import torchaudio.functional as AF
CAP, SEP, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
bundle = torchaudio.pipelines.MMS_FA
model = bundle.get_model(with_star=False).eval()
DICT = bundle.get_dict(star=None)
SR = bundle.sample_rate
def ts(t):
    h, m, s = t.split(':'); return int(h) * 3600 + int(m) * 60 + float(s)
def cues(path):
    txt = open(path, encoding='utf-8').read().replace('\r', '')
    out = []
    for blk in txt.split('\n\n'):
        m = re.search(r'(\d\d:\d\d:\d\d\.\d+)\s*-->\s*(\d\d:\d\d:\d\d\.\d+)[^\n]*\n(.+)', blk, re.S)
        if m: out.append((ts(m[1]), ts(m[2]), ' '.join(m[3].strip().split('\n'))))
    return out
def norm(w):
    w = unicodedata.normalize('NFKD', w).encode('ascii', 'ignore').decode().lower().replace('’', "'")
    return ''.join(c for c in w if DICT.get(c, 0) != 0)   # (index 0 is the blank)
def load(name):
    wav, sr = sf.read(os.path.join(SEP, 'htdemucs', name, 'vocals.wav'), dtype='float32', always_2d=True)
    wav = torch.from_numpy(wav.T).mean(0, keepdim=True)
    return AF.resample(wav, sr, SR)
for vtt in sorted(f for f in os.listdir(CAP) if f.endswith('.vtt')):
    name = vtt[:-4]
    if not os.path.exists(os.path.join(SEP, 'htdemucs', name, 'vocals.wav')): print('skip', name); continue
    voc = load(name); n = voc.shape[1]; lines = []
    cs = cues(os.path.join(CAP, vtt))
    for k, (a, b, text) in enumerate(cs):
        disp = text.split()
        toks = [norm(w) for w in disp]
        keep = [i for i, t in enumerate(toks) if t]
        if not keep: lines.append({'s': a, 'e': b, 'w': [[w, a, b] for w in disp]}); continue
        lo = max(a - 0.35, cs[k - 1][1] - 0.05 if k else 0); hi = min(b + 0.35, cs[k + 1][0] + 0.05 if k + 1 < len(cs) else n / SR)
        seg = voc[:, int(lo * SR):int(hi * SR)]
        with torch.inference_mode():
            em, _ = model(seg)
        em = torch.log_softmax(em, dim=-1)
        targets = torch.tensor([[DICT[c] for i in keep for c in toks[i]]], dtype=torch.int32)
        ali, scores = AF.forced_align(em, targets, blank=0)
        ali = ali[0]; scores = scores[0].exp()
        spans = AF.merge_tokens(ali, scores)
        ratio = seg.shape[1] / em.shape[1] / SR
        words = {}; p = 0
        for i in keep:
            L = len(toks[i]); sp = spans[p:p + L]; p += L
            words[i] = [lo + sp[0].start * ratio, lo + sp[-1].end * ratio, sum(s.score for s in sp) / L]
        # punctuation-only "words" ride with the word before (or after)
        out = []
        for i, w in enumerate(disp):
            if i in words: s, e, sc = words[i]
            else:
                j = max([x for x in keep if x < i] or [min(keep)]); s, e, sc = words[j][1], words[j][1], 0
            out.append([w, round(s, 3), round(e, 3), round(float(sc), 2)])
        lines.append({'s': round(out[0][1], 3), 'e': round(out[-1][2], 3), 'w': out})
    json.dump({'title': name, 'lines': lines}, open(os.path.join(OUT, name + '.words.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
    low = sum(1 for l in lines for w in l['w'] if w[3] < .3)
    print(name, len(lines), 'lines', sum(len(l['w']) for l in lines), 'words', low, 'low-confidence')
