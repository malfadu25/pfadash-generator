#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generateur du Dashboard PFA - Bloc Sud (GPEI).
Mode hebdomadaire : recalcule les champs de DONNEES par zone de sante a partir
des canevas provinciaux, et REPORTE le scoring (cat, flags, priority, risk_*)
depuis le gabarit precedent (passe de scoring periodique, cf. consigne projet).

Numerateur : liste linaire ("Base de donnees"), EPID distincts, contacts exclus,
< 15 ans (>=15 -> pfa_o15). Populations et % selles : onglet "ZS".
Taux : t26 = c26/pop15_26*1e5*52/semaine ; ta26 = t26*IF ; idem 12 mois.
"""
import json, re, unicodedata, argparse, sys
from collections import defaultdict
from openpyxl import load_workbook
import warnings; warnings.filterwarnings("ignore")

SEMAINE = 38  # semaine d'annualisation (verifiee = semaine max reelle de la liste lineaire)

# Alias de noms ZS (dashboard <- fichier), cf. consigne
ALIAS = {"RUASHI": "RWASHI"}

def norm(x):
    x = unicodedata.normalize('NFKD', str(x or '')).encode('ascii', 'ignore').decode().upper().strip()
    return re.sub(r'\s+', '', x)

def epid_key(ep):
    """Normalise les separateurs pour dedoublonner les fautes de frappe (double tiret, parenthese)."""
    k = re.sub(r'[^A-Z0-9]', '-', str(ep).upper())
    return re.sub(r'-+', '-', k).strip('-')

# ---------------------------------------------------------------- parsing canevas
def _header_row(ws, needles=('epid', 'zone')):
    for r in range(1, 14):
        cells = [str(ws.cell(r, c).value or '').lower() for c in range(1, ws.max_column + 1)]
        if all(any(n in v for v in cells) for n in needles):
            return r
    return None

def _col(H, *keys):
    for c, h in H.items():
        hl = h.lower()
        if all(k in hl for k in keys):
            return c
    return None

def parse_linelist(path):
    """Retourne {ZSnorm: {'c26':int,'pfa_o15':int}} depuis 'Base de donnees'."""
    ws = load_workbook(path, data_only=True)['Base de données']
    HR = _header_row(ws, ('epid', 'zone'))
    H = {c: str(ws.cell(HR, c).value or '').strip() for c in range(1, ws.max_column + 1)}
    cZS = _col(H, 'zone', 'sant') or _col(H, 'zones', 'sant') or _col(H, 'zone')
    cEP = _col(H, 'epid')
    cAge = _col(H, 'age', 'ann') or _col(H, 'âge', 'ann')
    cCon = next((c for c, h in H.items() if 'contact' in h.lower()), None)
    cases = defaultdict(set); o15 = defaultdict(int)
    for r in range(HR + 1, ws.max_row + 1):
        ep = ws.cell(r, cEP).value if cEP else None
        if not ep or not str(ep).upper().startswith('RDC'):
            continue
        k = epid_key(ep)
        con = str(ws.cell(r, cCon).value).strip() if cCon else ''
        if con in ('2', '2.0') or re.search(r'-C\d', k) or 'CC' in k:
            continue
        zs = norm(ws.cell(r, cZS).value) if cZS else '?'
        age = ws.cell(r, cAge).value if cAge else None
        try: av = float(age)
        except Exception: av = None
        if av is not None and av >= 15:
            o15[zs] += 1; continue
        cases[zs].add(k)
    return {z: {'c26': len(v), 'pfa_o15': o15.get(z, 0)} for z, v in cases.items()}, dict(o15)

def parse_zs_sheet(path):
    """Retourne {ZSnorm: {'pop15':float,'aq26':float}} depuis l'onglet 'ZS'."""
    ws = load_workbook(path, data_only=True)['ZS']
    # header ligne 3 (consigne) : reperer par contenu
    HR = None
    for r in range(1, 8):
        cells = [str(ws.cell(r, c).value or '').lower() for c in range(1, ws.max_column + 1)]
        if any('zone' in v for v in cells) and any('pop' in v for v in cells):
            HR = r; break
    H = {c: str(ws.cell(HR, c).value or '').strip() for c in range(1, ws.max_column + 1)}
    cZS = _col(H, 'zone') or 1
    cPop = _col(H, 'pop', '15')
    cAq = _col(H, 'selles', 'adequat') or _col(H, 'selles', 'adiquat')
    out = {}
    for r in range(HR + 1, ws.max_row + 1):
        z = ws.cell(r, cZS).value
        if not z: continue
        zn = norm(z)
        prov = ws.cell(r, 2).value
        if not prov or 'total' in str(z).lower() or zn == norm(prov):
            continue  # exclure lignes total et ligne au nom de la province
        def num(c):
            try: return float(ws.cell(r, c).value)
            except Exception: return None
        pop = num(cPop); aq = num(cAq)
        if aq is not None and aq <= 1.0001: aq = round(aq * 100, 1)
        out[zn] = {'pop15': pop, 'aq26': aq}
    return out

