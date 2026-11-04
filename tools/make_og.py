"""Rebuild assets/og-image.png (the link preview card) from the hero in index.html.

Run after any edit to the hero eyebrow, title, lede or stats:
    python tools/make_og.py
It reads the hero text from index.html, renders a 1200x630 card with Chrome,
and bumps the ?v=N on the og:image and twitter:image tags so apps refetch it.
"""
import html
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
OUT = ROOT / "assets" / "og-image.png"

CSS = """
html, body { margin: 0; width: 1200px; height: 630px; overflow: hidden; }
body { background: #0f1115; color: #e6e8ee; font-family: "Segoe UI", system-ui, sans-serif; border-top: 6px solid #5b9bff; box-sizing: border-box; }
.wrap { display: grid; grid-template-columns: 1fr 430px; gap: 56px; align-items: center; height: 624px; padding: 0 64px; box-sizing: border-box; }
.eyebrow { display: inline-block; font-size: 18px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: #5b9bff; border: 1px solid #262b36; border-radius: 999px; padding: 6px 16px; }
.name { font-size: 28px; font-weight: 700; color: #9aa3b2; margin: 28px 0 0; }
h1 { font-size: 64px; line-height: 1.1; margin: 6px 0 16px; letter-spacing: -.01em; }
p { font-size: 24px; line-height: 1.5; color: #9aa3b2; margin: 0; }
.stats { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.stat { background: #171a21; border: 1px solid #262b36; border-radius: 14px; padding: 16px 18px; box-sizing: border-box; }
.stat b { display: block; font-size: 34px; line-height: 1.1; margin-bottom: 6px; }
.stat span { font-size: 16px; line-height: 1.3; color: #9aa3b2; display: block; }
"""


def text(fragment):
    """Strip tags and decode entities."""
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def hero_parts(page):
    hero = re.search(r'<header class="hero">(.*?)</header>', page, re.S).group(1)
    eyebrow = text(re.search(r'<span class="eyebrow">(.*?)</span>', hero, re.S).group(1))
    h1 = re.search(r"<h1>(.*?)</h1>", hero, re.S).group(1)
    title = text(re.sub(r'<span class="sr-only">.*?</span>', "", h1))
    lede = text(re.search(r'<p class="lede">(.*?)</p>', hero, re.S).group(1))
    stats = [(text(b), text(s)) for b, s in re.findall(
        r'<div class="stat"><b>(.*?)</b><span>(.*?)</span></div>', hero, re.S)]
    if len(stats) != 4:
        raise SystemExit(f"Expected 4 hero stats, found {len(stats)}")
    return eyebrow, title, lede, stats


def card_html(eyebrow, title, lede, stats):
    e = html.escape
    boxes = "".join(f'<div class="stat"><b>{e(b)}</b><span>{e(s)}</span></div>' for b, s in stats)
    return (f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>'
            f'<div class="wrap"><div><span class="eyebrow">{e(eyebrow)}</span>'
            f'<div class="name">Austin Lewis</div><h1>{e(title)}</h1><p>{e(lede)}</p></div>'
            f'<div class="stats">{boxes}</div></div></body></html>')


def main():
    page = INDEX.read_bytes().decode("utf-8")
    card = card_html(*hero_parts(page))

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        tab = browser.new_page(viewport={"width": 1200, "height": 630}, device_scale_factor=1)
        tab.set_content(card)
        tab.wait_for_timeout(200)
        overflow = tab.evaluate("document.querySelector('.wrap').scrollHeight > 624")
        tab.screenshot(path=str(OUT))
        browser.close()
    if overflow:
        raise SystemExit("Card content is taller than 630px. Shorten the hero text or the card CSS.")

    def bump(m):
        return f"og-image.png?v={int(m.group(1)) + 1}"
    new_page, count = re.subn(r"og-image\.png\?v=(\d+)", bump, page)
    INDEX.write_bytes(new_page.encode("utf-8"))
    print(f"{OUT} {OUT.stat().st_size} bytes, {count} image tags bumped")


if __name__ == "__main__":
    main()
