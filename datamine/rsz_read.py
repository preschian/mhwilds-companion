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
    if nchars < 0 or nchars > 100000 or nchars * 2 > len(cur.raw) - cur.pos:
        raise ValueError(f'bad string len {nchars}')
    b = cur.read(nchars * 2)
    return b[:-2].decode('utf-16-le')


def read_value(cur, code, size, objs, layouts, mmap, ftype='', n_inst=10**9):
    """Read one non-array field value; returns python value (Object->ref dict)."""
    if code in PRIM:
        fmt, n = PRIM[code]
        v = struct.unpack('<' + fmt, cur.read(n))[0]
        return bool(v) if code == 'Bool' else v
    if code == 'Guid':
        return cur.read(16).hex()
    if code == 'UserData':
        # External-file reference: 4-byte INSTANCE index in the stream (the
        # target instance is the userdata-table path placeholder). Same
        # bounds as Object. Proven on MsData EmSetDataParts._EmSet_BossZako
        # (reads 7 = table[7], the external BossZakoLayout; n_ud is 1).
        idx = cur.s32()
        if idx <= 0:
            return None
        if idx < n_inst:
            return {'$ref': idx}
        return idx
    if code == 'Object':
        idx = cur.s32()
        # Wire index = instance table index directly (table[0] is the NULL
        # placeholder, never referenced). Proven: root._ActionIDHolder reads 2
        # and means table[2] (the Holder itself); Param_Parts arrays resolve
        # to the GuidArray wrapper only without the -1.
        # Out-of-range indices are inline values, not refs (e.g. PredatorParam
        # TraceGimmickID reads 100 with 25 instances: a raw gimmick id, either
        # by design or patch-15 drift vs the 8/12 dump).
        if idx <= 0:
            return None
        if idx < n_inst:
            return {'$ref': idx}
        return idx
    if code == 'String':
        return read_wstring(cur)
    if code == 'RuntimeType':
        # .NET type name: S32 byte-length incl. NUL + UTF-8 bytes. The length
        # prefix alignment is irregular (12/0/4-byte pads seen before the
        # first/sixth/... cData in EmParamBasic), so resync by content: try
        # alignments 16/8/4/1 and take the first sane ASCIIZ string.
        # Proven by end==len across all Param_Basic files.
        for a in (16, 8, 4, 1):
            p = (cur.pos + a - 1) // a * a
            nchars = struct.unpack('<i', cur.raw[p:p + 4])[0]
            if 0 < nchars < 256:
                b = cur.raw[p + 4:p + 4 + nchars]
                if b.endswith(b'\x00') and all(32 <= c < 127 for c in b[:-1]):
                    cur.pos = p + 4 + nchars
                    return b[:-1].decode('utf-8')
        # Fall back to an empty (all files so far have content; loud if wrong).
        nchars = cur.s32()
        if nchars == 0:
            return None
        return cur.read(nchars)[:-1].decode('utf-8')
    if code == 'Struct' and ftype.startswith('System.Nullable'):
        has = struct.unpack('<i', cur.read(4))[0]
        val = struct.unpack('<i', cur.read(4))[0]
        return val if has else None
    # Embedded fixed-size struct (via.vec3 etc.): honour declared size.
    b = cur.read(size)
    if code == 'Vec3':
        return list(struct.unpack('<fff', b[:12]))
    if code == 'Vec2':
        return list(struct.unpack('<ff', b[:8]))
    if code == 'Vec4':
        return list(struct.unpack('<ffff', b[:16]))
    return b.hex()


# (class, field) -> array stride, for fields where the dump's element type
# is stale. EmParamBasic._OverrideStealthIconOffset: dump says via.vec3
# (12B packed) but Em0161 proves 20B/element (lands _SlimRate on 1.0 and
# end==len); the 8B tail is uninterpreted patch drift.
OVERRIDES = {
    ('app.user_data.EmParamBasic', '_OverrideStealthIconOffset'): 20,
}


def read_field(cur, f, objs, layouts, mmap, n_inst=10**9, clsname=None):
    code = f['code']
    size = int(f['size'], 16)
    # re-editor GetAlign(): arrays align count to 4; contents use field.align.
    # Proven on Param_Parts (_PriorityConditions): single Object refs (s32
    # indices) also align to 4, not the native pointer align 8. Same for
    # UserData (MsData _EmSet_BossZako at a 4-but-not-8-aligned slot).
    code_align = 4 if (f.get('array') or code in ('Object', 'UserData')) else f['align']
    if code == 'RuntimeType':
        code_align = 1  # resync inside read_value handles alignment
    cur.align(code_align)
    if not f.get('array'):
        return read_value(cur, code, size, objs, layouts, mmap, f.get('type') or '', n_inst)
    count = cur.s32()
    if count < 0 or count > 100000:
        raise ValueError(f"bad array count {count} for {f.get('potential_name')}")
    if code == 'Object':
        out = []
        for _ in range(count):
            idx = cur.s32()
            if idx <= 0:
                out.append(None)
            elif idx < n_inst:
                out.append({'$ref': idx})
            else:
                out.append(idx)
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
    # Array of embedded structs: elements are PACKED (Vec3 = 12B, Vec2 = 8B),
    # unlike single fields which keep native size + padding (Vec3 = 16B).
    stride = OVERRIDES.get((clsname, f.get('potential_name')),
                           {'Vec3': 12, 'Vec2': 8, 'Vec4': 16}.get(code, size))
    return [cur.read(stride).hex() for _ in range(count)]


