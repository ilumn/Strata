from pathlib import Path
import sys, shutil
import argparse
parser=argparse.ArgumentParser(description="Temporary teacher-forcing overlay; no arithmetic changes")
parser.add_argument("root",type=Path)
parser.add_argument("--backup",type=Path,required=True)
parser.add_argument("--restore",action="store_true")
args=parser.parse_args()
root=args.root.resolve()
store=args.backup.resolve()
p=root/'src/program/generate.cpp'
if args.restore:
    shutil.copyfile(store/'generate.cpp',p);p.touch();sys.exit()
if 'UPSTREAM_PARITY_OVERLAY' in p.read_text():raise SystemExit('already instrumented')
store.mkdir(parents=True,exist_ok=True)
if (store/'generate.cpp').exists():raise SystemExit('backup already exists; use a fresh directory or restore first')
shutil.copyfile(p,store/'generate.cpp')
s=p.read_text()
header=Path(__file__).resolve().parent/'trace.hpp'
s='#include "'+str(header)+'" // UPSTREAM_PARITY_OVERLAY\n'+s
s=s.replace('        bool mrope_identity = true;', '        bool mrope_identity = true;\n        UpstreamTrace parity;')
s=s.replace('            bool active = false;', '            uint64_t parity_id = 0;\n            bool active = false;')
# Locate BSlot separately: not all versions spell its member initializer identically.
if 'uint64_t parity_id' not in s[s.index('struct BSlot'):s.index('struct BSlot')+250]:
    s=s.replace('        struct BSlot {', '        struct BSlot {\n            uint64_t parity_id = 0;')
s=s.replace('            int64_t produced_n = 0,', '            const uint64_t parity_id = ++parity.serial_id;\n            int64_t produced_n = 0,')
s=s.replace('                if (p + T > o.max_context) break;', '                if (parity.enabled()) T = 1;\n                if (p + T > o.max_context) break;')
s=s.replace('                int a = 0;\n                while (a < T - 1', '                if (!parity.record(ver, 0, parity_id, produced_n, p, outv[0], err)) { std::printf("ERR %s%c", err.c_str(), 10); return 1; }\n                int a = 0;\n                while (a < T - 1')
s=s.replace('                    sl = BSlot{};\n                    sl.active = true;', '                    sl = BSlot{};\n                    sl.parity_id = parity_id;\n                    sl.active = true;')
if 'sl.parity_id = parity_id' not in s:
    s=s.replace('                    sl = BSlot {};', '                    sl = BSlot {};\n                    sl.parity_id = parity_id;')
s=s.replace('            const Clock::time_point w1 = Clock::now();\n            if (!ver.commit_slots(err))', '''            for (int t = 0; t < S; ++t) {
                const auto& sl = bs[(size_t) rows[t]];
                if (!parity.record(ver, t, sl.parity_id, sl.produced, pos[t], outb[t], err)) { std::printf("ERR %s%c", err.c_str(), 10); return false; }
            }
            const Clock::time_point w1 = Clock::now();
            if (!ver.commit_slots(err))''')
s=s.replace('                    const int32_t y = outb[t];', '''                    int32_t y = outb[t];
                    if (!parity.record(vk, t, sl.parity_id, sl.produced, sl.p, y, err)) { std::printf("ERR %s%c", err.c_str(), 10); return false; }''')
assert 'sl.parity_id = parity_id' in s
p.write_text(s)