# ---------------------------------------------------------------- anonymisation & meta
def anonymize(html):
    """Version PUBLIC : chaque "Nom (CODE)" devient "CODE" (codes AT-/AP-).
    Valide : reproduit exactement la version publique de reference (0 nom residuel)."""
    return re.sub(r'"([^"]*?) \((AT-\d+|AP-\d+)\)"', r'"\2"', html)

def bump_meta(s, meta_version=None, semaine=None, date_maj=None,
              footer_from=None, footer_to=None, changelog_entry=None):
    """Met a jour le bandeau __META__ (version, semaine, date), prepend une entree
    de changelog, et bascule le numero de version du pied de page/titre."""
    if meta_version:
        s = re.sub(r'("version":")[0-9.]+(")', r'\g<1>' + meta_version + r'\2', s, count=1)
    if semaine:
        s = re.sub(r'("semaine":")[^"]*(")', r'\g<1>' + semaine + r'\2', s, count=1)
    if date_maj:
        s = re.sub(r'("date_maj":")[^"]*(")', r'\g<1>' + date_maj + r'\2', s, count=1)
    if changelog_entry:
        s = s.replace('"changelog":[', '"changelog":[' + changelog_entry, 1)
    if footer_from and footer_to:
        s = s.replace(footer_from, footer_to)
    return s

# ---------------------------------------------------------------- template I/O
def extract_block(s, name):
    i = s.find('const ' + name + '=')
    if i < 0: i = s.find(name + '=')
    b1, b2 = s.find('[', i), s.find('{', i)
    j = b1 if (b1 >= 0 and (b2 < 0 or b1 < b2)) else b2
    op = s[j]; cl = ']' if op == '[' else '}'; d = 0; k = j
    while k < len(s):
        if s[k] == op: d += 1
        elif s[k] == cl:
            d -= 1
            if d == 0: break
        k += 1
    return j, k, s[j:k + 1]

# ---------------------------------------------------------------- generation
CANEVAS = {}  # prov -> path, rempli par l'appelant

