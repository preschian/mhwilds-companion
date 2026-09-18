"""Hash helpers for RSZ class identification.

Usage:
  python hash_check.py <ClassName> [...]        -> print murmur3 of names
  python hash_check.py --collide <HEX> [...]    -> find all dump names with hash
"""
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rsz_inspect import murmur3_x86_32  # noqa: E402

SEED = 0xFFFFFFFF
GAME_DIR = os.environ.get('MHWILDS_GAME', r'D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds')
DUMP = os.path.join(GAME_DIR, 'il2cpp_dump.json')


def main():
    args = sys.argv[1:]
    if args and args[0] == '--collide':
        want = {int(x, 16) for x in args[1:]}
        top = re.compile(r'^    "(.+)": \{$')
        with open(DUMP, encoding='utf-8') as f:
            for line in f:
                m = top.match(line.rstrip('\r\n'))
                if not m:
                    continue
                h = murmur3_x86_32(m.group(1).encode('utf-8'), SEED)
                if h in want:
                    print(f'{h:08X} <- {m.group(1)[:130]}')
        return
    for n in args:
        print(f'{murmur3_x86_32(n.encode("utf-8"), SEED):08X}  {n}')


if __name__ == '__main__':
    main()
