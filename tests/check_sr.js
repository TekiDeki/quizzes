#!/usr/bin/env node
/* check_sr.js (v2) — verificare mecanică sr-cyrl ↔ sr-latn pentru quiz-uri și hub-ul TekiDeki
 * Regula: sârba latină↔chirilică e bijecție perfectă (Љ=Lj, Џ=Dž...).
 * Orice diferență între translit(sr-cyrl) și sr-latn = greșeală de transcriere.
 * Prinde și: sr-cyrl fără nicio literă chirilică (paste de variantă latină)
 *            și litere chirilice strecurate în sr-latn.
 * v2: Q opțional (hub-ul n-are bancă de întrebări), L parcurs recursiv (obiecte
 *     imbricate, ex. cards), contor real de perechi verificate.
 * Folosire: node check_sr.js [cale/către/index.html]
 * Ieșire: lista problemelor + „OK" dacă e curat. Exit code 1 la probleme.
 */
"use strict";
const fs = require("fs");
const file = process.argv[2] || "index.html";
const t = fs.readFileSync(file, "utf8");
const script = t.split(/<script>/)[1].split("</script>")[0];

function sectionEnd(s, marks) {
  let best = -1;
  for (const m of marks) { const i = s.indexOf(m); if (i > -1 && (best === -1 || i < best)) best = i; }
  return best;
}
const lStart = script.indexOf("var L={");
const lEnd = sectionEnd(script, ["/* ---------- question bank", "/* ---------- quizzes", "/* ---------- state"]);
const lsrc = lStart > -1 ? script.substring(lStart, lEnd > -1 ? lEnd : undefined) : "";
const qStart = script.indexOf("var Q=[");
let qsrc = "";
if (qStart > -1) {
  const qEnd = script.indexOf("/* ---------- state", qStart);
  qsrc = script.substring(qStart, qEnd > -1 ? qEnd : undefined);
}
let L, Q;
try {
  L = (0, eval)(lsrc + "\nL");
  Q = qsrc ? (0, eval)(qsrc + "\nQ") : [];
} catch (e) {
  console.error("Nu am putut evalua datele din fișier: " + e.message);
  process.exit(1);
}

const CYR2LAT = {
  "А":"A","Б":"B","В":"V","Г":"G","Д":"D","Ђ":"Đ","Е":"E","Ж":"Ž","З":"Z","И":"I",
  "Ј":"J","К":"K","Л":"L","Љ":"Lj","М":"M","Н":"N","Њ":"Nj","О":"O","П":"P","Р":"R",
  "С":"S","Т":"T","Ћ":"Ć","У":"U","Ф":"F","Х":"H","Ц":"C","Ч":"Č","Џ":"Dž","Ш":"Š"
};
function translit(s) {
  let out = "";
  const chars = [...s];
  for (let i = 0; i < chars.length; i++) {
    const c = chars[i];
    if (Object.prototype.hasOwnProperty.call(CYR2LAT, c)) {
      const lat = CYR2LAT[c];                     // tabelul e deja titlecase: Lj, Nj, Dž
      const next = chars[i + 1];
      if (["Љ", "Њ", "Џ"].includes(c)) {
        // majusculă urmată de minusculă -> Lj; altfel (all-caps) -> LJ
        out += (next && next === next.toLowerCase()) ? lat : lat.toUpperCase();
      } else out += lat;
    } else {
      const lower = c.toLowerCase();
      const upperKey = Object.keys(CYR2LAT).find(k => k.toLowerCase() === lower && k !== k.toLowerCase());
      out += upperKey ? CYR2LAT[upperKey].toLowerCase() : c; // latină, cifre, semne — trec neschimbate
    }
  }
  return out;
}
const hasCyr = s => [...s].some(c => c >= "\u0400" && c <= "\u04FF");
const hasLatLetters = s => /[A-Za-z]/.test(s);

let problems = [];
let checked = 0;
function pair(where, cyr, lat, en) {
  checked++;
  if (lat === undefined || lat === null) { problems.push(where + ": lipsește sr-latn"); return; }
  if (cyr === undefined || cyr === null) { problems.push(where + ": lipsește sr-cyrl"); return; }
  // Titlu/brand care stă intenționat în latină în ambele variante: sr-cyrl === sr-latn === en
  if (en !== undefined && cyr === lat && lat === en) return;
  if (!hasCyr(cyr) && hasLatLetters(cyr))
    problems.push(where + ": sr-cyrl nu conține NICIUN caracter chirilic (paste latin?): \"" + cyr.slice(0,70) + "\"");
  if (hasCyr(lat))
    problems.push(where + ": sr-latn conține chirilice: \"" + lat.slice(0,70) + "\"");
  const expected = translit(cyr);
  if (expected !== lat)
    problems.push(where + ": translit(sr-cyrl) ≠ sr-latn\n    așteptat: \"" + expected + "\"\n    actual:  \"" + lat);
}

// 1) locale: perechi pe cheie, recursiv prin obiecte imbricate (topic, cards, ...)
function walk(cyrNode, latNode, path) {
  for (const k of Object.keys(cyrNode)) {
    const c = cyrNode[k], l = latNode ? latNode[k] : undefined;
    if (typeof c === "string") pair(path + k, c, l);
    else if (typeof c === "object" && c !== null) walk(c, l, path + k + ".");
  }
}
if (!L || !L["sr-cyrl"] || !L["sr-latn"]) {
  console.error("Nu am găsit localele sr-cyrl/sr-latn în var L={...}");
  process.exit(1);
}
walk(L["sr-cyrl"], L["sr-latn"], "L.");

// 2) întrebări (opțional): q, opțiuni (t), explicații (w)
Q.forEach((q, i) => {
  const id = q.id || ("q" + i);
  pair(id + ".q", q.q["sr-cyrl"], q.q["sr-latn"]);
  q.o.forEach((o, j) => {
    pair(id + ".o" + j, o.t["sr-cyrl"], o.t["sr-latn"], o.t.en);
    pair(id + ".w" + j, o.w["sr-cyrl"], o.w["sr-latn"]);
  });
});

if (problems.length) {
  console.error("PROBLEME (" + problems.length + "):");
  problems.forEach(p => console.error("  ✗ " + p));
  process.exit(1);
} else {
  console.log("OK: " + checked + " perechi sr-cyrl↔sr-latn verificate, zero diferențe.");
}
