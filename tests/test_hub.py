#!/usr/bin/env python3
"""test_hub.py — suita de testare funcțională pentru hub-ul quiz.freehtml.dev.
Folosire: python3 test_hub.py [cale/hub/index.html] [cale/quiz/index.html]
Cerințe: playwright + chromium (pip install playwright && python3 -m playwright install chromium)
Ieșire: „TOATE TESTELE AU TRECUT" + exit 0, sau prima eroare + exit 1.
v2: + geometrie card (titlu/descriere/meta stivuite vertical, săgeata la dreapta) —
    prinde regresia „Testul vedetelorCincisprezece" (spans inline lipite).
v3: două carduri în listă (Celebrity + AI) - verifică al doilea card (href, titlu tradus).
"""
import os
import sys
from playwright.sync_api import sync_playwright

HUB = sys.argv[1] if len(sys.argv) > 1 else "index.html"
QUIZ = sys.argv[2] if len(sys.argv) > 2 else "celebrity-iq-test/index.html"
HUB_URL = "file://" + os.path.abspath(HUB)
QUIZ_URL = "file://" + os.path.abspath(QUIZ)

errors = []
def check(cond, msg):
    if not cond:
        raise AssertionError("EȘEC: " + msg)
    print("  ✓", msg)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 390, "height": 844})  # mobil
    pg = ctx.new_page()
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(HUB_URL); pg.wait_for_timeout(400)

    print("[1] Limbi")
    for lang, h1, card in [("en", "Free quizzes, checked answers", "Celebrity IQ Test"),
                           ("ro", "Quiz-uri gratuite, răspunsuri verificate", "Testul vedetelor"),
                           ("sr-cyrl", "Бесплатни квизови, проверени одговори", "Квиз о славнима"),
                           ("sr-latn", "Besplatni kvizovi, provereni odgovori", "Kviz o slavnima")]:
        pg.click(f'.langbtn[data-lang="{lang}"]'); pg.wait_for_timeout(120)
        check(h1 in pg.text_content("h1"), f"h1 tradus ({lang})")
        check(card in pg.text_content(".qtitle"), f"titlu card tradus ({lang})")
        c2 = pg.evaluate(f"L['{lang}'].cards.q2t")
        check(len(c2) > 3 and c2 in pg.evaluate("document.querySelectorAll('.qtitle')[1].textContent"),
              f"titlu card 2 tradus ({lang})")
        check(pg.text_content(".kicker").strip() == "quiz.freehtml.dev", f"kicker static ({lang})")
        check(pg.evaluate(f"L['{lang}'].cards.q1d.length > 30"), f"descriere card prezentă ({lang})")

    print("[2] Temă")
    pg.click("#themebtn"); pg.wait_for_timeout(120)
    th = pg.evaluate("document.documentElement.getAttribute('data-theme')")
    check(th in ("light", "dark"), "tema comutată")
    tc = pg.evaluate("document.querySelector('meta[name=theme-color]').content")
    check(tc == ("#131020" if th == "dark" else "#f6f3ec"), "theme-color sincronizat")
    pg.reload(); pg.wait_for_timeout(300)
    check(pg.evaluate("document.documentElement.getAttribute('data-theme')") == th, "tema persistă după reload")

    print("[3] Carduri quiz")
    check(pg.get_attribute(".qcard", "href") == "./celebrity-iq-test/", "card 1 leagă spre ./celebrity-iq-test/")
    check(pg.evaluate("document.querySelectorAll('#cards .qcard').length == 2"), "două carduri în listă")
    check(pg.evaluate("document.querySelectorAll('.qcard')[1].getAttribute('href')") == "./ai-iq-test/",
          "card 2 leagă spre ./ai-iq-test/")
    pills = pg.text_content(".qmeta")
    check("15" in pills and "3" in pills and "4" in pills, "meta card: 15 / ≈3 min / 4")
    geo = pg.evaluate("""() => {
        const r = s => document.querySelector(s).getBoundingClientRect();
        return {tTop: r('.qtitle').top, tBottom: r('.qtitle').bottom,
                dTop: r('.qdesc').top, dBottom: r('.qdesc').bottom,
                mTop: r('.qmeta').top, bRight: r('.qb').right, gLeft: r('.qgo').left};
    }""")
    check(geo["dTop"] >= geo["tBottom"] - 2, "descrierea sub titlu (stivuite, nu lipite inline)")
    check(geo["mTop"] >= geo["dBottom"] - 2, "pills sub descriere")
    check(geo["gLeft"] >= geo["bRight"] - 2, "săgeata la dreapta conținutului")

    print("[4] Partajare limbă/temă cu quiz-ul (cheie ciq-)")
    pg.click('.langbtn[data-lang="ro"]'); pg.wait_for_timeout(120)
    check(pg.evaluate("localStorage.getItem('ciq-lang')") == '"ro"', "hub scrie ciq-lang în formatul quiz-ului (JSON)")
    pg.goto(QUIZ_URL); pg.wait_for_timeout(400)
    check(pg.evaluate("lang") == "ro", "quiz-ul preia limba RO aleasă pe hub")
    check(pg.evaluate("L['ro'].h1") in pg.text_content("h1"), "quiz-ul pornește direct în română (titlu din L)")
    pg.goto(HUB_URL); pg.wait_for_timeout(300)
    check("Quiz-uri gratuite" in pg.text_content("h1"), "hub rămâne în română la întoarcere")

    print("[5] Linkuri subsol")
    # R6: linkul de sprijin e EXACT https://paypal.me/TekiDeki (litera mica). Testul cerea
    # varianta cu P mare, adica exact ce a fost scos la tura 212 - de aceea pica dupa corectie.
    for href in ["https://paypal.me/TekiDeki", "https://github.com/TekiDeki", "https://freehtml.dev"]:
        a = pg.query_selector(f'footer a[href="{href}"]')
        check(a is not None, f"link subsol prezent: {href}")
        if a:
            check(a.get_attribute("target") == "_blank" and a.get_attribute("rel") == "noopener",
                  f"link extern sigur (target/rel): {href}")

    print("[6] Layout")
    for w, h, label in [(360, 740, "360px"), (390, 844, "390px"), (768, 1024, "768px"), (1366, 900, "1366px")]:
        pg2 = b.new_context(viewport={"width": w, "height": h}).new_page()
        pg2.goto(HUB_URL); pg2.wait_for_timeout(250)
        ovf = pg2.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        check(ovf == 0, f"fără overflow orizontal ({label})")
        pg2.close()
    tap = pg.evaluate("Math.min(...[...document.querySelectorAll('.qcard,.langbtn,.iconbtn')].filter(e => e.offsetParent).map(e => e.getBoundingClientRect().height))")
    check(tap >= 34, f"ținte de tap ≥34px (min: {tap:.0f}px)")

    b.close()

if errors:
    print("\nERORI DE CONSOLĂ:"); [print("  -", e) for e in errors]; sys.exit(1)
print("\nTOATE TESTELE AU TRECUT — zero erori de consolă")
