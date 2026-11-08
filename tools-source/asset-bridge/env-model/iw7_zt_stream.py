"""ZoneTool assetmanager record streams (the .xmb / .xsb dump format), stdlib only.

ZoneTool's dumper writes a typed record per field (assetmanager.hpp): a one-byte type, then
  ARRAY (8):  existing byte, [u32 count, count * sizeof(T) bytes]
  STRING (6): existing byte, [NUL-terminated text]
  ASSET (7):  existing byte, [NUL-terminated asset name]
  RAW (10):   existing byte, [u32 size, size bytes]
  OFFSET (9): u32 entry index, u32 array index (a pointer into an earlier record)
Arrays carry no element size: a reader must know the schema. Reader and Writer here are the
schema-free primitives; iw7_xmodel_io.py holds the IW7 XModel / XModelSurfs schemas.
"""
import struct

T_STRING, T_ASSET, T_ARRAY, T_OFFSET, T_RAW = 6, 7, 8, 9, 10


class StreamError(ValueError):
    pass


class Reader:
    def __init__(self, data):
        self.d = bytes(data)
        self.p = 0

    def _type(self, want):
        t = self.d[self.p]
        if t == T_OFFSET:
            idx, arr = struct.unpack_from('<II', self.d, self.p + 1)
            self.p += 9
            return ('offset', idx, arr)
        if t != want:
            raise StreamError('record type %d at %d, expected %d' % (t, self.p, want))
        self.p += 1
        ex = self.d[self.p]
        self.p += 1
        return ex

    def array(self, size):
        """bytes of the array (count * size), None when absent; ('offset', i, j) for a back reference."""
        ex = self._type(T_ARRAY)
        if isinstance(ex, tuple):
            return ex
        if not ex:
            return None
        n = struct.unpack_from('<I', self.d, self.p)[0]
        self.p += 4
        b = self.d[self.p:self.p + n * size]
        if len(b) != n * size:
            raise StreamError('array truncated at %d' % self.p)
        self.p += n * size
        return b

    def raw(self):
        ex = self._type(T_RAW)
        if isinstance(ex, tuple):
            return ex
        if not ex:
            return None
        n = struct.unpack_from('<I', self.d, self.p)[0]
        self.p += 4
        b = self.d[self.p:self.p + n]
        self.p += n
        return b

    def _text(self, want):
        ex = self._type(want)
        if isinstance(ex, tuple):
            return ex
        if not ex:
            return None
        e = self.d.index(b'\0', self.p)
        s = self.d[self.p:e].decode('latin-1')
        self.p = e + 1
        return s

    def string(self):
        return self._text(T_STRING)

    def asset(self):
        return self._text(T_ASSET)

    def at_end(self):
        return self.p >= len(self.d)


class Writer:
    def __init__(self):
        self.parts = []

    def _offset(self, v):
        if isinstance(v, tuple) and v and v[0] == 'offset':
            self.parts.append(bytes([T_OFFSET]) + struct.pack('<II', v[1], v[2]))
            return True
        return False

    def array(self, data, size):
        if self._offset(data):
            return
        if data is None or len(data) == 0:
            self.parts.append(bytes([T_ARRAY, 0]))
            return
        if len(data) % size:
            raise StreamError('array of %d bytes is not a multiple of %d' % (len(data), size))
        self.parts.append(bytes([T_ARRAY, 1]) + struct.pack('<I', len(data) // size) + bytes(data))

    def raw(self, data):
        if self._offset(data):
            return
        if not data:
            self.parts.append(bytes([T_RAW, 0]))
            return
        self.parts.append(bytes([T_RAW, 1]) + struct.pack('<I', len(data)) + bytes(data))

    def string(self, s):
        if self._offset(s):
            return
        self.parts.append(bytes([T_STRING, 0]) if s is None else bytes([T_STRING, 1]) + s.encode('latin-1') + b'\0')

    def asset(self, s):
        if self._offset(s):
            return
        self.parts.append(bytes([T_ASSET, 0]) if s is None else bytes([T_ASSET, 1]) + s.encode('latin-1') + b'\0')

    def bytes(self):
        return b''.join(self.parts)
