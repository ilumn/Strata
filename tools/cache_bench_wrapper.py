"""Reuse the established staggered harness with an explicit reserve and startup timer."""
from pathlib import Path

source = Path(__file__).resolve().parents[2] / 'Strata-prefill-budget/tools/bench_concurrency.py'
code = source.read_text()
changes = {
    "    values['--vram-reserve-mib'] = '2560'": "    values.setdefault('--vram-reserve-mib', '2560')",
    "        proc = subprocess.Popen(": "        startup_started = time.perf_counter()\n        proc = subprocess.Popen(",
    "                    multi = 'multiplex' in line": "                    report['startup_s'] = time.perf_counter() - startup_started\n                    multi = 'multiplex' in line",
}
for old, new in changes.items():
    assert code.count(old) == 1, old
    code = code.replace(old, new)
exec(compile(code, str(source), 'exec'), {'__name__': '__main__', '__file__': str(source)})
