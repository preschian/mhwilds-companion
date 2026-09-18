"""Merge extra + missions + guide into data/monsters.json (+ quests, endemics).

Reads MHRESEARCH: monster_text, enemydata, questdata, guide_thresholds,
bosstitles, sizedata, extra, mission_index, guide, title_word, part_names,
enemy_guid. Writes data/monsters.json (additive), data/quests.json,
data/endemics.json, data/guide_meta.json.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
HERE = os.environ.get('MHRESEARCH', os.path.join(__import__('tempfile').gettempdir(), 'mhwilds-research'))
sys.path.insert(0, HERE)
import monster_extra as mx

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, 'data')


def load(name):
    with open(os.path.join(HERE, name), encoding='utf-8') as f:
        return json.load(f)


monster_text = load('monster_text.json')
enemydata = load('enemydata.json')
guilddata = load('questdata.json')
thresholds = load('guide_thresholds.json')
bosstitles = load('bosstitles.json')
sizedata = load('sizedata.json')
extra = load('extra.json')
missions = load('mission_index.json')
guide = load('guide.json')
title_words = {e['name']: e.get('eng') for e in load('title_word.json')}
part_names = load('part_names.json')
enemy_guid = load('enemy_guid.json')

monsters = json.load(open(os.path.join(DATA, 'monsters.json'), encoding='utf-8'))
by_em = {}
for m in monsters:
    by_em.setdefault((m.get('em'), m.get('variant')), m)

# ---------- enums / lookup tables ----------
QT = {v: k for k, v in mx.enum_map('app.QuestDef.QUEST_TYPE_Fixed').items()}
try:
    RR = {(v & 0xFFFFFFFF): k
          for k, v in mx.enum_map('app.QuestDef.EM_REWARD_RANK_Fixed').items()}
except Exception:
    RR = {}


def _rr(v):
    return RR.get(v & 0xFFFFFFFF, v) if isinstance(v, int) else v
ATTR = {v: k for k, v in mx.enum_map('app.WeaponDef.ATTR').items()}
ROLE = {v: k for k, v in mx.enum_map('app.EnemyDef.ROLE_ID').items()}
LEG = {v: k for k, v in mx.enum_map('app.EnemyDef.LEGENDARY_ID').items()}
MSZ = {v: k for k, v in mx.enum_map('app.EnemyDef.MODEL_SIZE').items()}

STAGE_BIT = {1: 'Windward Plains', 2: 'Scarlet Forest', 3: 'Oilwell Basin',
             4: 'Iceshard Cliffs', 5: 'Ruins of Wyveria'}
VENUE = {-1226157568: 'Windward Plains', -859829056: 'Scarlet Forest',
         -1251081216: 'Oilwell Basin', 1182228864: 'Iceshard Cliffs',
         327401792: 'Ruins of Wyveria', 2009549184: 'Wounded Hollow',
         13836: 'Oilwell Basin', 1181994624: 'Arena', 544388992: 'Special Arena',
         905584064: 'Special Venue', -1869346688: 'Grand Hub'}
SPECIES = {s['id']: s['name'] for s in guide.get('species', [])}
SP_BY_TYPE = {t['type']: t['name'] for t in guide.get('spAttackTypes', [])}
WA_BY_ATTR = {t['attr']: t['name'] for t in guide.get('weaponAttributes', [])}
KIND_VERB = {'HUNTING': 'Hunt', 'KILL': 'Slay', 'CAPTURE': 'Capture',
             'ARENA': 'Slay', 'BOSSRUSH': 'Hunt', 'COLLECTS': 'Gather',
             'TRANSPORT': 'Deliver', 'SPECIAL': 'Hunt'}


def bits(v):
    return [i for i in range(34) if v & (1 << i)]


def guid_text(g):
    if not g:
        return None
    e = enemy_guid.get(g) or enemy_guid.get(g.lower())
    t = (e or {}).get('eng') or ''
    t = t.replace('\r\n\r\n', '\n\n').replace('\r\n', ' ').strip()
    return t or None


def norm_part(s):
    return re.sub(r'[^a-z]+', '', (s or '').lower())


def _title_count(guide, freeinfo_guid):
    info = (guide.get('titleFreeInfo') or {}).get(freeinfo_guid or '', {})
    m = re.search(r'Hunt (\d+)', info.get('text') or '')
    return int(m.group(1)) if m else None


# ---------- quests ----------
def quest_locale(q):
    cands = []
    if q.get('fieldStage') != 1044114240:
        cands.append(q.get('fieldStage'))
    cands += sorted(set(e['tagField'] for e in q.get('emSets', [])) - {1044114240})
    qs = (q.get('quest') or {}).get('stage')
    if qs not in (None, 1044114240):
        cands.append(qs)
    cands = [c for c in cands if c in VENUE]
    return VENUE[cands[0]] if cands else 'Arena/Special'


def quest_kind(q):
    t = (q.get('quest') or {}).get('type')
    return QT.get(t) if t is not None else None


def quest_star(mid, q):
    qd = q.get('quest') or {}
    if qd.get('lv') is not None:
        return qd['lv']
    if re.match(r'10[1-9]', mid):
        return int(mid[2])
    return None


quests_out = []
mon_quests = {}
for mid in sorted(missions):
    q = missions[mid]
    loc = quest_locale(q)
    kind = quest_kind(q)
    star = quest_star(mid, q)
    band = 'High Rank' if (star is not None and star >= 4) or mid[:3] in (
        '004', '005', '006', '007', '008') else ('Low Rank' if star is not None and star <= 3
           or mid[:3] in ('001', '002', '003') else None)
    targets = []
    for t in q.get('mains') or []:
        if t.get('em'):
            targets.append({'em': t['em'][0], 'variant': t['em'][1], 'role': 'main',
                            'layout': t.get('layout'),
                            'roleId': t.get('role'), 'variantKind': t.get('legendary')})
    # Title templating counts targets within ONE layout (layouts are
    # solo/multi variants of the same hunt, not additional monsters).
    by_lay = {}
    for t in targets:
        by_lay.setdefault(t.get('layout') or '', []).append(t)
    t1 = sorted(by_lay.values(), key=lambda g: (-len(g), str(g[0].get('layout'))))[0] \
        if by_lay else []
    # title: real text, else template from kind + targets
    texts = {e['name']: e['text'] for e in (guide.get('questTitles', {}).get(mid) or [])}
    title = texts.get(f'Mission{mid}_000')
    desc = texts.get(f'Mission{mid}_001')
    guessed = False
    if not title or 'Rejected' in title:
        guessed = True
        names = []
        for t in t1:
            m = by_em.get((t['em'], t['variant'])) or by_em.get((t['em'], '00'))
            if m:
                names.append(m['name'])
        if mid[:2] in ('72', '73', '74') or mid[:3] == '700':
            title = (names[0] + ' Investigation') if len(names) == 1 else (
                ', '.join(names[:2]) + ' Investigation' if names else 'Investigation')
        elif names:
            verb = KIND_VERB.get(kind or 'HUNTING', 'Hunt')
            uniq = sorted(set(names))
            if len(uniq) == 1 and len(names) == 1:
                title = f'{verb} the {uniq[0]}'
            elif len(uniq) == 1:
                title = f'{verb} {len(names)} {uniq[0]}'
            else:
                title = f'{verb} all target monsters'
        else:
            title = None
    qd = q.get('quest') or {}
    rec = {'id': mid, 'title': title, 'titleGuessed': guessed,
           'locale': loc, 'kind': kind, 'star': star, 'rankBand': band,
           'time': qd.get('time'), 'faints': qd.get('faints'),
           'money': qd.get('money'), 'hrPoints': qd.get('hr'),
           'orderHR': qd.get('orderHR'), 'targets': targets}
    if desc and 'Rejected' not in desc:
        rec['desc'] = desc
    quests_out.append(rec)
    for t in targets:
        mon_quests.setdefault((t['em'], t['variant']),
                              []).append({'quest': mid, 'title': title,
                                          'locale': loc, 'kind': kind,
                                          'role': t['role'],
                                          'variantKind': t['variantKind']})

json.dump(quests_out, open(os.path.join(DATA, 'quests.json'), 'w', encoding='utf-8'),
          indent=1, ensure_ascii=False)
print('quests:', len(quests_out))

# ---------- endemics ----------
endemics = []
for r in guide.get('animal', []):
    key = r.get('em')
    ed = enemydata.get(key or '', {})
    sp = SPECIES.get(ed.get('_Species')) if ed.get('_Species') else None
    locs = [STAGE_BIT[b] for b in bits(r['stageBit']) if b in STAGE_BIT]
    em, _, var = (key or 'EM?').partition('_')
    rec = {'em': em, 'variant': var or '00',
           'name': guid_text(ed.get('_EnemyName')), 'habitat': locs}
    if sp:
        rec['species'] = sp
    endemics.append(rec)
endemics.sort(key=lambda d: (d['name'] or '~', d['em']))
json.dump(endemics, open(os.path.join(DATA, 'endemics.json'), 'w', encoding='utf-8'),
          indent=1, ensure_ascii=False)
print('endemics:', len(endemics))

# ---------- monsters merge ----------
hab = {}
for tag in ('boss', 'zako', 'animal'):
    for r in guide.get(tag, []):
        if r.get('em'):
            hab[r['em']] = [STAGE_BIT[b] for b in bits(r['stageBit']) if b in STAGE_BIT]
reco = {}
spat = {}
for r in guide.get('boss', []):
    if not r.get('em'):
        continue
    reco[r['em']] = [WA_BY_ATTR.get(b, ATTR.get(b, str(b)))
                     for b in bits(r.get('recoAttr') or 0) if b]
    spat[r['em']] = [SP_BY_TYPE.get(b, f'#{b}')
                     for b in bits((r.get('spAtk') or [0])[0]) if b]
anatomy = {}
for r in guide.get('anatomy', []):
    if not r.get('em'):
        continue
    slots = []
    for s in r.get('slots', []):
        pname = part_names.get(str(s['partsType']))
        if pname:
            slots.append({'part': pname, 'breakType': s['breakType']})
    anatomy[r['em']] = slots

n_new = 0
for (em, var), m in by_em.items():
    key = f'{em}_{var}'
    ed = enemydata.get(key, {})
    if ed.get('_Species') is not None:
        m['species'] = {'id': ed['_Species'],
                        'name': SPECIES.get(ed['_Species'], str(ed['_Species']))}
    eco = monster_text.get(key, {})
    if eco:
        m['ecology'] = eco
    vn = {'frenzy': guid_text(ed.get('_EnemyFrenzyName')),
          'legendary': guid_text(ed.get('_EnemyLegendaryName')),
          'legendaryKing': guid_text(ed.get('_EnemyLegendaryKingName')),
          'extra': guid_text(ed.get('_EnemyExtraName'))}
    vn = {k: v for k, v in vn.items() if v}
    if vn:
        m['variantNames'] = vn
    if key in hab:
        m['habitat'] = hab[key]
    if key in reco and reco[key]:
        m['recoElements'] = reco[key]
    if key in spat and spat[key]:
        m['specialAttacks'] = spat[key]
    bt = bosstitles.get(key, [])
    if bt:
        m['titles'] = [{'count': _title_count(guide, t['freeInfo']), 'word': t['word']}
                       for t in bt]
    mq = mon_quests.get((em, var), [])
    if mq:
        seen = set()
        uniq = []
        for d in sorted(mq, key=lambda d: d['quest']):
            if d['quest'] not in seen:
                seen.add(d['quest'])
                uniq.append(d)
        m['quests'] = uniq
    ex = extra.get(key)
    if ex:
        for f in ('tempered', 'enrage', 'stamina', 'ride', 'sizeClass',
                  'breakRewards', 'partVitals', 'attacks'):
            if ex.get(f) is not None:
                m[f] = ex[f]
        n_new += 1
    sz = (sizedata.get('enemies') or {}).get(key)
    if sz:
        m['sizeTables'] = [
            {'legendary': LEG.get(s.get('legendary'), s.get('legendary')),
             'rewardRankL': _rr(s.get('rewardRankL')),
             'rewardRankU': _rr(s.get('rewardRankU')),
             'dist': (sizedata.get('tables') or {}).get(s.get('sizeTable'), [])}
            for s in sz]
    g = guilddata.get(key)
    if g:
        m['guild'] = g
    if ed:
        m['guideIcons'] = {'boss': ed.get('_BossIconType'), 'zako': ed.get('_ZakoIconType'),
                           'item': ed.get('_ItemIconType'), 'map': ed.get('_MapIconType'),
                           'animal': ed.get('_AnimalIconType'),
                           'color': ed.get('_IconColor'),
                           'legs': ed.get('_LegNum'),
                           'guideTarget': ed.get('_GuideTargetType')}
    if key in anatomy and m.get('partsBreak'):
        slots = [(norm_part(s['part']).rstrip('s'), s['breakType'])
                 for s in anatomy[key]]
        for pb in m['partsBreak']:
            np = norm_part(pb.get('part')).rstrip('s')
            hit = None
            for sp, bname in slots:
                if sp == np:
                    hit = bname
                    break
            if hit is None:
                for sp, bname in slots:
                    if sp and np and (sp in np or np in sp):
                        hit = bname
                        break
            if hit:
                pb['breakType'] = hit

json.dump(monsters, open(os.path.join(DATA, 'monsters.json'), 'w', encoding='utf-8'),
          indent=1, ensure_ascii=False)
print('monsters merged:', len(monsters), 'with extra:', n_new)

# ---------- guide meta ----------
meta = {
    'locales': [{'bit': b, 'name': n} for b, n in sorted(STAGE_BIT.items())],
    'venues': {str(k): v for k, v in VENUE.items()},
    'species': guide.get('species', []),
    'spAttackTypes': guide.get('spAttackTypes', []),
    'weaponAttributes': guide.get('weaponAttributes', []),
    'breakTypes': guide.get('breakTypes', {}),
    'questTypes': {str(k): v for k, v in QT.items()},
    'roles': {str(k): v for k, v in ROLE.items()},
    'legendary': {str(k): v for k, v in LEG.items()},
    'modelSizes': {str(k): v for k, v in MSZ.items()},
    'thresholds': thresholds,
}
json.dump(meta, open(os.path.join(DATA, 'guide_meta.json'), 'w', encoding='utf-8'),
          indent=1, ensure_ascii=False)
print('DONE finalize')
