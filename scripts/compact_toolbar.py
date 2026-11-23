"""The phone toolbar on tablets and narrow windows (owner's request, 2026-11-23:
"make an ipad have the mobile menu. anything that looks like this should not be allowed").

Between 768px and 1279px wide the full toolbar (Home, four streaming logos, four
section buttons, Search, Settings) only fits by shrinking every button and dropping
the name, and on a touch screen it is a row of small targets. So those widths, and
every touch-only screen at any width (all iPads, including a 12.9" iPad Pro on its
side), get the phone toolbar instead: Home, the name, and Menu, with the phone menu
(Home, Listen on, the sections, Search, Settings folded).

Rather than copy the phone toolbar's CSS by hand (copies drift), the build rewrites
the media queries of the toolbar's own rules, in place, so the cascade is the very
one phones get:
  - a toolbar or menu rule written for phones, `@media (max-width: 767px)`, also
    applies on COMPACT_BAR screens;
  - a toolbar or menu rule written for 768px and up (which phones never see, so the
    phone rules never had to undo it) applies only to the full toolbar, WIDE_BAR.
Everything else (the page content) keeps its media queries: tablets keep their own
layout of the page. shared/kinetic.js uses the same condition (PHONE_BAR) to draw the
phone version of the menu.
"""
import re

# keep in step with PHONE_BAR in shared/kinetic.js (which also covers phones themselves)
COMPACT_BAR = ["(min-width: 768px) and (max-width: 1279px)",
               "(min-width: 768px) and (hover: none) and (pointer: coarse)"]
# the full toolbar: 1280px and up, with a pointer that can hover
WIDE_BAR = ["(min-width: 1280px) and (hover: hover)", "(min-width: 1280px) and (pointer: fine)"]
PHONE = '(max-width: 767px)'
TOOLBAR = re.compile(r'\.nav\b|\.nav-|#nav-|\.k-si--bar|\.k-si--flow|\.k-tools|\.k-menu|\.k-search-btn|'
                     r'\.k-settings-btn|\.settings-(?:title|fold|chev)|\.k-palette\[data-mode="menu"\]')


def _split_top(s, sep):
    """s split on sep outside brackets, parentheses and quotes"""
    out, depth, q, cur = [], 0, None, []
    for c in s:
        if q:
            cur.append(c)
            if c == q: q = None
            continue
        if c in '"\'': q = c
        elif c in '([': depth += 1
        elif c in ')]': depth -= 1
        if c == sep and depth == 0:
            out.append(''.join(cur)); cur = []
        else:
            cur.append(c)
    out.append(''.join(cur))
    return out


def _block_end(css, b):
    """index just past the block whose '{' is at b (comments and strings skipped)"""
    d, k, n, q = 1, b + 1, len(css), None
    while d and k < n:
        c = css[k]
        if q:
            if c == '\\': k += 1
            elif c == q: q = None
        elif css.startswith('/*', k):
            k = css.find('*/', k) + 1
        elif c in '"\'': q = c
        elif c == '{': d += 1
        elif c == '}': d -= 1
        k += 1
    return k


def _items(body):
    """the top-level items of a block body as (prelude, whole text), comments dropped"""
    out, i, n = [], 0, len(body)
    while i < n:
        if body.startswith('/*', i): i = body.find('*/', i) + 2; continue
        b = body.find('{', i)
        if b < 0: break
        pre = re.sub(r'/\*.*?\*/', '', body[i:b], flags=re.S).strip()
        e = _block_end(body, b)
        out.append((pre, pre + ' {' + body[b + 1:e - 1] + '}'))
        i = e
    return out


def _is_bar(pre, text):
    if pre.startswith('@'):   # a nested @supports/@media: the toolbar's if any rule in it is
        return bool(TOOLBAR.search(re.sub(r'\{[^{}]*\}', '', text[text.find('{') + 1:])))
    return any(TOOLBAR.search(s) for s in _split_top(pre, ','))


def _queries(prelude):
    return [q.strip() for q in _split_top(prelude[len('@media'):], ',')]


def _retarget(qs):
    """the new query list for a block's toolbar rules (None: leave the block alone)"""
    if any(q in COMPACT_BAR for q in qs): return None   # written for the compact toolbar itself (system.css)
    phone = [q for q in qs if PHONE in q and 'min-width' not in q]
    if phone:
        extra = []
        for q in phone:
            rest = re.sub(r'^and\s+|\s+and$', '', q.replace(PHONE, '').strip()).strip()
            extra += [c + (' and ' + rest if rest else '') for c in COMPACT_BAR]
        return qs + extra
    mins = [max([int(x) for x in re.findall(r'min-width:\s*(\d+)px', q)] or [0]) for q in qs]
    if qs and min(mins) >= 768:
        return [f'{q} and {w}' for q in qs for w in WIDE_BAR]
    return None


def compact_toolbar(css):
    """the stylesheet with the phone toolbar given to tablets, touch screens and narrow windows"""
    out, i, n = [], 0, len(css)
    while i < n:
        a, m, b = css.find('/*', i), css.find('@media', i), css.find('{', i)
        if m < 0: break
        if 0 <= a < m and (b < 0 or a < b):   # a comment first: copy it over
            e = css.find('*/', a) + 2; out.append(css[i:e]); i = e; continue
        if b < m:                               # a rule or other at-rule first: copy it over
            e = _block_end(css, b); out.append(css[i:e]); i = e; continue
        b = css.find('{', m); e = _block_end(css, b)
        pre = css[m:b].strip(); qs = _queries(pre); new = _retarget(qs)
        items = _items(css[b + 1:e - 1]) if new else []
        if not any(_is_bar(p, t) for p, t in items):
            out.append(css[i:e]); i = e; continue
        out.append(css[i:m])
        # runs of toolbar / other rules, in their order, each run in its own block
        run, run_bar = [], None
        def flush():
            if run: out.append('@media ' + ', '.join(new if run_bar else qs) + ' {\n' + '\n'.join(run) + '\n}\n')
        for p, t in items:
            bar = _is_bar(p, t)
            if bar != run_bar: flush(); run, run_bar = [], bar
            run.append(t)
        flush()
        i = e
    out.append(css[i:])
    return ''.join(out)


if __name__ == '__main__':   # show what changes: python3 scripts/compact_toolbar.py styles.css shared/*.css
    import sys
    src = ''.join(open(f).read() + '\n' for f in sys.argv[1:])
    new = compact_toolbar(src)
    print(len(src), '->', len(new), 'characters;', new.count('1279px'), 'phone blocks extended,',
          new.count('(min-width: 1280px) and (hover: hover)'), 'wide-only queries')
