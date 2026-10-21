#!/usr/bin/env python3
"""Write the review carousel into every page that should carry it.

Source of truth: tools/reviews/reviews.json. Run from the repo root:
    python3 tools/reviews/build.py

Each page gets three marked blocks, which this script replaces on every run:
  HTML   <!-- reviews:start --> ... <!-- reviews:end -->
  CSS    /* reviews-css:start */ ... /* reviews-css:end */   (inside the page <style>)
  JS     <!-- reviews-js:start --> ... <!-- reviews-js:end --> (before </body>)
Review schema lives on the homepage only and is rewritten from the same data.
"""
import glob
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.join(ROOT, "tools", "reviews")


def read(p):
    with open(os.path.join(HERE, p), encoding="utf-8") as f:
        return f.read().strip()


DATA = json.load(open(os.path.join(HERE, "reviews.json"), encoding="utf-8"))["reviews"]
CSS = read("reviews.css")
JS = read("reviews.js")
STARS = read("stars.html")

ARROWS = (
    '<div class="rv-nav">'
    '<button class="rv-btn" id="rv-prev" type="button" aria-label="Previous reviews" aria-controls="rv-rail">'
    '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M15 5l-8 7 8 7" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg></button>'
    '<button class="rv-btn" id="rv-next" type="button" aria-label="More reviews" aria-controls="rv-rail">'
    '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M9 5l8 7-8 7" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg></button>'
    "</div>"
)


def esc(t):
    return html.escape(t, quote=True)


def card(r):
    if r.get("face"):
        av = f'<img class="rv-face" src="/img/reviews/{r["face"]}" alt="" width="40" height="40" loading="lazy" decoding="async">'
    else:
        av = f'<span class="rv-initial" aria-hidden="true">{esc(r["initial"])}</span>'
    return (
        f'<article class="rv-card" tabindex="0">{STARS}<p class="rv-quote">{esc(r["text"])}</p>'
        f'<div class="rv-meta">{av}<span class="rv-who"><span class="rv-author">{esc(r["name"])}</span>'
        f'<span class="rv-sub">{r["label"]} / {r["source"]}</span></span></div></article>'
    )


def ordered(service):
    if not service:
        return DATA
    first = [r for r in DATA if service in r["tags"]]
    return first + [r for r in DATA if service not in r["tags"]]


def section(cls, service):
    cards = "".join(card(r) for r in ordered(service))
    return (
        f'<!-- reviews:start -->\n<section class="{cls}" id="reviews"><div class="wrap">'
        '<p class="eyebrow">Reviews</p><h2>What Connecticut homeowners say.</h2>'
        f'<div class="rv-head"><span class="rv-sub">Recent reviews from Facebook and Google</span>{ARROWS}</div>'
        '<div class="rv-rail" id="rv-rail" tabindex="0" role="region" aria-label="Customer reviews, scroll horizontally">'
        f'{cards}<div class="rv-clones" id="rv-clones" aria-hidden="true" style="display:contents"></div></div>'
        "</div></section>\n<!-- reviews:end -->"
    )


def service_for(rel):
    slug = rel.split("/")[0] if not rel.startswith("lp/") else rel.split("/")[1]
    for key, svc in (("house", "house"), ("roof", "roof"), ("gutter", "gutter"),
                     ("deck", "decks"), ("fence", "decks"), ("patio", "decks")):
        if slug.startswith(key):
            return svc
    return None


def strip_blocks(s):
    s = re.sub(r"<!-- reviews:start -->.*?<!-- reviews:end -->", "<!-- reviews:slot -->", s, flags=re.S)
    s = re.sub(r"\n/\* reviews-css:start \*/.*?/\* reviews-css:end \*/\n", "", s, flags=re.S)
    s = re.sub(r"<!-- reviews-js:start -->.*?<!-- reviews-js:end -->\n", "", s, flags=re.S)
    return s


def strip_legacy_home(s):
    """First run only: the homepage carried the carousel unmarked."""
    i = s.find('<section class="sec sec-shell" id="reviews">')
    if i >= 0:
        s = s[:i] + "<!-- reviews:slot -->" + s[s.index("</section>", i) + 10:]
    if "/* Review scroller." in s:
        a = s.index("/* Review scroller.")
        m = "@media (prefers-reduced-motion:reduce){.rv-rail{scroll-behavior:auto}}"
        s = s[:a] + s[s.index(m, a) + len(m):]
    k = s.find("var rail=document.getElementById('rv-rail')")
    if k >= 0:
        a = s.rindex("<script", 0, k)
        s = s[:a] + s[s.index("</script>", k) + 9:]
    return s


def prev_is_shell(s, pos):
    opens = re.findall(r'<section class="([^"]*)"', s[:pos])
    return bool(opens) and "sec-shell" in opens[-1].split()


def place(s):
    """Where the carousel goes: the old homepage slot, else before the closing
    quote band, else after the last section on the page."""
    if "<!-- reviews:slot -->" in s:
        return s.index("<!-- reviews:slot -->"), len("<!-- reviews:slot -->")
    m = re.search(r'<section class="sec cta"', s)
    if m:
        return m.start(), 0
    end = s.rindex("</section>", 0, s.index("<footer")) + len("</section>")
    return end, 0


def schema(s):
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', s, re.S)
    d = json.loads(m.group(1))
    for node in d["@graph"]:
        if "review" in node:
            node["review"] = [
                {"@type": "Review", "author": {"@type": "Person", "name": r["name"]},
                 "datePublished": r["date"],
                 "reviewRating": {"@type": "Rating", "ratingValue": 5, "bestRating": 5, "worstRating": 1},
                 "reviewBody": r["text"]}
                for r in DATA if r["full"]
            ]
    return s[:m.start(1)] + "\n" + json.dumps(d, indent=2) + "\n" + s[m.end(1):]


def targets():
    pages = ["index.html", "about/index.html", "contact/index.html", "faq/index.html",
             "house-washing/index.html", "roof-washing/index.html",
             "gutter-cleaning/index.html", "decks-fences-patios/index.html"]
    pages += sorted(glob.glob("pressure-washing-*-ct/index.html", root_dir=ROOT))
    pages += sorted(glob.glob("lp/*/index.html", root_dir=ROOT))
    return pages


def build():
    n = 0
    for rel in targets():
        p = os.path.join(ROOT, rel)
        s = open(p, encoding="utf-8").read()
        s = strip_blocks(s)
        if rel == "index.html":
            s = strip_legacy_home(s)
        pos, cut = place(s)
        cls = "sec" if prev_is_shell(s, pos) else "sec sec-shell"
        s = s[:pos] + section(cls, service_for(rel)) + s[pos + cut:]
        s = s.replace("</style>", f"\n/* reviews-css:start */\n{CSS}\n/* reviews-css:end */\n</style>", 1)
        s = s.replace("</body>", f"<!-- reviews-js:start -->\n{JS}\n<!-- reviews-js:end -->\n</body>", 1)
        if rel == "index.html":
            s = schema(s)
        open(p, "w", encoding="utf-8").write(s)
        n += 1
    print(f"reviews: {len(DATA)} reviews written to {n} pages")


if __name__ == "__main__":
    build()
