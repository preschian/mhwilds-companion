"""Resolve RSZ instance hashes to class names across merged files; hunt meat classes.

Usage: python rsz_classscan.py [--all-meat] [path-filter...]
Default: show instance classes for Param_Parts / Body / CharacterParamPack of Em0001.
--all-meat: scan every merged .user/.rcol, report files with meat-ish instances.
"""
import io
import os
import tempfile
import re
import struct
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rsz_inspect import murmur3_x86_32  # noqa: E402

RESEARCH = os.environ.get('MHRESEARCH', os.path.join(tempfile.gettempdir(), 'mhwilds-research'))
GAME_DIR = os.environ.get('MHWILDS_GAME', r'D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds')
DUMP = os.path.join(GAME_DIR, 'il2cpp_dump.json')
ROOT = os.path.join(RESEARCH, 'extract_full', 'merged', 'natives', 'STM', 'GameDesign', 'Enemy')
SEED = 0xFFFFFFFF
MEAT_RE = re.compile(r'Meat|Hitzone|HitZone|DamageRate|Niku|MeatQuality|Flesh', re.I)


def build_map():
    m = {}
    top = re.compile(r'^    "(.+)": \{$')
    with open(DUMP, encoding='utf-8') as f:
        for line in f:
            mt = top.match(line.rstrip('\r\n'))
            if mt:
                name = mt.group(1)
                m[murmur3_x86_32(name.encode('utf-8'), SEED)] = name
    return m


def instances_of(path):
    raw = open(path, 'rb').read()
    base = raw.find(b'RSZ\x00')
    if base == -1:
        return None
    _, _, n_obj, n_inst, _, _, inst_off, _, _ = struct.unpack_from('<IIIiIIQQQ', raw, base)
    eps = struct.unpack_from(f'<{n_obj}I', raw, base + 48)
    out = []
    for i in range(n_inst):
        h, _ = struct.unpack_from('<II', raw, base + inst_off + 8 * i)
        out.append(h)
    return eps, out


def main():
    print('building murmur map...', flush=True)
    mmap = build_map()
    print(f'map size={len(mmap)}', flush=True)
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    global ROOT
    if '--root' in sys.argv:
        _ri = sys.argv.index('--root')
        ROOT = sys.argv[_ri + 1]
        args = [a for a in args if a != sys.argv[_ri + 1]]
    if '--all-meat' in sys.argv:
        n_files, n_hit = 0, 0
        for dp, _, fns in os.walk(ROOT):
            for fn in fns:
                if not (fn.endswith('.3') or '.rcol.' in fn):
                    continue
                p = os.path.join(dp, fn)
                try:
                    r = instances_of(p)
                except Exception:
                    continue
                if r is None:
                    continue
                n_files += 1
                _, insts = r
                names = [mmap.get(h, f'??0x{h:08X}') for h in insts]
                meat = [x for x in names if MEAT_RE.search(x)]
                if meat:
                    n_hit += 1
                    print(f'== {os.path.relpath(p, ROOT)}')
                    for x in sorted(set(meat)):
                        print(f'   MEAT: {x}')
        print(f'scanned={n_files} meat_files={n_hit}')
        return
    targets = args or [
        r'Em0001\00\Data\Em0001_00_Param_Parts.user.3',
        r'Em0001\00\Collision\Collider\Em0001_00_Body.rcol.28',
        r'Em0001\00\Data\Em0001_00_CharacterParamPack.user.3',
    ]
    for t in targets:
        p = os.path.join(ROOT, t)
        print(f'== {t}')
        try:
            eps, insts = instances_of(p)
        except Exception as e:
            print(f'   ERR {e}')
            continue
        print(f'   entry={list(eps)}')
        for i, h in enumerate(insts):
            print(f'   [{i}] {mmap.get(h, ("NULL" if h == 0 else f"??0x{h:08X}"))}')


if __name__ == '__main__':
    main()
