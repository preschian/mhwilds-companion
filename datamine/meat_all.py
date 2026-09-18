"""Build the full companion hitzone dataset from all Param_Parts files.

Usage: python meat_all.py
Writes: monsters.json (dataset), validation.txt (Kiranico cross-check report).
"""
import json
import os
import tempfile
import re
import sys

HERE = os.environ.get('MHRESEARCH', os.path.join(tempfile.gettempdir(), 'mhwilds-research'))
sys.path.insert(0, HERE)
from meat_extract import load_layouts, parse_parts_file  # noqa: E402
from rsz_classscan import build_map  # noqa: E402

ROOT = os.path.join(HERE, 'extract_full', 'merged', 'natives', 'STM', 'GameDesign', 'Enemy')
REF = os.path.join(HERE, 'MH-Wilds-Monster-Database', 'web-scraper', 'monster_data.json')

MEAT_KEYS = ['slash', 'blow', 'shot', 'fire', 'water', 'thunder', 'ice', 'dragon', 'stun', 'lightPlant']
SRC_KEYS = ['_Slash', '_Blow', '_Shot', '_Fire', '_Water', '_Thunder', '_Ice', '_Dragon', '_Stun', '_LightPlant']
STATES = [('normal', '_MeatGuidNormal'), ('break', '_MeatGuidBreak'),
          ('custom1', '_MeatGuidCustom1'), ('custom2', '_MeatGuidCustom2'),
          ('custom3', '_MeatGuidCustom3'), ('custom4', '_MeatGuidCustom4'),
          ('custom5', '_MeatGuidCustom5')]
EMPTY = '00' * 16

# Field Guide EmID -> internal (em, variant) via monster names.
FG_MAP = {'Rathian': 0, 'Rathalos': 1, 'Guardian Rathalos': 2, 'Gravios': 3,
          'Yian Kut-Ku': 4, 'Gypceros': 5, 'Congalala': 6, 'Blangonga': 7,
          'Lagiacrus': 8, 'Nerscylla': 9, 'Gore Magala': 10, 'Seregios': 11,
          'Gogmazios': 12, 'Mizutsune': 13, 'Guardian Fulgur Anjanath': 14,
          'Guardian Ebony Odogaron': 15, 'Doshaguma': 16, 'Guardian Doshaguma': 17,
          'Balahara': 18, 'Chatacabra': 19, 'Quematrice': 20, 'Lala Barina': 21,
          'Rompopolo': 22, 'Rey Dau': 23, 'Uth Duna': 24, 'Nu Udra': 25,
          'Ajarakan': 26, 'Arkveld': 27, 'Guardian Arkveld': 28, 'Hirabami': 29,
          'Jin Dahaad': 30, 'Xu Wu': 31, 'Zoh Shia': 32, 'Omega Planetes': 34}

SHARED = {('EM0160', '50'): ('EM0160', '00')}  # Guardian Arkveld shares Arkveld parts.


def meat_vals(m):
    return {k: m[s] for k, s in zip(MEAT_KEYS, SRC_KEYS)}


def load_json(name):
    """Load a workdir JSON, tolerating PS-redirect (UTF-16) or UTF-8."""
    path = os.path.join(HERE, name)
    if not os.path.exists(path):
        raise SystemExit(f'missing {path} -- run the earlier pipeline steps first')
    for enc in ('utf-8', 'utf-16'):
        try:
            with open(path, encoding=enc) as f:
                return json.load(f)
        except (UnicodeError, json.JSONDecodeError):
            continue
    raise SystemExit(f'cannot decode {path} as utf-8 or utf-16')


