"""Generic RSZ data-section reader driven by il2cpp_dump RSZ metadata.

Covers the type subset used by EmParamParts files:
  primitives (S8..F64, Bool), Guid, Object/Object[], String/String[],
  F32[]/S32[]/Guid[], embedded fixed-size via structs (by declared size).
Layouts: {class_name: [field, ...]} as dumped by dump_rsz.py --full.
Instance classes resolved via murmur3 map (built by caller).
"""
import struct
import sys

PRIM = {
    'S8': ('b', 1), 'U8': ('B', 1), 'Bool': ('B', 1),
    'S16': ('h', 2), 'U16': ('H', 2),
    'S32': ('i', 4), 'U32': ('I', 4), 'F32': ('f', 4),
    'S64': ('q', 8), 'U64': ('Q', 8), 'F64': ('d', 8),
}


class Cursor:
    def __init__(self, raw, pos):
        self.raw = raw
        self.pos = pos

    def align(self, a):
        if a > 1:
            self.pos = (self.pos + a - 1) // a * a

    def read(self, n):
        b = self.raw[self.pos:self.pos + n]
        self.pos += n
        return b

    def s32(self):
        return struct.unpack('<i', self.read(4))[0]


def read_wstring(cur):
    nchars = cur.s32()
    if nchars == 0:
        return None
    b = cur.read(nchars * 2)
    return b[:-2].decode('utf-16-le')


def read_value(cur, code, size, objs, layouts, mmap):
    """Read one non-array field value; returns python value (Object->ref dict)."""
    if code in PRIM:
        fmt, n = PRIM[code]
        v = struct.unpack('<' + fmt, cur.read(n))[0]
        return bool(v) if code == 'Bool' else v
    if code == 'Guid':
        return cur.read(16).hex()
    if code == 'Object':
        idx = cur.s32()
        return {'$ref': idx - 1} if idx > 0 else None
    if code == 'String':
        return read_wstring(cur)
    # Embedded fixed-size struct (via.vec3 etc.): honour declared size.
    b = cur.read(size)
    if code == 'Vec3':
        return list(struct.unpack('<fff', b[:12]))
    if code == 'Vec2':
        return list(struct.unpack('<ff', b[:8]))
    if code == 'Vec4':
        return list(struct.unpack('<ffff', b[:16]))
    return b.hex()


def read_field(cur, f, objs, layouts, mmap):
    code = f['code']
    size = int(f['size'], 16)
    # re-editor GetAlign(): arrays align count to 4; contents use field.align.
    # Proven on Param_Parts (_PriorityConditions): single Object refs (s32
    # indices) also align to 4, not the native pointer align 8.
    code_align = 4 if (f.get('array') or code == 'Object') else f['align']
    cur.align(code_align)
    if not f.get('array'):
        return read_value(cur, code, size, objs, layouts, mmap)
    count = cur.s32()
    if count < 0 or count > 100000:
        raise ValueError(f"bad array count {count} for {f.get('potential_name')}")
    if code == 'Object':
        out = []
        for _ in range(count):
            idx = cur.s32()
            out.append({'$ref': idx - 1} if idx > 0 else None)
        return out
    if code == 'String':
        out = []
        for _ in range(count):
            cur.align(f['align'])
            out.append(read_wstring(cur))
        return out
    if code == 'Guid':
        # Embedded-struct array: align each element to field.align.
        return [cur.align(f['align']) or cur.read(16).hex() for _ in range(count)]
    if code in PRIM:
        n = PRIM[code][1]
        out = []
        for _ in range(count):
            b = cur.read(n)
            if code == 'Guid':
                out.append(b.hex())
            else:
                v = struct.unpack('<' + PRIM[code][0], b)[0]
                out.append(bool(v) if code == 'Bool' else v)
        return out
    # Array of embedded structs: recurse by size (no per-element class info here).
    return [cur.read(size).hex() for _ in range(count)]


def parse_instances(raw, base, data_off, inst_hashes, layouts, mmap, verbose=False):
    cur = Cursor(raw, base + data_off)
    objs = []
    for idx, h in enumerate(inst_hashes):
        if h == 0:
            continue
        name = mmap.get(h)
        if name is None:
            raise ValueError(f'unknown instance hash 0x{h:08X}')
        fields = layouts.get(name)
        if fields is None:
            raise ValueError(f'no layout for {name}')
        obj = {'$type': name}
        start = cur.pos
        try:
            for f in fields:
                obj[f.get('potential_name') or f.get('type')] = read_field(cur, f, objs, layouts, mmap)
        except Exception as e:
            raise ValueError(f'inst[{idx}] {name} @0x{cur.pos:X}: {e}') from e
        if verbose:
            print(f'inst[{idx}] {name.split(".")[-1][:30]:30s} 0x{start:X}..0x{cur.pos:X}')
        objs.append(obj)
    return objs, cur.pos


def resolve_refs(table, items):
    def walk(v):
        if isinstance(v, dict):
            if set(v.keys()) == {'$ref'}:
                return walk(table[v['$ref']])
            return {k: walk(x) for k, x in v.items()}
        if isinstance(v, list):
            return [walk(x) for x in v]
        return v
    return [walk(o) for o in items]
