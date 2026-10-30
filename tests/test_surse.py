#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_surse.py - promisiunea din hub: „every fact with a source and the date it was checked”.

De ce exista testul: quiz-ul AI avea doua intrebari cu surse neclare („AI research - standard
terminology”, „OpenAI model documentation”) si nici o data pe intrebare, iar hubul promitea
sursa si data pentru fiecare fapt. Testul cere, pentru fiecare intrebare din fiecare quiz:
  - o sursa de cel putin 12 caractere, cu o referinta concreta (an, autor, publicatie sau domeniu);
  - o data a verificarii, fie pe intrebare (d), fie globala (CHECKED);
  - exact o varianta corecta si explicatie pentru fiecare varianta.

Se ruleaza din radacina repo-ului: python3 tests/test_surse.py
"""
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
ok = 0
rau = 0


def check(cond, mesaj):
    global ok, rau
    if cond:
        ok += 1
        print("  ok   " + mesaj)
    else:
        rau += 1
        print("  RAU  " + mesaj)


def extrage_q(fisier):
    s = fisier.read_text(encoding="utf-8")
    i = s.index("var Q=[")
    j = s.index("];", i) + 2
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(s[i:j] + "\nconsole.log(JSON.stringify(Q));")
        cale = f.name
    out = subprocess.run(["node", cale], capture_output=True, text=True)
    if out.returncode:
        raise SystemExit("node nu a putut evalua Q din %s: %s" % (fisier, out.stderr[:200]))
    return json.loads(out.stdout), s


# o sursa concreta: un an, un domeniu, sau o publicatie / institutie pe nume
CONCRET = re.compile(
    r"\d{4}"                                   # anul
    r"|\.(org|com|rs|edu|gov|net)\b"          # domeniu
    r"|et al\.|Press|Journal|University|Nobel"  # lucrare stiintifica
    r"|Britannica|Guinness|Records|Academy|Olympics|Studios|Productions|Institute|Center|Centre"
    r"|Reuters|AP-NORC|BBC|NASA|WWE|DeepMind|IBM|OpenAI|VirusTotal|Research",
    re.I)
# formulari generice care nu trimit nicaieri
GENERIC = re.compile(r"standard terminology|general knowledge|common knowledge|^documentation$|^research$", re.I)


def main():
    quizuri = sorted(p for p in ROOT.glob("*/index.html") if p.parent.name != "tests")
    check(len(quizuri) >= 2, "au fost gasite quiz-urile (%d)" % len(quizuri))
    for q in quizuri:
        Q, sursa_fisier = extrage_q(q)
        globala = re.search(r'var CHECKED="([\d.]+)"', sursa_fisier)
        check(len(Q) == 15, "%s: 15 intrebari (%d)" % (q.parent.name, len(Q)))
        fara_sursa, fara_data, surse_slabe, gresite = [], [], [], []
        for it in Q:
            s = (it.get("s") or "").strip()
            if len(s) < 12:
                fara_sursa.append(it["id"])
            elif not CONCRET.search(s) or GENERIC.search(s):
                surse_slabe.append("%s (%s)" % (it["id"], s))
            if not it.get("d") and not globala:
                fara_data.append(it["id"])
            if it.get("c") is None or not (0 <= it["c"] < len(it["o"])):
                gresite.append(it["id"])
        check(not fara_sursa, "%s: fiecare intrebare are sursa %s" % (q.parent.name, fara_sursa or ""))
        check(not surse_slabe, "%s: fiecare sursa e concreta %s" % (q.parent.name, surse_slabe or ""))
        check(not fara_data, "%s: fiecare fapt are data verificarii (pe intrebare sau global) %s" % (q.parent.name, fara_data or ""))
        check(not gresite, "%s: fiecare intrebare are exact o varianta corecta %s" % (q.parent.name, gresite or ""))
        fara_expl = [it["id"] for it in Q if any(not (o.get("w") or {}).get("en") for o in it["o"])]
        check(not fara_expl, "%s: fiecare varianta are explicatie %s" % (q.parent.name, fara_expl or ""))
    print("\n%d verificari trecute, %d esuate" % (ok, rau))
    return 0 if rau == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
