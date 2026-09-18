"""RSZ inspector: header, instance hashes, userData strings. Tests murmur3(name)==hash.

Usage: python rsz_inspect.py <file.user.3|.rcol> [--test-hash]
"""
import struct
import sys


def murmur3_x86_32(data: bytes, seed=0):
    c1, c2 = 0xCC9E2D51, 0x1B873593
    h = seed
    n = len(data) // 4 * 4
    for i in range(0, n, 4):
        k = struct.unpack_from('<I', data, i)[0]
        k = (k * c1) & 0xFFFFFFFF
        k = ((k << 15) | (k >> 17)) & 0xFFFFFFFF
        k = (k * c2) & 0xFFFFFFFF
        h ^= k
        h = ((h << 13) | (h >> 19)) & 0xFFFFFFFF
        h = (h * 5 + 0xE6546B64) & 0xFFFFFFFF
    tail = data[n:]
    k = 0
    for i, b in enumerate(tail):
        k |= b << (8 * i)
    if tail:
        k = (k * c1) & 0xFFFFFFFF
        k = ((k << 15) | (k >> 17)) & 0xFFFFFFFF
        k = (k * c2) & 0xFFFFFFFF
        h ^= k
    h ^= len(data)
    h ^= h >> 16
    h = (h * 0x85EBCA6B) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0xC2B2AE35) & 0xFFFFFFFF
    h ^= h >> 16
    return h


def parse(path):
    raw = open(path, 'rb').read()
    base = raw.find(b'RSZ\x00')
    assert base != -1, 'no RSZ section'
    magic, ver, n_obj, n_inst, n_user, reserved, inst_off, data_off, user_off = \
        struct.unpack_from('<IIIiIIQQQ', raw, base)
    print(f'{path}\n  RSZ@0x{base:X} magic={magic:08X} ver={ver} objs={n_obj} insts={n_inst} users={n_user}')
    print(f'  inst_off=0x{inst_off:X} data_off=0x{data_off:X} user_off=0x{user_off:X}')
    eps = struct.unpack_from(f'<{n_obj}I', raw, base + 48)
    print(f'  entry points: {list(eps)}')
    print('  --- instances (idx, hash, crc) ---')
    insts = []
    for i in range(n_inst):
        h, c = struct.unpack_from('<II', raw, base + inst_off + 8 * i)
        insts.append((h, c))
        print(f'    [{i}] hash=0x{h:08X} crc=0x{c:08X}')
    print('  --- userData (instanceId, hash, str) ---')
    users = []
    for i in range(n_user):
        iid, h, soff = struct.unpack_from('<IiQ', raw, base + user_off + 16 * i)
        sp = base + soff
        end = sp
        while not (raw[end] == 0 and raw[end + 1] == 0):
            end += 2
        s = raw[sp:end].decode('utf-16-le')
        users.append((iid, h, s))
        print(f'    inst={iid} hash=0x{h:08X} str={s}')
    return insts, users


def main():
    insts, users = parse(sys.argv[1])
    if '--test-hash' in sys.argv:
        print('  --- murmur3 tests ---')
        for iid, h, s in users:
            for seed in (0, 0xFFFFFFFF):
                if murmur3_x86_32(s.encode('utf-8'), seed) == h:
                    print(f'    MATCH seed=0x{seed:X} :: {s}')
                    break
            else:
                print(f'    no-match: {s} (file hash 0x{h:08X}, mm0=0x{murmur3_x86_32(s.encode()):08X})')


if __name__ == '__main__':
    main()
