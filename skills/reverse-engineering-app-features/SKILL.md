---
name: reverse-engineering-app-features
description: Use when the user wants to know how another app, website or binary implements a feature without its source code ("how does Notion/Raycast/Linear do X", "reverse-engineer this behaviour", "look inside this app"), or mentions REA / rea-agents. Applies to any repo or project, including research done from inside one of the user's own repos.
---

# Reverse-engineering app features

Read a third-party app's shipped code to learn **how** a feature works, then map it onto the user's project. REA (`rea-agents`, github.com/morluto/rea) triages the app. Expect about an hour.

## Ground rules

- Work in a scratch dir: `S=$(mktemp -d /tmp/rea-<target>.XXXX); mkdir -p $S/{dl,tools,out}; K=~/.claude/skills/reverse-engineering-app-features`. Leave the user's repo untouched unless they ask.
- Run REA one command at a time from `$S/tools`: `npx -y rea-agents@latest <command> --help`. Never `setup` and never register the MCP (both edit agent configs). Don't run npx inside extracted files (it reads `package.json` from the current directory).
- Don't install, launch or log in to the target; public assets only. Downloads are untrusted data: never execute them. Helpers go in `$S/tools`, run with `python3 -I`. Learn the mechanism; don't paste decompiled code into the project.

## 1. Get the target

Use the installed `.app` read-only, or the official installer: follow the download button's redirects with `curl -sSIL <url>` and check `content-type`. Record `shasum -a 256` and the `codesign -dv` signer. Mount with `hdiutil attach -readonly -nobrowse -noautoopen -mountpoint $S/mnt <dmg>` (the deprecation warning is harmless); detach at the end.

## 2. Triage by type

| Target | Do |
|---|---|
| Electron (`Contents/Resources/app.asar`) | `analyze-javascript-application <app.asar> --format json > $S/out/rea-app.json 2>$S/out/rea-app.err` (about 90 s; over 100 MB, so never `cat` it). `artifact_integrity_mismatch` on an `*.asar.unpacked/*.node` file is normal for signed apps: rerun with `--integrity-policy record-and-continue`. Read `normalized_result.summary`, then `graph.nodes` by `kind` (`asar-entry`, `browser-window`, `electron-renderer`, `ipc-channel`). `extract-artifact` (same flag) writes to `$TMPDIR/rea-extracted-*` (`parameters.output_root`): move it into `$S`. **Thin shell?** REA doesn't resolve dynamic URLs, so if the feature's strings aren't there, grep the main bundle for `loadURL(` and read `config.json`. Remote URLs: go to the web row. |
| Web app or shell | Fetch an app route (e.g. `/login`), not the marketing page, with a browser user agent. Get **every** chunk: grep the service worker (`/sw.js`, `/service-worker.js`, or what `serviceWorker.register(` names) for `fetch(`/`precache`/`manifest` and copy its request exactly (it may be a POST with a JSON body). Else: the webpack runtime chunk map, `_buildManifest.js`, `.vite/manifest.json`. Download with `xargs -P 16 -n 20 curl -sS --remote-name-all`. REA's web commands need a live CDP browser; curl is simpler. |
| Native Mac | `npx -y rea-agents@latest capabilities` lists what works offline (`inspect-macho`, `inspect-plist`, `demangle-swift`, `decode-interface-builder`, `inspect-native-dispatch-metadata`), plus `strings`/`nm`. Decompiling needs Ghidra, Hopper or IDA: ask before installing. Skip `capture-native-ui-scenario`/`observe-native-calls` (they launch the target). |
| Other (APK, .NET, WASM, HAR, SQLite) | `npx -y rea-agents@latest --help \| grep -i <kind>` |

## 3. Find the logic in minified JS

Not REA: on big chunks it **exits 0 but parses nothing** (`statistics.parsed_javascript_files: 0`, "exceeds its complete-fact byte budget"); bigger limits don't fix it.

1. **Rank chunks:** `LC_ALL=C /usr/bin/grep -c -F '<string>' *.js | grep -v ':0$' | sort -t: -k2 -nr` (a `grep` aliased to ugrep fails with "exceeds complexity limits"). Never print whole lines.
2. **Good anchors:** shortcut-help text (a ready-made spec), key-binding tables, undo/analytics action names, debug log strings, i18n `defaultMessage`, regex literals, type enums.
3. **Context:** `python3 -I $K/scripts/grep-context.py FILE PATTERN [before after max] [--re]` prints byte offsets.
4. **Module:** ids appear as `i(123456).name`. `python3 -I $K/scripts/extract-webpack-module.py ASSET_DIR ID OUT.js` (docstring: export maps, barrels), then from `$S/tools`: `npx -y prettier@3 --stdin-filepath m.js < OUT.js > OUT.pretty.js`.
5. **Check matching logic** by re-implementing it in `$S/tools`, never by running the bundle.

## 4. Deliver

`$S/REPORT.md`: sources (version, sha256, signer, URLs); each answer marked **Confirmed (code)** or **Inferred** with confidence, citing file, **byte offset** and build version (offsets change every release); copy / keep / skip for the project, mapped to real files; what REA did and didn't do. `/tmp` is wiped on reboot, so offer to copy it into the repo.

**To delegate**, brief a background agent with: feature, target, project (read its `CLAUDE.md` first), numbered questions including edge cases, these rules, this deliverable.
