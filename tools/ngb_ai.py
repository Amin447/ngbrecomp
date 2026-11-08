"""Decode Ninja Gaiden Black enemy AI scripts with Sigma's aiscript.py (2026-11-08).

NGB .chr files have the same layout as Sigma's, and their AI bytecode is the same except for the
op numbers (found by lining up cat / genin / titan / yonin scripts with Sigma's):
  NGB op <= 0x30        = same Sigma op
  NGB op 0x31 - 0x91    = Sigma op + 1   (Sigma added one op at 0x30/0x31)
  NGB op 0x92 - 0x96    = Sigma op + 4   (Sigma added 0x92-0x94; NGB 0x92..0x96 = NOT, AND, OR, ELSE, END)
This rewrites the AI scripts of an NGB .chr into Sigma numbering (a temp copy) and prints the listing.

  python -I ngb_ai.py <ngb .chr file> [script n]
"""
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chrscript as cs  # noqa: E402
import aiscript as ai  # noqa: E402


def to_sigma(op):
    if op <= 0x30:
        return op
    if op <= 0x91:
        return op + 1
    if op <= 0x96:
        return op + 4
    return op


def convert(path):
    d = bytearray(open(path, 'rb').read())
    _, s4, sub = cs.load(path)
    base = s4 + sub[16]
    offs = []
    while True:
        v = struct.unpack_from('<I', d, base + len(offs) * 4)[0]
        if v == 0 or s4 + v >= len(d) or len(offs) > 512:
            break
        offs.append(v)
    for o in offs:
        p = s4 + o
        while p < len(d):
            op = to_sigma(d[p])
            if op >= 0x9C:
                break
            d[p] = op
            if op == 0:
                break
            p += ai.LEN[op]
    fd, tmp = tempfile.mkstemp(suffix='.chr')
    os.write(fd, bytes(d)); os.close(fd)
    return tmp


if __name__ == '__main__':
    tmp = convert(sys.argv[1])
    sys.argv = [sys.argv[0], tmp] + sys.argv[2:]
    try:
        ai.main()
    finally:
        os.remove(tmp)