def parse_instances(raw, base, data_off, inst_hashes, layouts, mmap, verbose=False,
                    external=None, skip_holder_guid=False, skip_extra=None):
    """Parse inline instances; objs[i] aligns with table index i.

    external: {table_idx: path} for userdata-linked instances (zero inline
    bytes; the RSZ userdata table holds (instance_idx, class, path) 12B
    entries, count in header field 5). They become {'$external': path}
    placeholders so $refs resolve. Entry points and $refs are 0-based
    table indices.
    skip_holder_guid: older-patch files omit cActionIDHolder._ExportGuid
    (EM0008 Legendary holds AddStun floats right after the 4B zero);
    newer ones keep it (Em0001 holds 16 zero bytes). Callers retry.
    skip_extra: {table_idx} elided instances (zero inline bytes, no table
    marker — proven by end==len on Ms001130 skipping 30/86/88). They
    become {'$elided': True} placeholders. Found by caller backtracking.
    """
    cur = Cursor(raw, base + data_off)
    objs = []
    for idx, h in enumerate(inst_hashes):
        if h == 0:
            objs.append(None)
            continue
        if external and idx in external:
            objs.append({'$type': mmap.get(h, '0x%08X' % h), '$external': external[idx]})
            continue
        if skip_extra and idx in skip_extra:
            objs.append({'$type': mmap.get(h, '0x%08X' % h), '$elided': True})
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
                fname = f.get('potential_name') or f.get('type')
                if (skip_holder_guid and name == 'ace.cActionIDHolder'
                        and fname == '_ExportGuid'):
                    obj[fname] = None
                    continue
                obj[fname] = read_field(cur, f, objs, layouts, mmap, len(inst_hashes),
                                        clsname=name)
            # Immediate $ref type-check against the TABLE (forward-safe):
            # garbage reads fail here at their true position instead of
            # cascading into a far-away array explosion. Elided instances
            # (Ms001130: 30/86/88) are caught this way for backtracking.
            for f in fields:
                fname = f.get('potential_name') or f.get('type')
                v = obj.get(fname)
                if v is None:
                    continue
                ftype = _inner((f.get('type') or '').split('[')[0])
                if ftype in ('System.Object', 'object', ''):
                    continue
                vals = v if isinstance(v, list) else [v]
                for e in vals:
                    if not (isinstance(e, dict) and set(e.keys()) == {'$ref'}):
                        continue
                    r = e['$ref']
                    tgt = objs[r] if 0 <= r < len(objs) else None
                    actual = (tgt.get('$type') if isinstance(tgt, dict)
                              else mmap.get(inst_hashes[r] if 0 <= r < len(inst_hashes) else 0, ''))
                    actual = _inner(actual)
                    if actual != ftype and not _is_derived(actual, ftype):
                        raise ValueError(
                            f'ref {fname} -> [{r}] {actual}, want {ftype}')
        except Exception as e:
            raise ValueError(f'inst[{idx}] {name} @0x{cur.pos:X}: {e}') from e
        if verbose:
            print(f'inst[{idx}] {name.split(".")[-1][:30]:30s} 0x{start:X}..0x{cur.pos:X}')
        objs.append(obj)
    return objs, cur.pos


def _inner(t):
    while '<' in t and t.endswith('>'):
        t = t[t.index('<') + 1:-1]
    return t


def _is_derived(actual, expected):
    try:
        from dump_block import is_derived
    except ImportError:
        return False
    try:
        return is_derived(actual, expected)
    except Exception:
        return False


def validate_refs(objs, inst_hashes, layouts, mmap):
    """Check every $ref target class matches the field's declared type.

    Returns a list of mismatch strings (empty = clean). Catches +-4B
    misalignments that end==len cannot (wrong-typed targets). External /
    elided / null targets always pass (their $type travels along).
    """
    bad = []
    for idx, obj in enumerate(objs):
        if not isinstance(obj, dict) or '$external' in obj or '$elided' in obj:
            continue
        h = inst_hashes[idx] if idx < len(inst_hashes) else 0
        fields = layouts.get(mmap.get(h, '')) or []
        for f in fields:
            fname = f.get('potential_name') or f.get('type')
            v = obj.get(fname)
            if v is None:
                continue
            ftype = _inner((f.get('type') or '').split('[')[0])
            vals = v if isinstance(v, list) else [v]
            for e in vals:
                if not (isinstance(e, dict) and set(e.keys()) == {'$ref'}):
                    continue
                t = objs[e['$ref']] if 0 <= e['$ref'] < len(objs) else None
                if not isinstance(t, dict):
                    bad.append(f'inst[{idx}].{fname} -> null/empty')
                    continue
                actual = _inner(t.get('$type', ''))
                if ftype in ('System.Object', 'object', ''):
                    continue
                if actual != ftype and not _is_derived(actual, ftype):
                    bad.append(f'inst[{idx}].{fname}: want {ftype}, got {actual}')
    return bad


def resolve_refs(table, items):
    def walk(v, seen):
        if isinstance(v, dict):
            if set(v.keys()) == {'$ref'}:
                i = v['$ref']
                if i in seen:
                    return {'$cyclic': i}
                return walk(table[i], seen | {i})
            return {k: walk(x, seen) for k, x in v.items()}
        if isinstance(v, list):
            return [walk(x, seen) for x in v]
        return v
    return [walk(o, set()) for o in items]
