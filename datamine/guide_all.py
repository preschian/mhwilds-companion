"""Field Guide tables -> guide.json (habitat, species, SP attacks, titles...).

Reads extract_report/merged (Common/Enemy/*), extract_reporttext/merged,
extract_breaktext/merged, mtext_merged (Mission texts), serial2em.json.
Writes MHRESEARCH/guide.json: fully resolved, human-readable.
"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
HERE = os.environ.get('MHRESEARCH', os.path.join(__import__('tempfile').gettempdir(), 'mhwilds-research'))
sys.path.insert(0, HERE)
import monster_extra as mx
from msg_parse import parse as parse_msg

R = os.path.join(HERE, 'extract_report', 'merged', 'natives', 'STM', 'GameDesign', 'Common', 'Enemy')
FALLBACK = os.path.join(HERE, 'reward_merged', 'natives', 'STM', 'GameDesign', 'Common', 'Enemy')
if not os.path.isdir(R):
    R = FALLBACK
T = os.path.join(HERE, 'extract_reporttext', 'merged', 'natives', 'STM', 'GameDesign', 'Text', 'Excel_Data')
B = os.path.join(HERE, 'extract_breaktext', 'merged', 'natives', 'STM', 'GameDesign', 'Text', 'Excel_Data')
M = os.path.join(HERE, 'mtext_merged', 'natives', 'STM', 'GameDesign', 'Text', 'Mission')


def sval(o):
    if isinstance(o, dict):
        return o.get('_Value', o.get('Value', o))
    return o


def clean(s):
    if not s:
        return None
    s = s.replace('\r\n\r\n', '\n\n').replace('\r\n', ' ').strip()
    return s or None


def msg_guid_map(path):
    """msg file -> {guid: (name, eng)}."""
    r = parse_msg(path)
    try:
        eng = r['langs'].index(1)
    except ValueError:
        eng = 1
    return {e['guid']: (e['name'], e['refs'][eng] if eng < len(e['refs']) else '')
            for e in r.get('entries') or []}


def msg_slim(path):
    r = parse_msg(path)
    try:
        eng = r['langs'].index(1)
    except ValueError:
        eng = 1
    return [(e['name'], e['refs'][eng] if eng < len(e['refs']) else '')
            for e in r.get('entries') or []]


IDMAP = {v: k for k, v in mx.enum_map('app.EnemyDef.ID').items()}
IDFIX = {v: k for k, v in mx.enum_map('app.EnemyDef.ID_Fixed').items()}
try:
    SERIAL2EM = json.load(open(os.path.join(HERE, 'serial2em.json'), encoding='utf-8'))
except FileNotFoundError:
    SERIAL2EM = {}


def em_of_serial(v):
    name = SERIAL2EM.get(str(v)) or IDFIX.get(v) or IDMAP.get(v)
    m = re.match(r'EM(\d+)_(\d+)', name or '')
    return f'EM{m.group(1)}_{m.group(2)}' if m else None


def table(fn):
    r = mx.auto_parse(os.path.join(R, fn))
    vals = r.get('_Values')
    if isinstance(vals, dict):
        vals = vals.get('_DataArray', [])
    return [v for v in (vals or []) if v is not None]


out = {}

# --- special-attack / attribute type maps (bit N <-> type N, 1-based) ---
sp_text = {}
for p in glob.glob(os.path.join(T, 'EnemyReportSpecialAttackTypeText.msg.23')):
    sp_text.update(msg_guid_map(p))
sp_rows = []
for row in table('EnemyReportSpecialAttackTypeData.user.3'):
    nm = sp_text.get(row.get('_EmSpecialAttackName'), ('?', '?'))
    sp_rows.append({'bit': row.get('_Index'), 'type': row.get('_EmSpecialAttackType'),
                    'name': nm[1]})
out['spAttackTypes'] = sorted(sp_rows, key=lambda d: d['bit'])
wa_text = {}
for p in glob.glob(os.path.join(T, 'EnemyReportWeaponAttributeText.msg.23')):
    wa_text.update(msg_guid_map(p))
wa_rows = []
for row in table('EnemyReportWeaponAttributeData.user.3'):
    nm = wa_text.get(row.get('_EmWeaponAttributeName'), ('?', '?'))
    wa_rows.append({'index': row.get('_Index'), 'attr': sval(row.get('_EmWeaponAttribute')),
                    'name': nm[1]})
out['weaponAttributes'] = sorted(wa_rows, key=lambda d: d['index'])

# --- boss / zako / animal habitat + guide bits ---
for fn, tag in (('EnemyReportBossData.user.3', 'boss'),
                ('EnemyReportZakoData.user.3', 'zako'),
                ('EnemyReportAnimalData.user.3', 'animal')):
    rows = []
    for e in table(fn):
        sb = (e.get('_StageBit') or {}).get('_Value') or [0]
        d = {'index': e.get('_Index'), 'emId': e.get('_EmID'),
             'em': em_of_serial(e.get('_EmID')), 'stageBit': sb[0]}
        if tag == 'boss':
            sp = (e.get('_EnemySPAttackBit') or {}).get('_Value') or [0, 0]
            ra = (e.get('_RecoAttributeBit') or {}).get('_Value') or [0]
            d['spAtk'] = sp
            d['recoAttr'] = ra[0]
        rows.append(d)
    out[tag] = rows
    print(tag, len(rows))

# --- anatomy break slots per boss ---
brk_text = {}
for p in glob.glob(os.path.join(B, 'EnemyReportPartsBreakTypeName.msg.23')):
    brk_text.update(msg_guid_map(p))
brk_types = {}
for row in table('EnemyReportPartsBreakTypeData.user.3'):
    nm = brk_text.get(row.get('_EmReportPartsBreakTypeName'), ('?', '?'))
    brk_types[sval(row.get('_EmReportPartsBreakType'))] = nm[1]
out['breakTypes'] = {str(k): v for k, v in brk_types.items()}
anatomy = []
for e in table('EnemyReportAnatomyPartsBreakData.user.3'):
    slots = []
    for k, v in e.items():
        if k.startswith('$') or k in ('_Index', '_EmID') or 'Arrow' in k:
            continue
        if k.endswith('PartsBreakType'):
            continue
        slots.append({'slot': k, 'partsType': sval(v),
                      'breakType': brk_types.get(sval(e.get(k + 'PartsBreakType')),
                                                 sval(e.get(k + 'PartsBreakType')))})
    anatomy.append({'index': e.get('_Index'), 'emId': e.get('_EmID'),
                    'em': em_of_serial(e.get('_EmID')), 'slots': slots})
out['anatomy'] = anatomy
print('anatomy', len(anatomy))

# --- species names ---
species = []
for p in glob.glob(os.path.join(T, 'EnemySpeciesName.msg.23')):
    for name, eng in msg_slim(p):
        m = re.match(r'EnemySpeciesName_(\d+)', name)
        if m and eng:
            species.append({'id': int(m.group(1)), 'name': eng})
out['species'] = sorted(species, key=lambda d: d['id'])

# --- title free-info texts (Hunt N: <word>) ---
freeinfo = {}
for p in glob.glob(os.path.join(T, 'EnemyReportBossTitleDataText.msg.23')):
    freeinfo.update(msg_guid_map(p))
out['titleFreeInfo'] = {g: {'name': n, 'text': clean(e)} for g, (n, e) in freeinfo.items()}
print('titleFreeInfo', len(out['titleFreeInfo']))

# --- quest titles + descriptions (EN) ---
titles = {}
for p in sorted(glob.glob(os.path.join(M, 'Mission*.msg.23'))):
    m = re.search(r'Mission(\d+)\.msg', os.path.basename(p))
    if not m:
        continue
    titles[m.group(1)] = [{'name': n, 'text': clean(e)} for n, e in msg_slim(p)]
out['questTitles'] = titles
print('questTitles', len(titles))

json.dump(out, open(os.path.join(HERE, 'guide.json'), 'w', encoding='utf-8'),
          indent=1, ensure_ascii=False)
print('DONE guide')
