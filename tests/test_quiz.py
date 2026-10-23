#!/usr/bin/env python3
"""test_quiz.py — suita de testare funcțională pentru quiz-uri single-file TekiDeki.
Folosire: python3 test_quiz.py [cale/către/index.html]
Cerințe: playwright + chromium (pip install playwright && python3 -m playwright install chromium)
Ieșire: „TOATE TESTELE AU TRECUT" + exit 0, sau prima eroare + exit 1.
v4: + legătura Home spre hub (href ../ + eticheta tradusă în 4 limbi).
v5: generică pentru ORICE quiz - titlurile h1 se citesc din L (fără hardcodare),
    theme-color se validează ca hex + schimbare la comutarea temei (paletă liberă).
"""
import os
import re
import sys
from playwright.sync_api import sync_playwright

QUIZ = sys.argv[1] if len(sys.argv) > 1 else "index.html"
URL = "file://" + os.path.abspath(QUIZ)

errors = []
def check(cond, msg):
    if not cond:
        raise AssertionError("EȘEC: " + msg)
    print("  ✓", msg)

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 390, "height": 844})  # mobil
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(400)

    print("[1] Limbi")
    check(pg.get_attribute(".homelink", "href") == "../", "legătura Home duce la hub (../)")
    for lang, home in [("en", "Home"), ("ro", "Acasă"),
                     ("sr-cyrl", "Почетна"), ("sr-latn", "Početna")]:
        pg.click(f'.langbtn[data-lang="{lang}"]'); pg.wait_for_timeout(120)
        h1 = pg.evaluate("L[lang].h1")
        check(len(h1) > 3, f"L[{lang}].h1 definit")
        check(h1 in pg.text_content("h1"), f"h1 tradus ({lang})")
        check(pg.text_content(".homelink span").strip() == home, f"eticheta Home tradusă ({lang})")

    print("[2] Temă")
    th0 = pg.evaluate("document.documentElement.getAttribute('data-theme')")
    tc0 = pg.evaluate("document.querySelector('meta[name=theme-color]').content")
    pg.click("#themebtn"); pg.wait_for_timeout(120)
    th = pg.evaluate("document.documentElement.getAttribute('data-theme')")
    check(th in ("light", "dark") and th != th0, "tema comutată")
    tc = pg.evaluate("document.querySelector('meta[name=theme-color]').content")
    check(re.match(r"^#[0-9a-fA-F]{6}$", tc), "theme-color este hex valid")
    check(tc != tc0, "theme-color sincronizat cu noua temă")
    pg.reload(); pg.wait_for_timeout(300)
    check(pg.evaluate("document.documentElement.getAttribute('data-theme')") == th, "tema persistă după reload")

    print("[3] Rundă completă 15/15")
    pg.click("#startbtn"); pg.wait_for_timeout(150)
    for i in range(15):
        pg.wait_for_selector(".opt:not(:disabled)", timeout=3000)
        idx = pg.evaluate("""() => {
            const q = Q[order[qi]];
            return [...document.querySelectorAll('.opt')].findIndex(b => +b.dataset.oi === q.c);
        }"""
        )
        pg.click(f".opt >> nth={idx}"); pg.wait_for_timeout(90)
        check(pg.evaluate("locked"), f"q{i+1} blocat după răspuns")
        check(pg.evaluate("[...document.querySelectorAll('.opt .mark')].some(m => m.textContent === '\\u2713')"),
              f"q{i+1} marca ✓ prezentă")
        pg.click("#nextbtn"); pg.wait_for_timeout(110)
    pg.wait_for_selector("#scorebig", timeout=3000)
    check(pg.text_content("#scorebig") == "15/15", "scor 15/15")

    print("[4] Board + share")
    check(pg.evaluate("document.querySelectorAll('#board tr').length >= 1"), "leaderboard populat")
    pg.click("#sharebtn"); pg.wait_for_timeout(350)
    check(len(pg.text_content("#sharemsg")) > 3, "mesaj share afișat")

    print("[5] Răspuns greșit")
    pg.click("#againbtn"); pg.wait_for_timeout(150)
    pg.wait_for_selector(".opt:not(:disabled)")
    idx = pg.evaluate("""() => {
        const q = Q[order[qi]];
        return ([...document.querySelectorAll('.opt')].findIndex(b => +b.dataset.oi === q.c) + 1) % 3;
    }"""
    )
    pg.click(f".opt >> nth={idx}"); pg.wait_for_timeout(120)
    check(len(pg.text_content("#verdict")) > 3, "verdict afișat")
    src = pg.evaluate("document.getElementById('srcline').textContent")
    check(any(k in src for k in ["Source:", "Sursă", "Извор", "Izvor"]), "sursa afișată")
    check(pg.evaluate("[...document.querySelectorAll('.opt .mark')].some(m => m.textContent === '\\u2717')"),
          "marca ✗ prezentă")
    check(pg.evaluate("[...document.querySelectorAll('.opt .note')].filter(n => getComputedStyle(n).display !== 'none' && n.textContent).length >= 2"),
          "explicațiile opțiunilor vizibile")

    pg.click("#quitbtn"); pg.wait_for_timeout(110)
    check(pg.evaluate("document.getElementById('home').classList.contains('on')"), "quit → acasă")

    print("[6] Taste + navigare")
    pg.click("#startbtn"); pg.wait_for_timeout(150)
    pg.wait_for_selector(".opt:not(:disabled)")
    pg.keyboard.press("2"); pg.wait_for_timeout(90)
    check(pg.evaluate("locked"), "tasta 2 răspunde")
    pg.keyboard.press("Enter"); pg.wait_for_timeout(110)
    check(pg.evaluate("!locked"), "Enter înaintează")
    pg.click("#quitbtn"); pg.wait_for_timeout(110)
    check(pg.evaluate("document.getElementById('home').classList.contains('on')"), "quit → acasă (din quiz)")

    print("[7] Layout")
    for w, h, label in [(360, 740, "360px"), (390, 844, "390px"), (768, 1024, "768px"), (1366, 900, "1366px")]:
        pg2 = b.new_context(viewport={"width": w, "height": h}).new_page()
        pg2.goto(URL); pg2.wait_for_timeout(200)
        ovf = pg2.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        check(ovf == 0, f"fără overflow orizontal ({label})")
        pg2.close()
    tap = pg.evaluate("Math.min(...[...document.querySelectorAll('.opt,.cta,.langbtn,.iconbtn')].filter(e => e.offsetParent).map(e => e.getBoundingClientRect().height))")
    check(tap >= 34, f"ținte de tap ≥34px (min: {tap:.0f}px)")

    b.close()

if errors:
    print("\nERORI DE CONSOLĂ:"); [print("  -", e) for e in errors]; sys.exit(1)
print("\nTOATE TESTELE AU TRECUT — zero erori de consolă")
