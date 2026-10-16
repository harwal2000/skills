# Skills

My Claude Code skills. Each one is a folder under `skills/` with a `SKILL.md` that Claude loads when the task matches its description.

| Skill | Use it when |
|---|---|
| [`reverse-engineering-app-features`](skills/reverse-engineering-app-features/) | You want to know how another app or website does something (e.g. "how does Notion handle Markdown shortcuts?"). Claude reads the shipped code with [REA](https://github.com/morluto/rea), run one command at a time through `npx` with nothing installed, and falls back to grep for big minified bundles. It's research only, and you get a report with code evidence for each answer. |
| [`scraping-account-data`](skills/scraping-account-data/) | You want your own data (orders, rides, bills, watch history) out of a website you log into that has no export. You log in yourself in the browser; Claude replays the site's own data requests and saves the raw responses. It never handles your password. |

## Install

Clone the repo and link the skills you want into `~/.claude/skills/`:

```bash
git clone https://github.com/harwal2000/skills.git
cd skills
ln -s "$PWD/skills/reverse-engineering-app-features" ~/.claude/skills/
ln -s "$PWD/skills/scraping-account-data" ~/.claude/skills/
```

Restart Claude Code, then ask for the task in plain words. To update later, run `git pull`.

If you'd rather not keep a clone, copy a skill's folder into `~/.claude/skills/` instead. You'll then need to copy it again to get updates.

## License

[MIT](LICENSE)
