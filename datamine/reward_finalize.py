"""Finalize materials dataset v2: lottery-grouped reward tables + item catalog.

Lottery model (verified vs wiki oracles):
  100s body carve | 200s tail carve | 300s breaks (per-part pIdx, or one
  shared pool when pIdx=-1) | 400s wound | 500s target (one table per roll)
  | 110/120/150/210s field drops by tens | 600s bonus | 800/900s gather.
Usage: python reward_finalize.py
"""
import json
import os
import sys

HERE = os.environ.get('MHRESEARCH', os.path.join(__import__('tempfile').gettempdir(), 'mhwilds-research'))
REPO = os.environ.get('MHREPO', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reward_all import parse_file, load_layouts  # noqa: E402
from rsz_classscan import build_map  # noqa: E402

RROOT = os.path.join(HERE, 'extract_full', 'merged', 'natives', 'STM', 'GameDesign')
EROOT = os.path.join(HERE, 'extract_full', 'merged', 'natives', 'STM', 'GameDesign', 'Enemy')
EMPTY_ITEM = 'ITEM<0>'


# Head rw codes: RW008=body carve, RW016=tail carve, RW002/RW003/RW011=breaks,
# RW003=wound, RW012=target, 911862272/906321792=drops, negatives=special.
CARVE_HEAD, TAIL_HEAD = 'RW008', 'RW016'


def bucket(data_id, head_rw):
    h, t = (data_id or 0) // 100, (data_id or 0) // 10
    if t == 10:
        return 'carve_body' if head_rw == CARVE_HEAD else 'drops'
    if t == 20:
        return 'carve_tail' if head_rw == TAIL_HEAD else 'drops'
    if h == 1 or h == 2:
        return 'drops'
    return {3: 'break', 4: 'wound', 5: 'target', 6: 'bonus',
            8: 'gather', 9: 'gather'}.get(h, 'drops')


def main():
    layouts = load_layouts()
    mmap = build_map()
    pnames = json.load(open(os.path.join(HERE, 'part_names.json'), encoding='utf-8'))
    catalog = json.load(open(os.path.join(HERE, 'items.json'), encoding='utf-8'))
    iexp = {e['name']: e['eng'] for e in
            json.load(open(os.path.join(HERE, 'item_text.json'), encoding='utf-8'))}

    def desc(iid):
        raw = iexp.get(f'Item_IT_EXP_{iid}')
        if not raw:
            return None
        return raw.replace('\r\n\r\n', '\n\n').replace('\r\n', ' ').strip()

    mats = [{'id': int(iid), 'name': c['name'], 'rarity': c['rare'], 'type': c['type'],
             'buy': c['buy'], 'sell': c['sell'], 'max': c['max'], 'desc': desc(iid)}
            for iid, c in sorted(catalog.items(), key=lambda kv: int(kv[0]))]
    json.dump(mats, open(os.path.join(REPO, 'data', 'materials.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'materials.json: {len(mats)} items')

    monsters = json.load(open(os.path.join(REPO, 'data', 'monsters.json'), encoding='utf-8'))
    rewards = json.load(open(os.path.join(HERE, 'rewards.json'), encoding='utf-8'))
    n_tables = 0
    for m in monsters:
        key = f"{m['em']}_{m['variant']}"
        src = m.get('sharedFrom', key)
        entries = rewards.get(key) or rewards.get(src) or []
        em_dir, var = src.split('_')[0].title(), src.split('_')[1]
        # Break part map + carve count from per-monster files.
        breaks, carve_count = {}, None
        bp = os.path.join(EROOT, em_dir, var, 'Data',
                           f'{em_dir}_{var}_Param_PartsBreakReward.user.3')
        if os.path.exists(bp):
            root = parse_file(bp, layouts, mmap)
            arr = root['_PartsBreakArray']
            arr = arr['_DataArray'] if isinstance(arr, dict) else arr
            for s in arr:
                pt = (s.get('PartsType') or {}).get('_Value')
                breaks[s.get('RewardTableIndex')] = pnames.get(str(pt), f'PART<{pt}>')
        hp = os.path.join(EROOT, em_dir, var, 'Data', f'{em_dir}_{var}_Param_Hagitori.user.3')
        if os.path.exists(hp):
            carve_count = parse_file(hp, layouts, mmap).get('HagitoriNum')

        # Group entries into lottery tables (head line decides category).
        pre = {}
        for e in entries:
            d = e['dataId']
            h = (d or 0) // 100
            if h == 3:
                gkey = ('break', e['partsIndex'])
            elif h == 5:
                gkey = ('target', d)
            elif h in (1, 2):
                gkey = ('tens', d // 10)
            else:
                gkey = (h, None)
            pre.setdefault(gkey, []).append(e)
        groups = {}
        for gkey, lines in pre.items():
            lines.sort(key=lambda e: e['dataId'])
            head = lines[0]
            cat = bucket(head['dataId'], head['rw'])
            if cat == 'drops' and head['dataId'] // 10 in (10, 20):
                print(f'  note {key}: tens-{head["dataId"] // 10} as drops (head {head["rw"]})')
            groups[(cat, gkey[1])] = lines

        tables = []
        for (cat, sub), lines in sorted(groups.items(), key=lambda kv: min(e['dataId'] for e in kv[1])):
            lines.sort(key=lambda e: e['dataId'])
            data_ids = sorted({e['dataId'] for e in lines})
            part = None
            if cat == 'break':
                part = breaks.get(sub) if sub is not None and sub >= 0 else None
                if sub is not None and sub < 0:
                    part = sorted(set(breaks.values())) or None
            high, low = [], []
            for e in lines:
                st = e['story']
                if st['item'] not in (EMPTY_ITEM, '---'):
                    low.append({'item': st['item'], 'num': st['num'], 'prob': st['prob'],
                                'dataId': e['dataId']})
                xs = [x for x in e['ex'] if x['item'] not in (EMPTY_ITEM, '---')]
                if xs:
                    prim = dict(xs[0])
                    prim['dataId'] = e['dataId']
                    if len(xs) > 1:
                        prim['alts'] = xs[1:]
                    high.append(prim)
            if high or low:
                t = {'category': cat, 'dataIds': data_ids, 'high': high, 'low': low}
                if cat == 'break':
                    t['part'] = part
                if cat == 'target':
                    t['roll'] = data_ids[0] - 500 + 1
                tables.append(t)
                n_tables += 1
        # Preserve existing non-reward fields; replace rewards block.
        m['rewards'] = {'carveCount': carve_count, 'tables': tables}
    _check_oracle(monsters)
    json.dump(monsters, open(os.path.join(REPO, 'data', 'monsters.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'monsters.json extended: {len(monsters)} entries, {n_tables} reward tables')


def _check_oracle(monsters):
    """Rathian tables must match the wiki oracle (Fextralife/GameRant)."""
    rath = next(m for m in monsters if m['name'] == 'Rathian')
    tabs = {}
    for t in rath['rewards']['tables']:
        tabs.setdefault(t['category'], []).append(t)

    def items(t):
        return [(x['item'], x['prob']) for x in t['high']]

    assert len(tabs['carve_body']) == 1
    assert items(tabs['carve_body'][0]) == [
        ('Rathian Scale+', 30), ('Rathian Carapace', 23), ('Rathian Webbing', 18),
        ('Rathian Spike+', 13), ('Rath Medulla', 11), ('Rathian Ruby', 5)]
    assert items(tabs['carve_tail'][0]) == [
        ('Rathian Spike+', 80), ('Rath Medulla', 13), ('Rathian Ruby', 7)]
    br = {t.get('part'): items(t) for t in tabs['break']}
    assert br['Left Wing'] == [('Rathian Webbing', 100)]
    assert br['Right Wing'] == [('Rathian Webbing', 100)]
    assert items(tabs['wound'][0]) == [
        ('Rathian Scale+', 50), ('Rathian Carapace', 42), ('Rathian Spike+', 8)]
    tg = sorted(tabs['target'], key=lambda t: t['roll'])
    assert [t['high'][0]['item'] for t in tg] == [
        'Rathian Certificate S', 'Rathian Scale+', 'Rathian Carapace', 'Rathian Webbing',
        'Rathian Spike+', 'Rath Medulla', 'Inferno Sac', 'Rathian Ruby']
    print('oracle check passed (Rathian tables match wiki)')


if __name__ == '__main__':
    main()
