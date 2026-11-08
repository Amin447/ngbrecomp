import struct, subprocess, sys
exec(open('opmap.py').read().split('G="')[0])
G = "C:/Users/10/AppData/Local/NinjaGaidenBlack/game/"
C = "G:/NinjaGaidenBlack/RecordBuild/userdata/Cache/"
X = "G:/NinjaGaidenSigma/NGS1_extracted/"
def zlists(d):
    t = struct.unpack_from('<I', d, 0x18)[0]; s2 = struct.unpack_from('<I', d, t + 8)[0]; L = d[s2:]
    hdr, p = [], 0
    while True:
        z, o = struct.unpack_from('<II', L, p); p += 8
        if z == 0xffff: break
        hdr.append((z, o))
    out = {}
    for z, o in hdr:
        q, r = o, []
        while struct.unpack_from('<H', L, q)[0] != 0xff:
            r.append(struct.unpack_from('<3H', L, q)); q += 6
        out[z] = [k for pl, k, _ in r if pl == 0 and k not in (0, 4)]
    return out
for m in ('m_27tlna', 'm_33tlna', 'm_39tlna', 'm_43tlna', 'm_53tlna', 'm_54tlna', 'm_70tlna', 'm_78tlna'):
    d = afs_get(C + 'tln_a_cmn.afs.bak', m + '.sty'); open('ngb_' + m + '.sty', 'wb').write(d)
    zl = zlists(d)
    cand = zl.get(77) or zl.get(78) or zl.get(76) or []
    tm = [] if 0x2e in cand else ([f'--type-map', f'0x2e:{cand[0]:#x}'] if cand else [])
    r = subprocess.run([sys.executable, '-I', 'G:/NinjaGaidenSigma/levels/sigma2ngb_sty.py', X + '04326.stry_dat', X + '04327.btl_dat',
                        '-o', f'r_tlna04_{m}.sty', '--container', 'ngb_' + m + '.sty', '--drop-container-spawns',
                        '--replace-zone-rules', '--drop-battles', '0', '--no-start-lock'] + tm, capture_output=True, text=True)
    new = open(f'r_tlna04_{m}.sty', 'rb').read()
    ok = len(new) == len(d)
    print(m, 'zone77 types', [hex(x) for x in cand], 'map', tm[1:] or 'none', 'size ok' if ok else f'SIZE {len(new)} != {len(d)}', r.stderr[-200:])
    if ok:
        r2 = subprocess.run([sys.executable, '-I', 'G:/NinjaGaidenSigma/levels/afs_replace.py', C + 'tln_a_cmn.afs', m + '.sty', f'r_tlna04_{m}.sty'], capture_output=True, text=True)
        print('   ', r2.stdout.strip(), r2.stderr.strip()[-200:])
