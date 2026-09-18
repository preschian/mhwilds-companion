"""RE Engine GMSG (.msg) reader — port of re-editor MSG.cs for data mining.

Usage: python msg_parse.py <file.msg.23> [--json out.json]
Prints entry count + first entries (name, eng).
"""
import struct
import sys
import json

KEY = bytes([207, 206, 251, 248, 236, 10, 51, 102, 147, 169, 29, 147, 80, 57, 95, 9])


def decrypt(data: bytearray) -> None:
    b = 0
    for num in range(len(data)):
        b2 = b
        b = data[num]
        data[num] = b2 ^ b ^ KEY[num & 15]


def read_wstr(dec: bytes, data1_off: int, off: int) -> str:
    if off < data1_off:
        return ''
    pos = off - data1_off
    end = pos
    while not (dec[end] == 0 and dec[end + 1] == 0):
        end += 2
    return dec[pos:end].decode('utf-16-le')


def parse(path: str):
    raw = bytearray(open(path, 'rb').read())
    (version, magic, header_off, sub_count, type_count, lang_count, zero,
     data1_off, data2_off, lang_off, type_off, typename_off) = struct.unpack_from('<IIQIII IQQQQQ'.replace(' ', ''), raw, 0)
    assert magic == 0x47534D47, f'bad magic {magic:08X} in {path}'
    data1 = bytearray(raw[data1_off:])
    decrypt(data1)
    dec = bytes(data1)
    pos = 4 + 4 + 8 + 4 + 4 + 4 + 4 + 8 + 8 + 8 + 8 + 8
    sub_offsets = struct.unpack_from(f'<{sub_count}Q', raw, pos)
    entries = []
    for sub_off in sub_offsets:
        guid = bytes(raw[sub_off:sub_off + 16])
        crc, h = struct.unpack_from('<II', raw, sub_off + 16)
        entry_name_off, type_entry_off = struct.unpack_from('<QQ', raw, sub_off + 24)
        str_offs = struct.unpack_from(f'<{lang_count}Q', raw, sub_off + 40)
        name = read_wstr(dec, data1_off, entry_name_off)
        refs = [read_wstr(dec, data1_off, o) for o in str_offs]
        entries.append({'guid': guid.hex(), 'crc': crc, 'hash': h, 'name': name, 'refs': refs})
    # Language order table (positions -> LangIndex; eng == 1).
    p = pos + 8 * sub_count + 8
    langs = list(struct.unpack_from(f'<{lang_count}i', raw, p))
    return {'version': version, 'langs': langs, 'entries': entries}


def main():
    path = sys.argv[1]
    out = None
    if '--json' in sys.argv:
        out = sys.argv[sys.argv.index('--json') + 1]
    r = parse(path)
    try:
        eng = r['langs'].index(1)
    except ValueError:
        eng = 1 if len(r['langs']) > 1 else 0
    print(f'{path}: version={r["version"]} langs={r["langs"]} entries={len(r["entries"])} eng_pos={eng}')
    for e in r['entries'][:25]:
        print(f'  {e["name"]}  =>  {e["refs"][eng] if eng < len(e["refs"]) else "?"}')
    if len(r['entries']) > 25:
        print(f'  ... +{len(r["entries"]) - 25} more')
    if out:
        slim = [{'name': e['name'], 'eng': e['refs'][eng], 'crc': e['crc'], 'hash': e['hash']} for e in r['entries']]
        json.dump(slim, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'wrote {out}')


if __name__ == '__main__':
    main()
