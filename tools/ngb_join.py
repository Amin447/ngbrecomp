"""Name NGB global file numbers: join recordings/chr_loads.txt (archive, offset, buffer) with
recordings/chr_slots.txt (slot start address -> file number). Appends to ngb_filenames.csv."""
import re, os, csv, sys
R = sys.argv[1] if len(sys.argv) > 1 else "G:/NinjaGaidenBlack/RecordBuild/recordings"
bufs = {}
for l in open(os.path.join(R, "chr_loads.txt")):
    m = re.match(r"(\S+) off (\w+) len (\w+) buf (\w+)", l)
    if m and m.group(4)[0] == "8":
        bufs[int(m.group(4), 16)] = (m.group(1), m.group(2), m.group(3))
num = {}
for l in open(os.path.join(R, "chr_slots.txt")):
    p = l.split()
    if len(p) == 9 and len(p[1]) == 8:
        start, fileno = int(p[1], 16), int(p[6], 16) & 0xFFFF
        if start in bufs and fileno != 0xFFFF:
            num[fileno] = bufs[start]
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ngb_filenames.csv")
old = {}
if os.path.exists(out):
    old = {r["number"]: r for r in csv.DictReader(open(out))}
for k, (a, o, ln) in num.items():
    old[f"{k:04X}"] = {"number": f"{k:04X}", "archive": a, "offset": o, "length": ln}
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["number", "archive", "offset", "length"]); w.writeheader()
    w.writerows(sorted(old.values(), key=lambda r: r["number"]))
print(len(num), "named now,", len(old), "total")
for k in sorted(num): print(f"{k:04X}", *num[k])