def main():
    print('loading layouts + murmur map...', flush=True)
    layouts = load_layouts()
    mmap = build_map()
    enums = load_json('parts_enums.json')
    pnames = load_json('part_names.json')
    etext = load_json('enemy_text_merged.json')
    erod = {str(v): k for k, v in enums['app.Hit.ROD_EXTRACT'].items()}
    names = {}
    for e in etext:
        m = re.fullmatch(r'EnemyText_(?:FRENZY_|LEGENDARY_KING_)?NAME_(EM\d+_\d+_\d+)', e['name'])
        if m and e['eng']:
            names.setdefault(m.group(1), e['eng'])

    files = []
    for dp, _, fns in os.walk(ROOT):
        for fn in fns:
            if fn.endswith('_Param_Parts.user.3'):
                files.append(os.path.join(dp, fn))
    files.sort()
    print(f'part files: {len(files)}', flush=True)

    monsters = []
    for path in files:
        rel = os.path.relpath(path, ROOT)
        em, var = rel.split(os.sep)[0], rel.split(os.sep)[1]
        key = f'{em.upper()}_{var}_0'
        name = names.get(key, f'{em}_{var}')
        try:
            root, end, total = parse_parts_file(path, layouts, mmap)
        except Exception as e:  # noqa: BLE001
            print(f'PARSE-FAIL {rel}: {e}')
            continue
        assert end == total, f'{rel}: end 0x{end:X} != len 0x{total:X}'
        meats = {m['_InstanceGuid']: meat_vals(m) for m in root['_MeatArray']['_DataArray']}
        by_guid = {p['_InstanceGuid']: p for p in root['_PartsArray']['_DataArray']}
        parts = []
        for p in root['_PartsArray']['_DataArray']:
            states = {}
            for label, slot in STATES:
                g = p[slot]
                if g != EMPTY and g in meats:
                    states[label] = meats[g]
            parts.append({'part': pnames.get(str(p['_PartsType']['_Value']),
                                             f"PART<{p['_PartsType']['_Value']}>"),
                          'kinsect': erod.get(str(p['_RodExtract']), p['_RodExtract']),
                          'states': states})
        weak = []
        for w in root['_WeakPointArray']['_DataArray']:
            link = by_guid.get(w['_LinkPartsGuid'], {})
            pt = link.get('_PartsType', {}).get('_Value') if link else None
            weak.append({'part': pnames.get(str(pt)) if pt is not None else None,
                         'values': meats.get(w['_MeatGuid'])})
        scars = []
        for s in root['_ScarPointArray']['_DataArray']:
            link = by_guid.get(s['_LinkPartsGuid'], {})
            pt = link.get('_PartsType', {}).get('_Value') if link else None
            scars.append({'part': pnames.get(str(pt)) if pt is not None else None,
                          'num': s['_Num'], 'values': meats.get(s['_MeatGuid'])})
        breaks = []
        for b in root['_PartsBreakArray']['_DataArray']:
            breaks.append({'part': pnames.get(str(b['_PartsType']['_Value']),
                                             f"PART<{b['_PartsType']['_Value']}>"),
                           'maxCount': b['_MaxCount']})
        monsters.append({'em': em.upper(), 'variant': var, 'name': name,
                         'fieldGuideEmId': FG_MAP.get(name),
                         'baseHealth': root.get('_BaseHealth'),
                         'source': rel.replace(os.sep, '/'),
                         'parts': parts, 'weakPoints': weak, 'scars': scars,
                         'partsBreak': breaks})
        print(f'  ok {em}_{var} {name} parts={len(parts)}', flush=True)

    # Shared-data variants (Guardian Arkveld).
    by_em = {(m['em'], m['variant']): m for m in monsters}
    for (em, var), (sem, svar) in SHARED.items():
        src = by_em.get((sem, svar))
        key = f'{em}_{var}_0'
        monsters.append({**src, 'em': em, 'variant': var, 'name': names.get(key, key),
                         'fieldGuideEmId': FG_MAP.get(names.get(key, '')),
                         'sharedFrom': f'{sem}_{svar}'})
        print(f'  shared {em}_{var} <- {sem}_{svar}', flush=True)

    monsters.sort(key=lambda m: (m['fieldGuideEmId'] is None, m['fieldGuideEmId'] or 0, m['em']))
    json.dump(monsters, open(os.path.join(HERE, 'monsters.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'wrote monsters.json ({len(monsters)} entries)')
    validate(monsters)


def norm(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())


def validate(monsters):
    if not os.path.exists(REF):
        print(f'validation skipped (optional reference not found: {REF})')
        return
    ref = json.load(open(REF, encoding='utf-8'))
    ours = {m['name']: m for m in monsters}
    lines = []
    n_match = n_cell = n_diff = 0
    missing = []
    for r in ref:
        m = ours.get(r['name'])
        if m is None:
            missing.append(r['name'])
            continue
        oparts = {norm(p['part']): p for p in m['parts']}
        for h in r['hitzones']:
            if h.get('state'):
                continue
            p = oparts.get(norm(h['part_name']))
            if p is None:
                lines.append(f"{r['name']}: part missing in ours: {h['part_name']}")
                continue
            ours_n = p['states'].get('normal', {})
            for k, rk in [('slash', 'sever'), ('blow', 'blunt'), ('shot', 'ammo'),
                          ('fire', 'fire'), ('water', 'water'), ('thunder', 'thunder'),
                          ('ice', 'ice'), ('dragon', 'dragon'), ('stun', 'stun')]:
                n_cell += 1
                if ours_n.get(k) == h[rk]:
                    n_match += 1
                else:
                    n_diff += 1
                    lines.append(f"{r['name']}/{h['part_name']}.{k}: ours={ours_n.get(k)} kiranico={h[rk]}")
            ok = norm(p.get('kinsect', '')) == norm(h.get('kinsect_extract', ''))
            if not ok:
                lines.append(f"{r['name']}/{h['part_name']}.kinsect: ours={p.get('kinsect')} "
                             f"kiranico={h.get('kinsect_extract')}")
    only_ours = sorted(set(ours) - {r['name'] for r in ref})
    report = [f'normal-state cells: {n_match}/{n_cell} match ({100.0 * n_match / max(n_cell, 1):.1f}%)',
              f'in kiranico but missing in ours: {missing}',
              f'in ours but missing in kiranico: {only_ours}',
              '--- diffs ---'] + lines
    open(os.path.join(HERE, 'validation.txt'), 'w', encoding='utf-8').write('\n'.join(report))
    print('\n'.join(report[:12]))
    print(f'... full report: validation.txt ({len(lines)} diff lines)')


if __name__ == '__main__':
    main()
