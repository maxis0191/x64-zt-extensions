"""ZoneTool assetmanager dump stream (the .xsb/.xmb/... binary dumps of IW7 in-memory structs).

Every record starts with a dump_type byte:
  STRING(6)/ASSET(7): existing u8, then a NUL-terminated string when existing.
  ARRAY(8): existing u8, then u32 element count and count * sizeof(T) bytes.
  RAW(10):  existing u8, then u32 byte size and size bytes.
  OFFSET(9): u32 entry index, u32 array index (re-use of an earlier dumped pointer, no existing byte).
  CHAR/SHORT/INT/FLOAT/INT64 (1..5): value only.
Source: x64-zt src/zonetool/zonetool/utils/io/assetmanager.hpp (dumper/reader).
"""
import struct

T_CHAR, T_SHORT, T_INT, T_FLOAT, T_INT64, T_STRING, T_ASSET, T_ARRAY, T_OFFSET, T_RAW = range(1, 11)
_SCALAR = {T_CHAR: 1, T_SHORT: 2, T_INT: 4, T_FLOAT: 4, T_INT64: 8}


class Rec:
    """One dump record. data is bytes (array/raw payload), str (string/asset) or None (non existing)."""
    __slots__ = ("kind", "data", "count", "offset")

    def __init__(self, kind, data=None, count=0, offset=None):
        self.kind, self.data, self.count, self.offset = kind, data, count, offset

    @property
    def exists(self):
        return self.offset is not None or self.data is not None

    def __repr__(self):
        if self.offset is not None:
            return "Rec(OFFSET %r)" % (self.offset,)
        n = len(self.data) if isinstance(self.data, (bytes, bytearray)) else self.data
        return "Rec(%d, %r, count=%d)" % (self.kind, n, self.count)


class Reader:
    def __init__(self, blob):
        self.b, self.p = blob, 0
        self.entries = []  # existing records in dump order (targets of OFFSET records)

    def resolve(self, rec):
        """Follow an OFFSET record to the earlier record it points into."""
        return self.entries[rec.offset[0]] if rec.offset is not None else rec

    def _u8(self):
        v = self.b[self.p]
        self.p += 1
        return v

    def _u32(self):
        v = struct.unpack_from("<I", self.b, self.p)[0]
        self.p += 4
        return v

    def _cstr(self):
        e = self.b.index(b"\0", self.p)
        s = self.b[self.p:e].decode("latin-1")
        self.p = e + 1
        return s

    def _head(self, want):
        t = self._u8()
        if t == T_OFFSET:
            return Rec(want, offset=(self._u32(), self._u32()))
        if t != want:
            raise ValueError("dump type %d at 0x%x, expected %d" % (t, self.p - 1, want))
        return None

    def string(self, kind=T_STRING):
        off = self._head(kind)
        if off:
            return off
        if not self._u8():
            return Rec(kind)
        r = Rec(kind, self._cstr())
        self.entries.append(r)
        return r

    def asset(self):
        return self.string(T_ASSET)

    def array(self, elem_size):
        off = self._head(T_ARRAY)
        if off:
            return off
        if not self._u8():
            return Rec(T_ARRAY)
        n = self._u32()
        d = bytes(self.b[self.p:self.p + n * elem_size])
        if len(d) != n * elem_size:
            raise ValueError("truncated array")
        self.p += n * elem_size
        r = Rec(T_ARRAY, d, n)
        self.entries.append(r)
        return r

    def raw(self):
        off = self._head(T_RAW)
        if off:
            return off
        if not self._u8():
            return Rec(T_RAW)
        n = self._u32()
        d = bytes(self.b[self.p:self.p + n])
        self.p += n
        r = Rec(T_RAW, d, n)
        self.entries.append(r)
        return r

    def at_end(self):
        return self.p == len(self.b)


class Writer:
    def __init__(self):
        self.out = bytearray()

    def rec(self, r):
        o = self.out
        o.append(r.kind)
        if r.offset is not None:
            o[-1] = T_OFFSET
            o += struct.pack("<II", *r.offset)
            return
        if r.data is None:
            o.append(0)
            return
        o.append(1)
        if r.kind in (T_STRING, T_ASSET):
            o += r.data.encode("latin-1") + b"\0"
        elif r.kind == T_ARRAY:
            o += struct.pack("<I", r.count) + r.data
        elif r.kind == T_RAW:
            o += struct.pack("<I", len(r.data)) + r.data
        else:
            raise ValueError(r.kind)

    def string(self, s, kind=T_STRING):
        self.rec(Rec(kind, s))

    def asset(self, s):
        self.rec(Rec(T_ASSET, s))

    def array(self, data, count):
        self.rec(Rec(T_ARRAY, bytes(data) if data is not None and count else None, count))

    def raw(self, data):
        self.rec(Rec(T_RAW, bytes(data) if data else None, len(data) if data else 0))

    def bytes(self):
        return bytes(self.out)
