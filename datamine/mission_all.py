"""Parse all MsData + BossZakoLayout + QuestData -> mission_index.json.

Reads mission_merged + extract_quest (+ serial2em.json from monster_extra).
Writes MHRESEARCH/mission_index.json.
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

MROOT = os.path.join(HERE, 'mission_merged', 'natives', 'STM', 'GameDesign', 'Mission')
QROOT = os.path.join(HERE, 'extract_quest', 'merged', 'natives', 'STM', 'GameDesign', 'Mission')


def sval(o):
    if isinstance(o, dict):
        return o.get('_Value', o.get('Value', o))
    return o


def _em_pair(name):
    if not name:
        return None
    m = re.match(r'EM(\d+)_(\d+)', name)
    return [f'EM{m.group(1)}', m.group(2)] if m else None


IDMAP = {v: k for k, v in mx.enum_map('app.EnemyDef.ID').items()}
IDFIX = {v: k for k, v in mx.enum_map('app.EnemyDef.ID_Fixed').items()}
ROLE = {v: k for k, v in mx.enum_map('app.EnemyDef.ROLE_ID').items()}
LEG = {v: k for k, v in mx.enum_map('app.EnemyDef.LEGENDARY_ID').items()}
try:
    SERIAL2EM = json.load(open(os.path.join(HERE, 'serial2em.json'), encoding='utf-8'))
except FileNotFoundError:
    SERIAL2EM = {}


def em_of_idfixed(v):
    """Fixed serial (EnemyData) -> [EMxxxx, variant]; enum fallback."""
    name = SERIAL2EM.get(str(v)) or IDFIX.get(v) or IDMAP.get(v)
    return _em_pair(name)


quests = {}
fails = []
msfiles = sorted(glob.glob(os.path.join(MROOT, 'Mission*', '*MsData.user.3')))
print('msdata:', len(msfiles))
for p in msfiles:
    mid = os.path.basename(os.path.dirname(p)).replace('Mission', '')
    q = {'id': mid}
    try:
        r = mx.auto_parse(p)
    except Exception as e:
        fails.append((mid, 'msdata: ' + str(e)[:120]))
        continue
    q['missionId'] = sval(r.get('_MissionIDSerial'))
    q['type'] = sval(r.get('_MissionTypeSerial'))
    q['fieldStage'] = sval(r.get('_BeaconSetStage'))
    q['openHR'] = r.get('_OpenFlagHunterRank')
    emsets = []
    for e in r.get('_EmSetDataList') or []:
        b = e.get('_EmSet_BossZako') or {}
        emsets.append({'stage': sval(e.get('_Stage')),
                       'layout': b.get('$external'),
                       'tagField': sval((e.get('_EmSet_AnimalTag') or {}).get('_FieldID')),
                       'tagValue': (e.get('_EmSet_AnimalTag') or {}).get('_Value')})
    q['emSets'] = emsets
    q['env'] = [{'stage': sval(x.get('_StageType')), 'env': sval(x.get('_EnvType')),
                 'fixed': x.get('_IsFixEnv')}
                for x in (r.get('_SetEnvironmentDataList') or [])]
    qd = r.get('_QuestData')
    # Quest params live in _Quest/Ms<MID>_QuestData.user.3, linked either by
    # userdata ref (001030) or pure convention (109000: _QuestData elided).
    qpaths = []
    if isinstance(qd, dict) and qd.get('$external'):
        qpaths.append(qd['$external'].replace('GameDesign/Mission/', '') + '.3')
    qpaths.append(f'Mission{mid}/_Quest/Ms{mid}_QuestData.user.3')
    qp = None
    for rel in qpaths:
        for root in (QROOT, MROOT):
            if os.path.exists(os.path.join(root, rel)):
                qp = os.path.join(root, rel)
                break
        if qp:
            break
    if qp:
        try:
            qr = mx.auto_parse(qp)
        except Exception as e:
            fails.append((mid, 'questdata: ' + str(e)[:120]))
            qr = None
        if qr is not None:
            cc = qr.get('_ClearCondition') or {}
            q['quest'] = {
                'lv': qr.get('_QuestLv'), 'type': qr.get('_QuestType'),
                'time': qr.get('_TimeLimit'), 'faints': qr.get('_QuestLife'),
                'money': qr.get('_RemMoney'), 'hr': qr.get('_HRPoint'),
                'orderHR': (qr.get('_OrderCondition') or {}).get('_OrderHR'),
                'stage': sval(qr.get('_Stage')),
                'targetType': cc.get('_TargetType'),
                # _EmTargetID here is a layout slot (101-105), NOT an EmID:
                # quest->monster links come from BossZako mains instead.
                'targets': [({'slot': sval(t.get('_EmTargetID')),
                              'role': ROLE.get(t.get('_RoleID')),
                              'legendary': LEG.get(t.get('_LegendaryID'))})
                           for t in (cc.get('_TargetInfoArray') or [])],
                'subs': [({'slot': sval(s.get('_EmTargetID')),
                           'role': ROLE.get(s.get('_RoleID')),
                           'legendary': LEG.get(s.get('_LegendaryID'))})
                        for s in (qr.get('_SubBossInfoArray') or [])],
                'titleGuid': (qr.get('_QuestMsg') or {}).get('_TitleMsg'),
            }
    # BossZako targets (main)
    seen_layouts = {e['layout'] for e in emsets if e['layout']}
    mains = []
    for lp in seen_layouts:
        fp = os.path.join(MROOT, lp.replace('GameDesign/Mission/', '') + '.3')
        if not os.path.exists(fp):
            fails.append((mid, 'missing layout ' + lp))
            continue
        try:
            lr = mx.auto_parse(fp)
        except Exception as e:
            fails.append((mid, 'layout: ' + str(e)[:120]))
            continue
        for t in lr.get('_MainTargetDataList') or []:
            mains.append({'raw': t.get('_EmID'), 'layout': lp,
                          'em': em_of_idfixed(t.get('_EmID')),
                          'role': ROLE.get(t.get('_RoleID')),
                          'legendary': LEG.get(t.get('_LegendaryID')),
                          'area': t.get('_SetAreaNo'),
                          'fixedSize': t.get('_FixedSize'),
                          'randomSize': t.get('_IsUseRandomSize')})
    q['mains'] = mains
    quests[mid] = q

json.dump(quests, open(os.path.join(HERE, 'mission_index.json'), 'w'), indent=1)
print('quests:', len(quests), 'fails:', len(fails))
for f in fails[:30]:
    print('  FAIL:', f)
# Distinct-value survey for stage/field anchors
from collections import Counter
print('fieldStage:', Counter(str(q.get('fieldStage')) for q in quests.values()).most_common(12))
print('emset stage:', Counter(str(e['stage']) for q in quests.values() for e in q['emSets']).most_common(12))
print('tagField:', Counter(str(e['tagField']) for q in quests.values() for e in q['emSets']).most_common(12))
print('quest stage:', Counter(str((q.get('quest') or {}).get('stage')) for q in quests.values()).most_common(12))
print('quest type:', Counter(str((q.get('quest') or {}).get('type')) for q in quests.values()).most_common(12))
print('quest lv:', Counter(str((q.get('quest') or {}).get('lv')) for q in quests.values()).most_common(12))
print('DONE missions')
