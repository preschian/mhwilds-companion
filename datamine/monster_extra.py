"""Monster extra data: text, globals, per-monster params -> research JSONs.

Reads extract_full/merged (Enemy/* + texts), extract_report/merged
(Common/Enemy/*, falls back to reward_merged), titles_merged.
Writes MHRESEARCH: monster_text.json, enemydata.json, questdata.json,
serial2em.json, guide_thresholds.json, bosstitles.json, sizedata.json,
extra.json. Downstream: mission_all.py, guide_all.py, guide_finalize.py.
"""
import glob
import json
import os
import re
import struct
import sys

HERE = os.environ.get('MHRESEARCH', os.path.join(__import__('tempfile').gettempdir(), 'mhwilds-research'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dump_block import extract, get_rsz  # noqa: E402
from rsz_classscan import build_map, instances_of  # noqa: E402
from rsz_read import parse_instances, resolve_refs  # noqa: E402
from msg_parse import parse as parse_msg  # noqa: E402

EROOT = os.path.join(HERE, 'extract_full', 'merged', 'natives', 'STM', 'GameDesign', 'Enemy')
_CANDS = [os.path.join(HERE, d, 'merged', 'natives', 'STM', 'GameDesign', 'Common', 'Enemy')
          for d in ('extract_report', 'reward_merged')]
CROOT = next((d for d in _CANDS if os.path.isdir(d)), _CANDS[0])
MROOT = os.path.join(HERE, 'mission_merged', 'natives', 'STM', 'GameDesign', 'Mission')
LAYOUTS = {}
MMAP = None
# Engine types with no il2cpp RSZ layout: fixed-size raw reads, proven by
# end==len across all files that contain them.
SYNTHETIC = {
    # U16 resource id + NUL-terminated path String (MsData [2]/[38] prove
    # the split: [38] sits at a 2-aligned slot with nchars right after).
    'via.Prefab': [{'potential_name': '_ResourceId', 'type': 'via.Prefab', 'code': 'U16',
                    'array': False, 'align': 2, 'size': '0x2'},
                   {'potential_name': '_Path', 'type': 'via.Prefab', 'code': 'String',
                    'array': False, 'align': 4, 'size': '0x8'}],
}


def enum_map(name):
    block = extract(name)
    obj = json.loads('{' + block.rstrip().rstrip(',') + '}')
    fields = obj[name].get('fields') or {}
    return {k: v.get('default') for k, v in fields.items()
            if isinstance(v, dict) and 'default' in v}


def auto_parse(path):
    """Parse any .user.3, building layouts for all classes found inside."""
    global MMAP
    if MMAP is None:
        print('building murmur map...', flush=True)
        MMAP = build_map()
    raw = open(path, 'rb').read()
    base = raw.find(b'RSZ\x00')
    assert base != -1, path
    _, _, n_obj, n_inst, n_ud, _, inst_off, data_off, ud_off = struct.unpack_from(
        '<IIIiIIQQQ', raw, base)
    eps = struct.unpack_from(f'<{n_obj}I', raw, base + 48)
    insts = [struct.unpack_from('<I', raw, base + inst_off + 8 * i)[0] for i in range(n_inst)]
    # Userdata table: n_ud entries of (instance_idx, class_hash, path_off).
    # Trailing table bytes can be garbage (EM0008 Legendary entry 2), so
    # validate: live instance index + in-file NUL-terminated path.
    external, udpaths = {}, []
    for i in range(n_ud):
        idx, _, po = struct.unpack_from('<III', raw, base + ud_off + 12 * i)
        if not (0 < idx < n_inst) or base + po + 2 > len(raw):
            continue
        s = raw[base + po:base + po + 400].decode('utf-16-le', 'ignore').split('\x00')[0]
        if not s or '/' not in s:
            continue
        external[idx] = s
        udpaths.append(s)
    names = {MMAP.get(h) for h, _ in
             [struct.unpack_from('<II', raw, base + inst_off + 8 * i) for i in range(n_inst)]}
    names.discard(None)
    for n in names:
        if n not in LAYOUTS:
            lay = get_rsz(n)
            if lay is None:
                if n in SYNTHETIC:
                    LAYOUTS[n] = SYNTHETIC[n]
                    continue
                print(f'  LAYOUT MISSING: {n} ({os.path.basename(path)})')
                continue
            LAYOUTS[n] = lay
    from rsz_read import validate_refs

    def fail_idx(e):
        m = re.search(r'inst\[(\d+)\]', str(e))
        return int(m.group(1)) if m else -1

    def attempt(skipset, holder=False):
        o, e = parse_instances(raw, base, data_off, insts, LAYOUTS, MMAP,
                               external=external, skip_extra=skipset,
                               skip_holder_guid=holder)
        if e != len(raw):
            raise AssertionError(f'end 0x{e:X} != len 0x{len(raw):X}')
        bad = validate_refs(o, insts, LAYOUTS, MMAP)
        if bad:
            raise ValueError(f'$ref mismatches: {bad[:4]}')
        return o, e

    # Pass 1: plain parse. Small trailing tail (appended patch field,
    # EM1150 Basic +12B) is kept visible instead of failing the file.
    first_err = None
    try:
        objs, end = parse_instances(raw, base, data_off, insts, LAYOUTS, MMAP,
                                    external=external)
    except ValueError as e:
        if str(e).startswith(('no layout', 'unknown instance hash')):
            raise
        first_err = e
        objs = end = None
    if objs is not None and (end == len(raw) or 0 < len(raw) - end <= 16):
        if end != len(raw):
            print(f'  TRAILING {len(raw) - end}B: {os.path.basename(path)}')
        bad = validate_refs(objs, insts, LAYOUTS, MMAP)
        if bad:
            print('  WARN $ref: %s: %s' % (os.path.basename(path), bad[:4]))
    else:
        # Pass 2: elided instances (zero bytes, no table marker — Ms001130:
        # 30/86/88). Elisions surface downstream (garbage passes local
        # checks, explodes later), so failure-anchored windows MISS
        # (Ms001030 needs {30,35,97,98}). Enumerate subsets of inline
        # elidable-class instances instead (complete for the known
        # pattern); adopt ONLY full success (end==len + $ref-clean).
        from itertools import combinations
        ELIDABLE = {'EnemyLayoutDataBossZako', 'QuestData', 'CameraWorkData',
                    'CameraAttachParam', 'RailCameraDataList', 'Prefab'}
        univ = [i for i in range(n_inst)
                if insts[i] != 0 and i not in eps and i not in external
                and (MMAP.get(insts[i]) or '').split('.')[-1] in ELIDABLE]
        found = None
        n_try = [0]

        def attempt_any(skipset):
            n_try[0] += 1
            if n_try[0] > 300:
                return None
            try:
                return attempt(set(skipset))
            except (ValueError, AssertionError):
                return None

        for k in range(0, min(len(univ), 5) + 1):
            if found is not None:
                break
            for combo in combinations(univ, k):
                r = attempt_any(combo)
                if r is not None:
                    found = (r[0], r[1], set(combo))
                    break
        if found is not None:
            objs, end, skips = found
            who = ['%d:%s' % (i, (MMAP.get(insts[i]) or '?').split('.')[-1])
                   for i in sorted(skips)]
            print(f'  ELIDED {who}: {os.path.basename(path)}')
            root = resolve_refs(objs, [objs[e] for e in eps])[0]
            return root
        # Fallback: failure-anchored window DFS for elisions of unknown
        # classes (never observed; loud if it fires meaningfully).
        tried = set()
        budget = [200]

        def dfs(skipset):
            key = frozenset(skipset)
            # Cap 5: elisions are rare (Ms001030 has 5); deeper "successes"
            # are spurious (Em0161 "validated" 7 skips with garbage data).
            if key in tried or len(skipset) > 5 or budget[0] <= 0:
                return None
            tried.add(key)
            budget[0] -= 1
            try:
                o, e = attempt(set(skipset))
                return o, e, set(skipset)
            except (ValueError, AssertionError) as ex:
                cur = fail_idx(ex)
            cands = [c for c in range(cur, max(cur - 6, -1), -1)
                     if c not in eps and c not in skipset and c >= 0
                     and insts[c] != 0 and c not in external]
            cands.sort(key=lambda c: (
                0 if (MMAP.get(insts[c]) or '').split('.')[-1] in ELIDABLE else 1,
                cur - c))
            for c in cands:
                r = dfs(skipset | {c})
                if r is not None:
                    return r
            return None

        r = dfs(set())
        if r is None:
            if budget[0] <= 0:
                raise ValueError(f'{path}: backtracking budget exhausted')
            # Older patches omit cActionIDHolder._ExportGuid; one retry.
            o, e = attempt(set(), holder=True)
            r = (o, e, set())
        objs, end, skips = r
        who = ['%d:%s' % (i, (MMAP.get(insts[i]) or '?').split('.')[-1]) for i in sorted(skips)]
        print(f'  ELIDED {who}: {os.path.basename(path)}')
    if end != len(raw):
        # (Pass 1 already printed TRAILING; pass 2 requires exact end.)
        if end > len(raw) or len(raw) - end > 16:
            raise AssertionError(f'{path}: end 0x{end:X} != len 0x{len(raw):X}')
    root = resolve_refs(objs, [objs[e] for e in eps])[0]
    if end != len(raw):
        root['_Trailing'] = raw[end:len(raw)].hex()
    return root


def clean(s):
    if not s:
        return None
    s = s.replace('\r\n\r\n', '\n\n').replace('\r\n', ' ').strip()
    return s or None


def em_of(eid, idmap):
    """EnemyDef.ID value -> (EMxxxx, variant)."""
    name = idmap.get(eid)
    if not name:
        return None, None
    m = re.match(r'EM(\d+)_(\d+)_\d+', name)
    return (f'EM{m.group(1)}', m.group(2)) if m else (None, None)


def _slim_edata(c):
    """EnemyData row -> serials, species, text guids, icons (no $type)."""
    keep = {'_Index', '_enemyId', '_Species', '_JpEnemyName', '_EnemyName',
            '_EnemyExp', '_EnemyExtraName', '_EnemyBossExp', '_EnemyFrenzyName',
            '_EnemyLegendaryName', '_EnemyLegendaryKingName', '_EnemyFeatures',
            '_EnemyTips', '_FirstCapture', '_Memo', '_Grammar', '_BossIconType',
            '_ZakoIconType', '_ItemIconType', '_MapIconType', '_AnimalIconType',
            '_IconColor', '_IsMapDraw', '_OtomoPick', '_AdvisorPick',
            '_NpcPartnerPick', '_CategoryForNPC', '_MapFilteringType',
            '_GuideTargetType', '_AnimationType', '_FeatureType', '_LegNum'}
    return {k: v for k, v in c.items() if k in keep}


def _slim_qdata(c):
    keep = {k for k in c if not k.startswith('$')
            and not isinstance(c[k], (dict, list))}
    return {k: c[k] for k in sorted(keep)}


def _slim_size(r, em_idx):
    """EmCommonRandomSize -> {tables: guid -> [{scale, prob}], enemies: em -> [...]}."""
    out = {'tables': {}, 'enemies': {}}
    arr = r.get('_RandomSizeTblArray') or {}
    for t in (arr.get('_DataArray') or []):
        if not isinstance(t, dict):
            continue
        out['tables'][t.get('_InstanceGuid')] = [
            {'scale': p.get('_Scale'), 'prob': p.get('_Prob')}
            for p in (t.get('_ProbDataTbl') or [])]
    for e in (r.get('_EnemyRandomSizeTblArray') or []):
        if not isinstance(e, dict):
            continue
        k = em_idx.get(e.get('_EmId'))
        key = f'{k[0]}_{k[1]}' if k else str(e.get('_EmId'))
        rows = []
        for s in (e.get('_SizeTable') or []):
            if not isinstance(s, dict):
                continue
            rows.append({
                'legendary': e.get('_LegendaryId'),
                'rewardRankL': (s.get('_RewardRank_L') or {}).get('_Value'),
                'rewardRankU': (s.get('_RewardRank_U') or {}).get('_Value'),
                'sizeTable': (s.get('_SizeTableId') or {}).get('Value'),
                'sizeTable2': (s.get('_SizeTableId2') or {}).get('Value'),
            })
        out['enemies'][key] = rows
    return out


if __name__ == '__main__':


    print('== enums')
    IDMAP = {v: k for k, v in enum_map('app.EnemyDef.ID').items()}
    SIZE_NAMES = {v: k for k, v in enum_map('app.EnemyDef.MODEL_SIZE').items()}
    CNAMES = {v: k for k, v in enum_map('app.ColorPreset.TYPE').items()}

    print('== text')
    txt = {}
    for e in json.load(open(os.path.join(HERE, 'enemy_text_merged.json'), encoding='utf-8')):
        m = re.match(r'EnemyText_([A-Z_]+)_EM(\d+)_(\d+)', e.get('name', ''))
        if m:
            txt.setdefault((m.group(2), m.group(3)), {})[m.group(1)] = clean(e.get('eng'))
    TEXT_KEYS = {'EXP': 'exp', 'FEATURES': 'features', 'TIPS': 'tips', 'MEMO': 'memo',
                 'FIRST_CAPTURE': 'firstCapture', 'BOSS_EXP': 'bossExp'}
    slim_txt = {}
    for (em, var), kv in txt.items():
        d = slim_txt.setdefault(f'EM{em}_{var}', {})
        for k, v in kv.items():
            if k in TEXT_KEYS and v:
                d[TEXT_KEYS[k]] = v
    json.dump(slim_txt, open(os.path.join(HERE, 'monster_text.json'), 'w', encoding='utf-8'),
              indent=1, ensure_ascii=False)
    print('monster_text entries:', len(slim_txt))

    print('== globals')
    GUID_EM = {}
    _r = parse_msg(glob.glob(os.path.join(HERE, 'extract_full', 'merged', 'natives', 'STM',
                                          'GameDesign', 'Text', 'Excel_Data', 'EnemyText.msg.23'))[0])
    try:
        _eng = _r['langs'].index(1)
    except ValueError:
        _eng = 1
    _guid_full = {}
    for e in _r['entries']:
        _guid_full[e['guid']] = {'name': e['name'],
                                 'eng': e['refs'][_eng] if _eng < len(e['refs']) else ''}
        m = re.match(r'EnemyText_NAME_EM(\d+)_(\d+)', e['name'])
        if m:
            GUID_EM[e['guid']] = (f'EM{m.group(1)}', m.group(2))
    json.dump(_guid_full, open(os.path.join(HERE, 'enemy_guid.json'), 'w', encoding='utf-8'),
              indent=1, ensure_ascii=False)
    print('guid map:', len(GUID_EM))


    def edata_rows(fn):
        r = auto_parse(os.path.join(CROOT, fn))
        vals = r['_Values']['_DataArray'] if isinstance(r.get('_Values'), dict) else r['_Values']
        return [v for v in vals if v is not None]


    EDATA = {}
    for c in edata_rows('EnemyData.user.3'):
        k = GUID_EM.get((c['_EnemyName'] or '').lower())
        if k:
            EDATA[k] = c
    print('enemydata rows:', len(EDATA))
    QDATA = {}
    _idx_em = {}
    for k, c in EDATA.items():
        _idx_em[c['_Index']] = k
    _em_idx = {}
    for k, c in EDATA.items():
        _em_idx[c['_enemyId']] = k
    _bad = 0
    for c in edata_rows('EnemyQuestData.user.3'):
        k = _idx_em.get(c['_Index'])
        if k:
            QDATA[k] = c
            if EDATA[k]['_enemyId'] != c['_enemyId']:
                _bad += 1
    print('questdata rows:', len(QDATA), 'index/id mismatches:', _bad)
    json.dump({f'{k[0]}_{k[1]}': _slim_edata(c) for k, c in EDATA.items()},
              open(os.path.join(HERE, 'enemydata.json'), 'w'), indent=1)
    json.dump({f'{k[0]}_{k[1]}': _slim_qdata(c) for k, c in QDATA.items()},
              open(os.path.join(HERE, 'questdata.json'), 'w'), indent=1)
    json.dump({str(s): f'{k[0]}_{k[1]}' for s, k in _em_idx.items()},
              open(os.path.join(HERE, 'serial2em.json'), 'w'), indent=1)

    print('== thresholds')
    th = {}
    for fn in ['EnemyReportMeatThresholdData.user.3', 'EnemyReportMeatElementThresholdData.user.3',
               'EnemyReportDropThresholdData.user.3']:
        p = os.path.join(CROOT, fn)
        if not os.path.exists(p):
            print(fn, 'MISSING')
            continue
        r = auto_parse(p)
        vals = r['_Values']['_DataArray'] if isinstance(r.get('_Values'), dict) else r['_Values']
        vals = [v for v in vals if v is not None]
        vkey = '_DropValue' if 'Drop' in fn else '_MeatValue'
        th[fn] = [{'index': v['_Index'], 'step': v['_StepIndex'], 'value': v[vkey]} for v in vals]
        print(fn, th[fn])
    json.dump(th, open(os.path.join(HERE, 'guide_thresholds.json'), 'w'), indent=1)

    print('== titles')
    tw = {}
    twmsg = glob.glob(os.path.join(HERE, 'titles_merged', '**/Title_Word.msg.23'), recursive=True)
    if twmsg:
        _r = parse_msg(twmsg[0])
        try:
            eng = _r['langs'].index(1)
        except ValueError:
            eng = 1
        slim = [{'name': e['name'], 'eng': e['refs'][eng], 'crc': e['crc'], 'hash': e['hash']}
                for e in _r['entries']]
        json.dump(slim, open(os.path.join(HERE, 'title_word.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        for e in slim:
            tw[e['name']] = clean(e.get('eng'))
        print('title words:', len(tw), 'sample:', list(tw.items())[:3])

    print('== boss titles')
    BT = {}
    for c in edata_rows('EnemyReportBossTitleData.user.3'):
        k = _em_idx.get(c['_EmID'])
        if k:
            BT.setdefault(f'{k[0]}_{k[1]}', []).append(
                {'titleId': c['_TitleID'],
                 'word': tw.get(f"Title_Word_NAME_{c['_TitleID']}"),
                 'freeInfo': c.get('_FreeInfo')})
    json.dump(BT, open(os.path.join(HERE, 'bosstitles.json'), 'w', encoding='utf-8'),
              indent=1, ensure_ascii=False)
    print('titled monsters:', sum(1 for v in BT.values() if any(t['word'] for t in v)),
          '/', len(BT))

    print('== size tables')
    SZ = glob.glob(os.path.join(EROOT, 'CommonData', 'Data', 'EmCommonRandomSize.user.3'))
    if SZ:
        r = auto_parse(SZ[0])
        size = _slim_size(r, _em_idx)
        json.dump(size, open(os.path.join(HERE, 'sizedata.json'), 'w'), indent=1)
        print('size tables:', len(size.get('tables', {})),
              'enemy tables:', len(size.get('enemies', {})))

    print('== per-monster params')
    PNAMES = json.load(open(os.path.join(HERE, 'part_names.json'), encoding='utf-8'))
    ROLE = {v: k for k, v in enum_map('app.EnemyDef.ROLE_ID').items()}
    LEG = {v: k for k, v in enum_map('app.EnemyDef.LEGENDARY_ID').items()}
    STAGE = {v: k for k, v in enum_map('app.FieldDef.STAGE').items()}
    COND = {0: 'NONE', 1: 'EITHER', 2: 'ALL'}


    def scalars(o, skip=('$type',)):
        if not isinstance(o, dict):
            return None
        return {k: v for k, v in o.items()
                if k not in skip and v is not None and not isinstance(v, (dict, list))}


    def ser(o):
        if isinstance(o, dict):
            return o.get('_Value', o)
        return o


    EXTRA = {}
    FAILS = []
    ems = sorted(d for d in os.listdir(EROOT)
                 if re.match(r'Em\d+$', d) and os.path.isdir(os.path.join(EROOT, d)))
    print('em dirs:', len(ems))
    for emd in ems:
        em = emd.upper()
        for var in sorted(os.listdir(os.path.join(EROOT, emd))):
            dd = os.path.join(EROOT, emd, var, 'Data')
            if not os.path.isdir(dd):
                continue
            key = (em, var)
            ex = EXTRA.setdefault(key, {})
            pre = f'{emd}_{var}_'
            try:
                r = auto_parse(os.path.join(dd, pre + 'Param_Legendary.user.3'))
                tiers = {}
                for t, suf in (('normal', ''), ('king', '_King'), ('hard', '_Hard')):
                    tiers[t] = {k: v for k, v in scalars(r).items()
                                if (suf and k.endswith(suf)) or (not suf and not k.endswith(('_King', '_Hard')))}
                ex['tempered'] = tiers
            except FileNotFoundError:
                pass
            except Exception as e:
                FAILS.append((key, str(e)[:100]))
            try:
                r = auto_parse(os.path.join(dd, pre + 'Param_Angry.user.3'))
                ex['enrage'] = {'lower': scalars(r['_DataLvLower']), 'upper': scalars(r['_DataLvUpper']),
                                'rateLevels': r.get('_AngryRateLevelArray')}
            except FileNotFoundError:
                pass
            except Exception as e:
                FAILS.append((key, str(e)[:100]))
            try:
                r = auto_parse(os.path.join(dd, pre + 'Param_Stamina.user.3'))
                ex['stamina'] = {'lower': scalars(r['_DataLvLower']), 'upper': scalars(r['_DataLvUpper'])}
            except FileNotFoundError:
                pass
            except Exception as e:
                FAILS.append((key, str(e)[:100]))
            try:
                r = auto_parse(os.path.join(dd, pre + 'Param_Ride.user.3'))
                ex['ride'] = {'successVital': r.get('_SuccessVital')}
            except FileNotFoundError:
                pass
            except Exception as e:
                FAILS.append((key, str(e)[:100]))
            try:
                r = auto_parse(os.path.join(dd, pre + 'Param_Basic.user.3'))
                ms = r.get('_ModelSize')
                ex['sizeClass'] = SIZE_NAMES.get(ms, ms)
            except FileNotFoundError:
                pass
            except Exception as e:
                FAILS.append((key, str(e)[:100]))
            try:
                r = auto_parse(os.path.join(dd, pre + 'Param_PartsBreakReward.user.3'))
                ex['breakRewards'] = [
                    {'name': b.get('RewardName'), 'part': PNAMES.get(str(ser(b.get('PartsType')))),
                     'condition': COND.get(b.get('RewardCondition'), b.get('RewardCondition')),
                     'tableIndex': b.get('RewardTableIndex'), 'takeMax': b.get('RewardTakeMaxNum'),
                     'breakData': b.get('PartsBreakData')}
                    for b in r['_PartsBreakArray']]
            except FileNotFoundError:
                pass
            except Exception as e:
                FAILS.append((key, str(e)[:100]))
            # Part vitals: re-parse Param_Parts cParts.
            pp = glob.glob(os.path.join(dd, '*_Param_Parts.user.3'))
            if pp:
                try:
                    r = auto_parse(pp[0])
                    parr = r['_PartsArray']
                    parr = parr['_DataArray'] if isinstance(parr, dict) else parr
                    ex['partVitals'] = [
                        {'part': PNAMES.get(str(ser(p.get('_PartsType')))),
                         'vitals': [scalars(v) for v in (p.get('_Vital') or [])]}
                        for p in parr]
                except Exception as e:
                    print('vital fail', key, e)
            # Shell attack catalog from filenames.
            sh = glob.glob(os.path.join(EROOT, emd, var, 'Shell', '*MainParam.user.3'))
            if sh:
                names = set()
                for s in sh:
                    b = os.path.basename(s)
                    b = re.sub(r'^Em\d+_\d+_?i?', '', b, flags=re.I)
                    b = b.replace('MainParam.user.3', '')
                    names.add(b)
                ex['attacks'] = sorted(names)
    print('extra keys:', len(EXTRA), 'failures:', len(FAILS))
    for f in FAILS[:20]:
        print('  FAIL:', f)
    print('sample Rathian:', json.dumps(EXTRA.get(('EM0001', '00')), ensure_ascii=False)[:800])
    json.dump({f'{k[0]}_{k[1]}': v for k, v in EXTRA.items()},
              open(os.path.join(HERE, 'extra.json'), 'w'), indent=1, default=str)
    json.dump(FAILS, open(os.path.join(HERE, 'extra_fails.json'), 'w'), indent=1, default=str)

    print('== DONE (part 2b)')



