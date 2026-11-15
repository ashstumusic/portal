"""One-word identifiers for songs.

Every song has one KEY: a single word, unique across the catalogue, that
finds it. "cloud" is The Cloud for the Desert:
  - ashstu.art/cloud opens the song's page
  - typing "cloud" (or "ash stu cloud") in the site's search puts it first
  - the word is on the song's page and in its structured data

Any other word that appears in only one song title ("desert", "dirge") also
finds that song in the site's search; the KEY is the one with a short link.

To change a song's word, edit KEYS below (title -> word) and rebuild. A new
song with no entry gets the first distinctive word of its title. The build
stops if two songs would share a word or a word clashes with a site folder.
"""
import os
import re
import unicodedata

KEYS = {
    'Still Sad': 'sad',
    'Worship Song': 'worship',
    'You Are What You Love': 'love',
    'Somewhere, Sometime': 'somewhere',
    'The Cloud for the Desert': 'cloud',
    'Pretty, May You Please': 'pretty',
    'Is This Limerence?': 'limerence',
    'St. James Infirmary': 'infirmary',
    'The Maid Freed From the Gallows': 'gallows',
    'Lucky to Grieve': 'lucky',
    "Cool Cat Can't Comprehend": 'cat',
    'Dirge for Ducklings': 'ducklings',
    'Savior Complicated': 'savior',
    'Annabel Lena': 'annabel',
    'Summertime Even on the Moon': 'moon',
    'Performatives Anonymous': 'anonymous',
    'Theory of Hope': 'hope',
    'Peacekeepers': 'peacekeepers',
    'The Wandering Jerk': 'jerk',
    'The Cosmos Is Alive': 'cosmos',
    'There Used To Be a Brighter Boy': 'brighter',
    'Drive Me Home': 'drive',
    'Who Stuns the Birds': 'birds',
    'The Helpful Raven': 'raven',
    'VCR': 'vcr',
    'Waste My Time': 'waste',
    'Pretend': 'pretend',
    'Relapse Sonnet': 'sonnet',
    'Pick Up the Phone': 'phone',
    'Why Have Eyes': 'eyes',
    'Unanswerable Questions': 'questions',
    'A Grief Preserved': 'grief',
    'Future Lives': 'future',
    "Don't Wish Your Life Away": 'wish',
    'Anybody Still Awake?': 'awake',
}

STOP = set('a an and are as at be by even for from have i is it me my of on or so that the there this to up used was what who why you your'.split())
# words the site's search already uses for kinds of things and sections
RESERVED = set('ash stu vol song songs music track tracks play audio album albums video videos lyric lyrics words home press kit contact about section setting settings'.split())
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def words_of(title):
    t = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode().lower()
    t = re.sub(r"['’]", '', t)
    return [w for w in re.findall(r'[a-z0-9]+', t)]


def assign(titles):
    """titles (in catalogue order) -> ({title: key}, {word: title}).
    The second map holds every word that points at exactly one song."""
    all_words = {t: words_of(t) for t in titles}
    count = {}
    for t, ws in all_words.items():
        for w in set(ws):
            count[w] = count.get(w, 0) + 1
    keys, taken = {}, {}
    for t in titles:
        k = KEYS.get(t)
        if not k:
            cands = [w for w in all_words[t] if w not in STOP and w not in RESERVED and len(w) > 2 and count[w] == 1]
            cands = [w for w in cands if w not in KEYS.values()] or all_words[t]
            k = cands[0]
        if k in taken:
            raise SystemExit(f'song_keys: "{k}" is used by both "{taken[k]}" and "{t}". Give one of them another word in scripts/song_keys.py.')
        if k in RESERVED or os.path.exists(os.path.join(ROOT, k)) and not os.path.isfile(os.path.join(ROOT, k, '.song-key')):
            raise SystemExit(f'song_keys: "{k}" (for "{t}") clashes with a site word or folder. Choose another in scripts/song_keys.py.')
        taken[k] = t
        keys[t] = k
    lookup = {k: t for t, k in keys.items()}
    for t, ws in all_words.items():
        for w in ws:
            if count[w] == 1 and w not in STOP and w not in RESERVED and len(w) > 2 and w not in lookup:
                lookup[w] = t
    return keys, lookup
