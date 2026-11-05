#!/usr/bin/env python3
"""Link Ryu's actions to his moves and animations, from his own data files.

  tools/ryu_moves.py RYU_CHR RYU_MTN                 every action: its moves and their animation ids
  tools/ryu_moves.py RYU_CHR RYU_MTN --action 0x0B   one action in detail
  tools/ryu_moves.py RYU_CHR RYU_MTN --move 0x8EC    which records use one move

The files are cmn.afs entries 141 (ryu.chr, "chr_dat2") and 22 (ryu.mtn, "chr_dat"); the research
folder's Extracted/first_slice has both. What is known (docs/function_map.md):

  ryu.chr  move records, 12 bytes: u16 condition, u16 move, u16 0, u8 kind, u8 flags, u32 0.
           "kind" is Ryu's action number (the byte at 0x4968B4): its values are the ones seen
           while playing (0x0B light attack, 0x26 run start, ...). src/intercept.c edits four of them.
  ryu.mtn  section 1: 2296 move entries (offsets from the section start). Each starts
           u16 3, u16 animation id, then a small script. Animation ids are decimal: below
           10000 a clip of Ryu's own (ryu.mtn section 0, 1890 slots); 10000 + N clip N of the
           weapon's motion file (rm_kt.mot for the Dragon Sword, 1992 slots; ids empty there
           are most likely other weapons' files, which share the numbering).

Records are found by shape (the exact list structure that holds them is not decoded yet), so a
few false matches are possible; counts are of distinct records.
"""
import argparse
import collections
import struct


def chr_sections(b):
    n = struct.unpack_from("<I", b, 0x10)[0]
    first = struct.unpack_from("<I", b, 0x18)[0]
    return list(struct.unpack_from(f"<{n}I", b, first))


def mtn_moves(path):
    b = open(path, "rb").read()
    s0, s1, s2 = chr_sections(b)
    offs = []
    k = 0
    while s1 + 4 * k < s2:
        v = struct.unpack_from("<I", b, s1 + 4 * k)[0]
        if not (0 < v < s2 - s1):
            break
        offs.append(v)
        k += 1
    moves = {}
    for i, o in enumerate(offs):
        a = s1 + o
        tag, anim = struct.unpack_from("<HH", b, a)
        moves[i] = anim if tag == 3 else None
    return moves


def chr_records(path, nmoves):
    b = open(path, "rb").read()
    start = chr_sections(b)[4]
    recs = {}
    for off in range(start, len(b) - 12, 2):
        cond, mv, zero, kind, flags, tail = struct.unpack_from("<HHHBBI", b, off)
        if zero == 0 and tail == 0 and 0 < mv < nmoves and cond < 0x2000 and flags in (0x00, 0x01, 0x02, 0xFF):
            recs[off] = (cond, mv, kind, flags)
    # drop matches overlapping an earlier accepted one (records do not overlap)
    out, last = {}, -12
    for off in sorted(recs):
        if off >= last + 12:
            out[off] = recs[off]
            last = off
    return out


def anim_str(a):
    if a is None:
        return "-"
    return f"ryu:{a}" if a < 10000 else f"weapon:{a - 10000}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("chr")
    ap.add_argument("mtn")
    ap.add_argument("--action", type=lambda x: int(x, 0))
    ap.add_argument("--move", type=lambda x: int(x, 0))
    args = ap.parse_args()

    moves = mtn_moves(args.mtn)
    recs = chr_records(args.chr, len(moves))
    by_kind = collections.defaultdict(list)
    for off, (cond, mv, kind, flags) in recs.items():
        by_kind[kind].append((off, cond, mv, flags))
    print(f"{len(moves)} moves in ryu.mtn, {len(recs)} move records in ryu.chr, {len(by_kind)} actions")

    if args.move is not None:
        print(f"move 0x{args.move:03X}: animation {anim_str(moves.get(args.move))}")
        for off, (cond, mv, kind, flags) in sorted(recs.items()):
            if mv == args.move:
                print(f"  record at 0x{off:05X}: action 0x{kind:02X}, condition 0x{cond:04X}, flags {flags:02X}")
        return
    if args.action is not None:
        rows = by_kind.get(args.action, [])
        print(f"action 0x{args.action:02X}: {len(rows)} records")
        for off, cond, mv, flags in sorted(rows):
            print(f"  0x{off:05X}  condition 0x{cond:04X}  move 0x{mv:03X}  animation {anim_str(moves.get(mv))}"
                  f"  flags {flags:02X}")
        return
    print(f"\n{'action':>6} {'records':>7} {'moves':>5}  animations (ryu:N own clip, weapon:N weapon clip)")
    for kind in sorted(by_kind):
        rows = by_kind[kind]
        if kind == 0 and len(rows) > 1000:
            print(f"  0x00 {len(rows):7}        (mostly false matches in zero-filled data; use --action 0)")
            continue
        mvs = {mv for _, _, mv, _ in rows}
        anims = collections.Counter(anim_str(moves.get(mv)) for mv in mvs)
        print(f"  0x{kind:02X} {len(rows):7} {len(mvs):5}  " + ", ".join(f"{a} x{n}" for a, n in anims.most_common(6)))


if __name__ == "__main__":
    main()
