#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_sitemap.py - sitemap.xml si robots.txt ale quiz.freehtml.dev.

De ce exista testul: pana pe 31.10.2026 gazda quiz nu avea niciun sitemap.xml, iar
Search Console primea 404 la https://quiz.freehtml.dev/sitemap.xml. Fisierul nu era
rupt de deploy, pur si simplu nu exista. Testul strange legatura in ambele sensuri:
  - fiecare adresa din sitemap duce la o pagina care exista in repo;
  - fiecare pagina din repo apare in sitemap (ca sa nu uitam una la urmatorul quiz);
  - adresele au slash la final, pentru ca Pages da 307 de la /slug la /slug/;
  - lastmod e o data valida si nu vine din viitor;
  - robots.txt permite accesul si trimite exact la sitemap.

Se ruleaza din radacina repo-ului:
  python3 tests/test_sitemap.py            # local, fara retea
  python3 tests/test_sitemap.py --live     # cere 200 pe fiecare adresa publicata
"""
import datetime
import pathlib
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
BAZA = "https://quiz.freehtml.dev"
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
LIVE = "--live" in sys.argv

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


# Cloudflare raspunde 403 la agentul implicit al lui urllib ("Python-urllib/3.x"),
# deci un test care nu isi declara un User-Agent normal raporteaza esec acolo unde
# un browser primeste 200. Verificat pe viu pe 31.10.2026: curl 200, urllib 403.
AGENT = "Mozilla/5.0 (compatible; TekiDeki-sitemap-test/1.0; +https://quiz.freehtml.dev/)"


def cod(url):
    cerere = urllib.request.Request(url, headers={"User-Agent": AGENT})
    try:
        with urllib.request.urlopen(cerere, timeout=20) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:  # reteaua cazuta nu e un verdict despre sitemap
        return None, str(e).encode()


print("[1] Fisierele exista si sunt XML valid")
sitemap = ROOT / "sitemap.xml"
robots = ROOT / "robots.txt"
check(sitemap.is_file(), "sitemap.xml exista")
check(robots.is_file(), "robots.txt exista")
if not sitemap.is_file():
    print("\n%d verificari trecute, %d esuate" % (ok, rau))
    sys.exit(1)

try:
    radacina = ET.parse(sitemap).getroot()
    xml_ok = True
except ET.ParseError as e:
    radacina, xml_ok = None, False
    print("       eroare XML: " + str(e))
check(xml_ok, "sitemap.xml se poate parsa ca XML")
if not xml_ok:
    print("\n%d verificari trecute, %d esuate" % (ok, rau))
    sys.exit(1)
check(radacina.tag == NS + "urlset", "elementul radacina e urlset, in namespace-ul sitemaps.org")

print("[2] Continutul adreselor")
urls = radacina.findall(NS + "url")
check(len(urls) > 0, "sitemap-ul are cel putin o adresa")
azi = datetime.date.today()


def local_din_loc(loc):
    """https://quiz.freehtml.dev/ai-iq-test/ -> ai-iq-test/index.html"""
    cale = loc[len(BAZA):].strip("/")
    return (ROOT / (cale + "/index.html")) if cale else (ROOT / "index.html")


for u in urls:
    loc = (u.findtext(NS + "loc") or "").strip()
    lastmod = (u.findtext(NS + "lastmod") or "").strip()
    changefreq = (u.findtext(NS + "changefreq") or "").strip()
    priority = (u.findtext(NS + "priority") or "").strip()
    check(loc.startswith(BAZA + "/"), "adresa relativa la gazda: " + loc)
    check(loc.endswith("/"), "adresa are slash la final, fara redirect: " + loc)
    fisier = local_din_loc(loc)
    check(fisier.is_file(), "pagina exista in repo: " + str(fisier.relative_to(ROOT)))
    try:
        data = datetime.date.fromisoformat(lastmod)
        check(data <= azi, "lastmod nu vine din viitor: " + lastmod)
    except ValueError:
        check(False, "lastmod e o data ISO valida: " + repr(lastmod))
    check(changefreq in {"always", "hourly", "daily", "weekly", "monthly", "yearly", "never"},
          "changefreq e o valoare permisa: " + changefreq)
    try:
        val = float(priority)
        check(0.0 <= val <= 1.0, "priority intre 0 si 1: " + priority)
    except ValueError:
        check(False, "priority e numar: " + repr(priority))

print("[3] Nicio pagina publicata nu lipseste din sitemap")
pagini = {p for p in ROOT.rglob("index.html") if "tests" not in p.parts}
incluse = {local_din_loc((u.findtext(NS + "loc") or "").strip()) for u in urls}
for p in sorted(pagini):
    check(p in incluse, "pagina e in sitemap: " + str(p.relative_to(ROOT)))

print("[4] robots.txt")
text = robots.read_text(encoding="utf-8")
check("User-agent: *" in text, "robots.txt se adreseaza tuturor agentilor")
check("Allow: /" in text, "robots.txt permite accesul la tot site-ul")
check("Sitemap: " + BAZA + "/sitemap.xml" in text, "robots.txt trimite exact la sitemap")

print("[5] Cratima lunga (R31)")
for f in ("sitemap.xml", "robots.txt"):
    continut = (ROOT / f).read_text(encoding="utf-8")
    check("\u2014" not in continut and "&mdash;" not in continut, f + ": fara cratima lunga (R31)")

if LIVE:
    print("[6] Publicat: fiecare adresa raspunde 200")
    for loc in sorted((u.findtext(NS + "loc") or "").strip() for u in urls):
        status, _ = cod(loc)
        check(status == 200, "200 pentru " + loc + " (primit: %s)" % status)
    status, corp = cod(BAZA + "/sitemap.xml")
    check(status == 200, "sitemap publicat, 200 (primit: %s)" % status)
    check(b"<urlset" in corp, "sitemapul publicat chiar e XML sitemap")
    status, corp = cod(BAZA + "/robots.txt")
    check(status == 200, "robots.txt publicat, 200 (primit: %s)" % status)
    check(b"Sitemap: " + BAZA.encode() in corp, "robots.txt publicat trimite la sitemap")

print("\n%d verificari trecute, %d esuate" % (ok, rau))
sys.exit(1 if rau else 0)
