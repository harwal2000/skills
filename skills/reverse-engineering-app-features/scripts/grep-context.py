"""Print bounded context around matches in a minified file (whole lines can be megabytes).

usage: python3 -I grep-context.py FILE PATTERN [BEFORE=200] [AFTER=300] [MAX=5] [--re]

PATTERN is a literal string unless --re is given (Python regex). Offsets printed are BYTE offsets,
the same as `LC_ALL=C grep -b -o -F`, so they can be cited and found again.
Exit codes: 0 matches found, 1 no match, 2 bad arguments.
"""
import re
import sys

def die(message, code):
    print(message, file=sys.stderr)
    sys.exit(code)


args = [a for a in sys.argv[1:] if a != "--re"]
use_re = "--re" in sys.argv
if len(args) < 2 or not all(a.isdigit() for a in args[2:5]):
    die(__doc__.strip(), 2)
path, pattern = args[0], args[1]
before, after, limit = (int(args[i]) if len(args) > i else d for i, d in ((2, 200), (3, 300), (4, 5)))

try:
    data = open(path, "rb").read()
except OSError as e:
    die(f"error: {e}", 2)
try:
    regex = re.compile(pattern.encode() if use_re else re.escape(pattern.encode()))
except re.error as e:
    die(f"error: bad regex: {e}", 2)

count = 0
for m in regex.finditer(data):
    if count >= limit:
        break
    count += 1
    print(f"--- {path} @byte {m.start()}")
    print(data[max(0, m.start() - before):m.end() + after].decode("utf-8", "replace"))
if count == 0:
    die(f"no match for {pattern!r} in {path}", 1)
