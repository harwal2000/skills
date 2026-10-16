"""Extract one webpack module from minified chunks, ready for prettier.

usage: python3 -I extract-webpack-module.py ASSET_DIR MODULE_ID OUT_FILE

Finds the first .js file in ASSET_DIR (not recursive) that defines MODULE_ID, in any of these forms:
  webpack 5:  ,123456(e,t,n){...}      webpack 4:  ,123456:function(e,t,n){...}  or  ,123456:(e,t,n)=>{...}
The module ends at the next module header in the same chunk, or at the end of the file if it's the last one.
OUT_FILE gets `const m={<module>};` so prettier parses it as is. If prettier reports a SyntaxError, the end
boundary was wrong: look at the chunk around the printed end offset.

Prints: chunk, start/end byte offsets (cite these), and the module's export map (`.d(t,{name:()=>local})`).
Module ids show up at call sites as `i(123456).name` / `(0,i(123456).name)(...)`; a barrel export
`name:()=>p().other` with `p=()=>r(999)` means: look up `other` in module 999.
Exit codes: 0 found, 1 not found, 2 bad arguments.
"""
import os
import re
import sys

def die(message, code):
    print(message, file=sys.stderr)
    sys.exit(code)


if len(sys.argv) != 4 or not sys.argv[2].isdigit():
    die(__doc__.strip().split("\n\n")[1] + "\nMODULE_ID must be numeric. More: read this file's docstring.", 2)
asset_dir, mid, out = sys.argv[1], sys.argv[2], sys.argv[3]
if not os.path.isdir(asset_dir):
    die(f"error: {asset_dir} is not a directory", 2)

HEADER = rb"(?:\(\w,\w,\w\)\{|:function\(\w(?:,\w){0,2}\)\{|:\(\w(?:,\w){0,2}\)=>\{)"
start_re = re.compile(rb"(?:^|(?<=[,{]))" + mid.encode() + HEADER)
next_re = re.compile(rb"\},\d{1,7}" + HEADER)

hits = []
for name in sorted(os.listdir(asset_dir)):
    if not name.endswith(".js"):
        continue
    data = open(os.path.join(asset_dir, name), "rb").read()
    m = start_re.search(data)
    if m:
        hits.append((name, data, m))

if not hits:
    die(f"error: module {mid} not found in any .js file in {asset_dir}", 1)

name, data, m = hits[0]
nxt = next_re.search(data, m.end())
if nxt:
    end = nxt.start() + 1
else:  # last module in the chunk: stop before the chunk wrapper (`}]);`) or a trailing runtime function
    tail = re.search(rb"\}(?=\}(?:,(?:function\b|\(?\w*\)?=>)|\]\)[;,]?\s*(?://[^\n]*\s*)?$))", data[m.end():])
    end = m.end() + tail.start() + 1 if tail else len(data)
module = data[m.start():end]
with open(out, "wb") as f:
    f.write(b"const m={" + module + b"};\n")
print(f"{name}: module {mid} bytes {m.start()}-{end} ({end - m.start()} bytes) -> {out}")
exports = re.search(rb"\.d\(\w,\{([^}]*)\}", module[:3000])
if exports:
    print("exports:", exports.group(1).decode("utf-8", "replace")[:600])
if len(hits) > 1:
    print("also defined in:", ", ".join(h[0] for h in hits[1:6]))