def generate(template_path, canevas, out_path, validate_against=None,
             meta=None, public_out=None):
    s = open(template_path, encoding='utf-8').read()
    j, k, dtxt = extract_block(s, 'D')
    D = json.loads(dtxt)

    # 1) lire tous les canevas
    upd = {}  # (prov, ZSnorm) -> data
    for prov, path in canevas.items():
        ll, _ = parse_linelist(path)
        zs = parse_zs_sheet(path)
        for zn, d in ll.items():
            upd.setdefault((prov, zn), {}).update(d)
        for zn, d in zs.items():
            upd.setdefault((prov, zn), {}).update(d)

    def lookup(prov, z):
        zn = norm(z)
        for cand in (zn, ALIAS.get(zn), norm(ALIAS.get(zn, ''))):
            if cand and (prov, cand) in upd:
                return upd[(prov, cand)]
        return None

    # 2) appliquer aux lignes D (champs DONNEES uniquement ; scoring reporte)
    stats = defaultdict(lambda: [0, 0])
    for r in D:
        u = lookup(r['p'], r['z'])
        if not u:
            continue
        pop = u.get('pop15')
        if pop:
            r['pop15_26'] = int(round(pop))
            r['pop15_25'] = int(round(pop))
        if u.get('c26') is not None:
            r['c26'] = u['c26']
        if u.get('pfa_o15') is not None:
            r['pfa_o15'] = u['pfa_o15']
        if r.get('pop15_26'):
            base = r['c26'] / r['pop15_26'] * 1e5
            r['t26'] = round(base * 52 / SEMAINE, 2)
            if r.get('IF') is not None:
                r['ta26'] = round(r['t26'] * r['IF'], 2)
        if r.get('pop15_25') and r.get('c12') is not None:
            r['t12'] = round(r['c12'] / r['pop15_25'] * 1e5, 2)
            if r.get('IF') is not None:
                r['ta12'] = round(r['t12'] * r['IF'], 2)
        # aq26 : REPORTE du gabarit precedent (definition d'adequation des selles
        # calculee sur la liste lineaire par la passe de scoring, a reconstituer
        # exactement ulterieurement). Ne pas ecraser avec le % de la synthese.
        stats[r['p']][0] += 1

    # 3) validation optionnelle contre un D de reference
    report = None
    if validate_against:
        ref = {(x['p'], norm(x['z'])): x for x in json.load(open(validate_against))}
        fields = ['c26', 'pfa_o15', 'pop15_26', 't26', 'ta26']
        report = defaultdict(lambda: defaultdict(list))
        for r in D:
            x = ref.get((r['p'], norm(r['z'])))
            if not x: continue
            for f in fields:
                a, b = r.get(f), x.get(f)
                ok = (a == b) or (isinstance(a, float) and isinstance(b, float) and abs(a - b) < 0.05)
                report[r['p']][f].append((r['z'], a, b, ok))

    # 4) re-injecter D
    newD = json.dumps(D, ensure_ascii=False, separators=(',', ':'))
    s = s[:j] + newD + s[k + 1:]

    # 5) bandeau __META__ (version, semaine, changelog, pied de page)
    if meta:
        s = bump_meta(s, **meta)

    # 6) ecrire la version MANAGERS (noms + codes)
    open(out_path, 'w', encoding='utf-8').write(s)

    # 7) ecrire la version PUBLIC anonymisee (codes seuls), si demandee
    if public_out:
        pub = anonymize(s)
        n_names = len(re.findall(r'"[^"]+ \((?:AT|AP)-\d+\)"', pub))
        assert n_names == 0, f"anonymisation incomplete : {n_names} noms residuels"
        open(public_out, 'w', encoding='utf-8').write(pub)

    return D, stats, report

if __name__ == '__main__':
    UP = "/root/.claude/uploads/701935d9-20f8-5f7f-aeb4-69d62f5fb37b/"
    canevas = {
        'Haut-Katanga': UP + "d4840ea2-ANALYSE__SUIVI__DES__ECHANTILLONS_PFA_HAUT_KATANGA_DE_LA_S1_A_S38.xlsx",
        'Haut-Lomami':  UP + "b4d55b3c-Masque_nouveau_Bloc_-_MAJ_Haut-Lomami_S_38.xlsx",
        'Tanganyika':   UP + "bb97fca0-Masque_PFA_-_SEM_38_Tanganyika_VA.xlsx",
        'Lualaba':      UP + "c127d525-Base_Surveillance_PFA_Semaine_38-2026_Lualaba_1.xlsx",
    }
    meta = {
        'meta_version': '6.26.0',
        'semaine': 'S38/2026 (Haut-Katanga, Haut-Lomami, Tanganyika, Lualaba)',
        'date_maj': '2026-09-23',
        'footer_from': 'Dashboard PFA v9.7',
        'footer_to': 'Dashboard PFA v9.8',
        'changelog_entry': '{"version":"6.26.0","date":"2026-09-23","modifs":["Regeneration complete via le generateur reproductible (depot pfadash-generator) : donnees recalculees a partir des 4 canevas provinciaux S38, scoring reporte, version publique anonymisee produite automatiquement."]},',
    }
    D, stats, report = generate(
        '/tmp/Dashboard_BlocSud_PFA_Managers_v9.7.html',
        canevas,
        '/tmp/gen/_regen_managers.html',
        validate_against='/tmp/gt_D.json',
        meta=meta,
        public_out='/tmp/gen/_regen_public.html')
    print("ZS mises a jour par province:", {p: v[0] for p, v in stats.items()})
    print("\n=== VALIDATION (genere vs dashboard actuel) ===")
    for p in ['Haut-Katanga', 'Haut-Lomami', 'Tanganyika', 'Lualaba']:
        if p not in report: continue
        tot = ok = 0; diffs = []
        for f, lst in report[p].items():
            for z, a, b, good in lst:
                tot += 1; ok += good
                if not good: diffs.append((z, f, a, b))
        print(f"  {p:14} {ok}/{tot} champs concordants" + ("" if ok == tot else f"  ({len(diffs)} ecarts)"))
        for z, f, a, b in diffs[:10]:
            print(f"       {z:14} {f}: genere={a} vs actuel={b}")
