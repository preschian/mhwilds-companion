"""Parse monster reward tables (Common/Enemy/EM*) + item catalog + break links.

Usage: python reward_all.py [EMXXXX]   (filter prints one monster; else summary)
Writes: rewards.json (raw per-monster tables), items.json (catalog).
"""
import json
import os
import struct
import sys

HERE = os.environ.get('MHRESEARCH', os.path.join(__import__('tempfile').gettempdir(), 'mhwilds-research'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dump_block import extract  # noqa: E402
from rsz_classscan import build_map  # noqa: E402
from rsz_read import parse_instances, resolve_refs  # noqa: E402

RROOT = os.path.join(HERE, 'extract_full', 'merged', 'natives', 'STM', 'GameDesign')
EROOT = os.path.join(HERE, 'extract_full', 'merged', 'natives', 'STM', 'GameDesign', 'Enemy')
LAYOUTS = os.path.join(HERE, 'layouts_reward.json')

CLASSES = [
    'app.user_data.EnemyRewardData',
    'app.user_data.EnemyRewardData.cData',
    'app.ItemDef.ID_Serializable',
    'app.EnemyReward.RewardType_Serializable',
    'app.RewardDef.REWARD_COMMON_LOT_TYPE_Serializable',
    'app.user_data.ItemData',
    'app.user_data.ItemData.cData',
    'app.user_data.EmParamPartsBreakReward',
    'app.user_data.EmParamPartsBreakReward.cPartsBreakData',
    'app.user_data.EmParamPartsBreakReward.cPartsBreakRewardSettingData',
    'app.cEmParamGuid_BreakParts',
    'app.user_data.EmParamHagitori',
]


def load_layouts():
    if os.path.exists(LAYOUTS):
        out = json.load(open(LAYOUTS, encoding='utf-8'))
    else:
        out = {}
        for n in CLASSES:
            block = extract(n)
            if block is None:
                print(f'LAYOUT MISSING: {n}')
                continue
            out[n] = json.loads('{' + block.rstrip().rstrip(',') + '}')[n].get('RSZ')
        json.dump(out, open(LAYOUTS, 'w', encoding='utf-8'))
        print(f'layouts cached: {len(out)} classes')
    # Reuse parts layouts (PARTS_TYPE) when present.
    pl = os.path.join(HERE, 'layouts_parts.json')
    if os.path.exists(pl):
        for k, v in json.load(open(pl, encoding='utf-8')).items():
            out.setdefault(k, v)
    return out


def parse_file(path, layouts, mmap):
    raw = open(path, 'rb').read()
    base = raw.find(b'RSZ\x00')
    _, _, n_obj, n_inst, _, _, inst_off, data_off, _ = struct.unpack_from('<IIIiIIQQQ', raw, base)
    eps = struct.unpack_from(f'<{n_obj}I', raw, base + 48)
    insts = [struct.unpack_from('<I', raw, base + inst_off + 8 * i)[0] for i in range(n_inst)]
    objs, end = parse_instances(raw, base, data_off, insts, layouts, mmap)
    assert end == len(raw), f'{path}: end 0x{end:X} != len 0x{len(raw):X}'
    return resolve_refs(objs, [objs[e] for e in eps])[0]


def main():
    filt = sys.argv[1].upper() if len(sys.argv) > 1 else None
    print('loading layouts + murmur map...', flush=True)
    layouts = load_layouts()
    mmap = build_map()
    enums = json.load(open(os.path.join(HERE, 'reward_enums.json'), encoding='utf-8')) \
        if os.path.exists(os.path.join(HERE, 'reward_enums.json')) else {}
    rw = {v: k for k, v in enums.get('app.EnemyReward.RewardType', {}).items()}
    lot = {v: k for k, v in enums.get('app.RewardDef.REWARD_COMMON_LOT_TYPE', {}).items()}
    items_txt = {e['name']: e['eng'] for e in
                 json.load(open(os.path.join(HERE, 'item_text.json'), encoding='utf-8'))}

    def iname(iid):
        return items_txt.get(f'Item_IT_{iid}', f'ITEM<{iid}>')

    # Item catalog.
    iroot = parse_file(os.path.join(RROOT, 'Common', 'Item', 'itemData.user.3'), layouts, mmap)
    catalog = {}
    for c in iroot['_Values']['_DataArray'] if isinstance(iroot.get('_Values'), dict) else iroot['_Values']:
        catalog[c['_ItemId']] = {'rare': c['_Rare'], 'type': c['_Type'], 'buy': c['_BuyPrice'],
                                 'sell': c['_SellPrice'], 'max': c['_MaxCount'],
                                 'name': iname(c['_ItemId'])}
    print(f'catalog items: {len(catalog)}')
    json.dump(catalog, open(os.path.join(HERE, 'items.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    # Per-monster reward files.
    emdir = os.path.join(RROOT, 'Common', 'Enemy')
    files = sorted(f for f in os.listdir(emdir) if f.startswith('EM') and f.endswith('.user.3'))
    allm = {}
    for fn in files:
        em = fn.split('_')[0] + '_' + fn.split('_')[1]
        if filt and not em.startswith(filt):
            continue
        root = parse_file(os.path.join(emdir, fn), layouts, mmap)
        vals = root['_Values']['_DataArray'] if isinstance(root.get('_Values'), dict) else root['_Values']
        entries = []
        for v in vals:
            ex = v.get('_IdEx') or []
            en = v.get('_RewardNumEx') or []
            ep = v.get('_probabilityEx') or []
            entries.append({
                'index': v.get('_Index'), 'dataId': v.get('_dataId'),
                'lot': lot.get(v.get('_lotType', {}).get('_Value'), v.get('_lotType', {}).get('_Value')),
                'rw': rw.get(v.get('_rewardType', {}).get('_Value'), v.get('_rewardType', {}).get('_Value')),
                'partsIndex': v.get('_partsIndex'),
                'story': {'item': iname(v.get('_IdStory', {}).get('_Value')),
                          'num': v.get('_RewardNumStory'), 'prob': v.get('_probabilityStory')},
                'ex': [{'item': iname(x.get('_Value')), 'num': n, 'prob': p}
                       for x, n, p in zip(ex, en, ep)],
            })
        allm[em] = entries
        print(f'== {em} ({fn}): {len(entries)} entries')
        for e in entries:
            exs = ', '.join(f"{x['item']} x{x['num']} {x['prob']}%" for x in e['ex'][:7])
            print(f"  idx={e['index']} data={e['dataId']} lot={e['lot']} rw={e['rw']} pIdx={e['partsIndex']}")
            print(f"    story: {e['story']['item']} x{e['story']['num']} {e['story']['prob']}%")
            print(f"    ex: {exs}")
    if not filt:
        json.dump(allm, open(os.path.join(HERE, 'rewards.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        print(f'wrote rewards.json ({len(allm)} monsters)')


if __name__ == '__main__':
    main()
