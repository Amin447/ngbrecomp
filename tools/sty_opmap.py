"""Sigma <-> NGB stage-script (.sty) opcode map (found 2026-11-08 by aligning s_yask00/s_tlna01/s_chrc01/s_hori
of both games on their arguments; ~44k instructions matched).

  NGB op 0x01-0x05   = Sigma same
  NGB op 0x06-0x55   = Sigma op + 0x05      (Sigma inserted 0x06-0x0a: battle-script ops, used by .btl)
  NGB op 0x56-0x141  = Sigma op + 0x0F      (Sigma inserted 0x5b-0x64)
  NGB op 0x142       = Sigma 0x16E          (Sigma inserted 0x152-0x16d)
Sigma-only ops (no NGB number) are mostly per-difficulty / multi-value versions of NGB ops:
  0x61(a,x,..)->0x2c(a,x)   0x160(x,1,..)->0x83(x,1)   0x161(x,..)->0x11f(x)   0x62->0x41  0x162->0xd1  0x163->0xd2  0x164->0xd4
  0x157/0x153/0x154/0x155/0x5b/0x63/0x64/0x16a-0x16c -> NGB 0xd6 (flags) or 0x09, with DIFFERENT flag ids
  (e.g. Sigma 0x157(1024,0) = NGB 0xd6(896,0)), so a flag-id map is needed too. Item ids also differ (Sigma 42 = NGB 64).
NGB has no .btl files: Sigma moved battles into .btl (ops 0x06-0x0a); NGB keeps them inside .sty.

  python -I sty_opmap.py <sigma .sty>    -> counts of ops that map / need a rule
"""
import struct, sys, collections


def sigma_to_ngb(op):
    if op <= 5: return op
    if 0x0b <= op <= 0x5a: return op - 5
    if 0x65 <= op <= 0x151: return op - 0x0f
    if op == 0x16e: return 0x142
    return None


def ngb_to_sigma(op):
    if op <= 5: return op
    if 0x06 <= op <= 0x55: return op + 5
    if 0x56 <= op <= 0x141: return op + 0x0f
    if op == 0x142: return 0x16e
    return None


if __name__ == "__main__":
    d = open(sys.argv[1], "rb").read()
    a, e = struct.unpack_from("<2I", d, 0x20)
    W = struct.unpack_from(f"<{(e - a) // 4}I", d, a)
    ops = [w & 0xFFFFFF for w in W if w >> 24 == 0x82 and (w & 0xFFFFFF) < 0x200]
    bad = collections.Counter(o for o in ops if sigma_to_ngb(o) is None)
    print(len(ops), "ops,", len(ops) - sum(bad.values()), "map directly; need a rule:", {hex(k): v for k, v in bad.most_common()})
