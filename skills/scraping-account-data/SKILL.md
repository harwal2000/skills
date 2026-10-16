---
name: scraping-account-data
description: Use when the user wants their own data out of a website they log into — order history, rides, bookings, transactions, watch or listening history, bills, statements, saved items — and there is no usable export, or an existing scraper repo is outdated, broken, or wants their password.
---

# Scraping Account Data

## Overview

The user logs in with their own hands in the Playwright browser; you find the data source the site's own pages use and replay it **inside the page** (session cookies + real headers), saving raw responses to disk. Never handle credentials.

## When to Use

- "Get my <service> history", "scrape my orders/trips/bookings", "use this scraper repo"
- **Old scraper repos** (requests + password/OTP login): read them on GitHub for endpoint names and selectors only. Never run them — bot checks (HTTP 202 empty body, captchas) break them, and they want the password.

**Official export first.** Google Takeout, "Download your data", GDPR/DPDP requests, public APIs, email receipts. Slow exports take days — ask the user to request one at the start, then scrape now and cross-check by ID when it arrives.

## Workflow

1. **Gitignore the output dir before writing anything** (`data/<service>/` or the project's equivalent); confirm with `git check-ignore`. Raw data has addresses, phones, GPS.
2. **Navigate, hand over login.** Open the account page; tell the user to type phone/password/OTP in the browser window and reply when done. Never ask for codes in chat.
3. **Discover the source** (`browser-snippets.md` §1). Reload with a listener and classify:
   - **JSON XHR/fetch** (best) — note list endpoint, pagination shape (`next_url`/cursor, `page_number`, offset = last id, `endOfList`), and the detail endpoint (open one item).
   - **GraphQL** — one `POST /graphql`; record the full request body (operationName, query or persisted-query hash, variables).
   - **Server-rendered HTML** — data arrives in the `document` response; fetch list *and* detail pages in-page and parse with `DOMParser`; save raw HTML too so you can re-parse.
   - **Partitioned lists** — if the list is split by a filter (year dropdown, date range, tabs like archived/cancelled/digital), read every filter value and paginate each one.
4. **Auth.** Try `fetch(url, {credentials: 'include'})` first. If that returns 401/403/empty, copy the non-browser headers from a live request (§2) — copy, never guess values. Log header *names* only; never print or save values.
5. **Paginate in the background inside the page** (§2): `window.__x = {running, pages, error}`, 1.5s between requests, retries, poll with short evaluates. Every response: if it's a login/captcha page (URL contains signin/captcha, or HTML instead of expected JSON), set `error` and stop — these often come back as 200.
6. **Save before navigating** (§3). Any `goto`/reload wipes `window`. `browser_evaluate` with an absolute `filename` path, returning an **object** (`JSON.stringify` double-encodes). ~5 MB per file is fine; split per batch beyond that.
7. **Signed/unreplayable requests** (request-signature headers, nonce bodies, persisted queries that reject edits): visit each detail page and passively capture its responses (§4).
8. **Build + verify** (below) with a parser script outside the data dir, then an insights note. Follow the repo's existing layout if there is one (e.g. `tools/<service>/build_db.py`, notes next to the data); otherwise ask.

**Read-only.** Replay only what the page itself requests to *display* data. GraphQL: judge by operation (`query`/Get*/List*), never `mutation`. Never reorder, cancel, rate, archive, delete.

## Verification — do all of these

| Check | Why |
|---|---|
| Pagination ended because the cursor/list ran out, not an error or login redirect | Silent truncation |
| Look for "view older orders in app" text at the end | Web views cap history (Swiggy: ~11 months) |
| Don't trust the site's count endpoint or header alone | Blinkit's said 40; the list had 83 |
| Components sum to total per row (items + fees − discounts = paid) | Catches parser drift; if the site omits lines for old records, say so — don't force it |
| Item prices sum to item total | Per-unit vs line-total confusion |
| Unique IDs; dedupe exact duplicates | Exports and receipts double-list |
| Cross-check another source by ID (export, receipts) | Proves coverage |
| Every list/tab/filter was covered (archived, cancelled, other years, sub-services) | "All orders" often spans several lists |

## Parsing notes

- **Server-driven UI APIs** (`snippets`, `widgets`, `widget_type`, `layout`): walk widgets in order, collect each widget's `text` fields, map by known labels. A one-text widget is often a label for the next one — whitelist label names or every field shifts.
- Amounts may be paise/cents; "FREE" = 0; leading "-" = discount; strip currency symbols and Indian comma grouping. Keep currencies separate.
- Timestamps: purchases → user's timezone; trips/travel → the record's local time.
- Keep raw files dated (`orders-raw-YYYY-MM-DD.json`) next to the built SQLite.

## Git

Commit only: the gitignore line, the parser script, any README/index row. Raw files and the SQLite stay local. Stage explicit paths (never `git add -A` in a dirty tree); commit only when asked.

## Common Mistakes

- One long synchronous evaluate loop — times out; background it and poll.
- Returning bulk data into chat instead of `filename`.
- Snippet listeners left attached — `page.off` them, or repeated runs stack handlers.
- Filtering discovery to xhr/fetch on an HTML-rendered site and concluding "no data source".
