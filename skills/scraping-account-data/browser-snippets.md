# Browser snippets (Playwright MCP)

Code is for `browser_run_code_unsafe` (gets `page`) unless marked `browser_evaluate` (runs in the page). Every snippet that adds a listener removes it with `page.off`.

## 1. Discover the data source

```js
async (page) => {
  const reqs = [];
  const h = async r => {
    const t = r.request().resourceType(), u = r.url();
    if (!['xhr', 'fetch', 'document'].includes(t) || /analytics|google|facebook|events|clarity|doubleclick/.test(u)) return;
    let body = ''; try { body = (await r.text()).slice(0, 400); } catch (e) {}
    reqs.push({ t, m: r.request().method(), u: u.slice(0, 200), s: r.status(), post: (r.request().postData() || '').slice(0, 300), body });
  };
  page.on('response', h);
  await page.goto('https://example.com/account/orders');
  await page.waitForTimeout(5000);
  page.off('response', h);
  return reqs;
}
```
- JSON in an xhr/fetch body → JSON API. `POST /graphql` → GraphQL (record full `post`). Data only in the `document` body → server-rendered HTML (§5).
- Then open one item (navigate to its `href` if an overlay blocks the click) and repeat to find the detail source.

## 2. Capture headers + paginate in background

```js
async (page) => {
  let hdr = null, post = null;
  const h = r => { if (/\/api\/v2\/order\//.test(r.url()) && !hdr) { hdr = r.headers(); post = r.postData(); } };
  page.on('request', h);
  await page.reload(); await page.waitForTimeout(4000);
  page.off('request', h);
  if (!hdr) return 'no headers captured';
  const drop = /^(sec-|user-agent|referer|accept-encoding|accept-language|origin|host|cookie$)/i;
  const keep = Object.fromEntries(Object.entries(hdr).filter(([k]) => !drop.test(k)));
  return page.evaluate(([h]) => {
    const s = window.__x = { running: true, pages: [], error: null };
    (async () => {
      try {
        for (let n = 1; n <= 200; n++) {
          const r = await fetch(`/api/v2/order/?page_number=${n}`, { headers: h, credentials: 'include' });
          if (/signin|login|captcha/i.test(r.url) || !(r.headers.get('content-type') || '').includes('json')) { s.error = 'login/captcha page: ' + r.url; break; }
          const j = await r.json();
          s.pages.push(j);
          if (r.status !== 200 || !j.orders?.length || j.endOfList) break;
          await new Promise(r => setTimeout(r, 1500));
        }
      } catch (e) { s.error = String(e); }
      s.running = false;
    })();
    return 'started; headers: ' + Object.keys(h).join(',');   // names only
  }, [keep]);
}
```
**Pagination variants** (swap the loop body):
- Cursor: `url = j.pagination?.next_url`; stop when missing or repeated.
- Offset by id: next offset = last item's id; stop when no *new* ids arrive.
- GraphQL: `const b = JSON.parse(post); b.variables.cursor = next; fetch('/graphql', {method: 'POST', headers: h, credentials: 'include', body: JSON.stringify(b)})`. Check `j.errors`. If a persisted-query hash rejects the edited body, fall back to §4.

Poll (`browser_evaluate`): `() => ({ running: window.__x.running, pages: window.__x.pages.length, error: window.__x.error })`

## 3. Save to disk (before any navigation)

`browser_evaluate` with `filename: "/abs/path/data/<service>/orders-raw-YYYY-MM-DD.json"` (absolute paths work):
```js
() => ({ fetched_at: new Date().toISOString(), source: '<endpoint>', pages: window.__x.pages })
```
Return the object, not `JSON.stringify(...)` (that double-encodes). Verify with `python3 -I -c "import json; json.load(open('...'))"`.

## 4. Passive capture for signed requests

```js
async (page) => {
  const ids = [/* from the saved list */];
  const out = {}; let cur = null;
  const h = async r => { if (cur && /get-page\/ORDER_DETAILS/.test(r.url())) { try { out[cur].push(await r.json()); } catch (e) {} } };
  page.on('response', h);
  for (const id of ids) {
    cur = id; out[id] = [];
    await page.goto(`https://example.com/order/${id}`);
    for (let i = 0; i < 16 && !out[id].some(x => x?.endOfPage); i++) await page.waitForTimeout(500);
    await page.waitForTimeout(1200);
  }
  page.off('response', h);
  return page.evaluate(o => {               // survives later navigations within the tab
    const prev = JSON.parse(sessionStorage.getItem('__xd') || '{}');
    window.__xd = Object.assign(prev, o);
    sessionStorage.setItem('__xd', JSON.stringify(window.__xd));
    return Object.keys(window.__xd).length;
  }, out);
}
```
Batch ~10 per call; save `window.__xd` with §3 at the end. If sessionStorage overflows (~5 MB), save each batch to its own file instead.

## 5. Server-rendered HTML pages

Run with `browser_evaluate` (background pattern from §2):
```js
() => {
  const s = window.__x = { running: true, pages: [], error: null };
  (async () => {
    for (let i = 0; i < 500; i += 10) {
      const r = await fetch(`/your-orders/orders?startIndex=${i}`, { credentials: 'include' });
      if (/signin|captcha/i.test(r.url)) { s.error = 'login/captcha: ' + r.url; break; }
      const html = await r.text();
      const d = new DOMParser().parseFromString(html, 'text/html');
      const cards = [...d.querySelectorAll('.order-card')];
      s.pages.push({ startIndex: i, html, parsed: cards.map(c => c.innerText) });
      if (!cards.length) break;
      await new Promise(r => setTimeout(r, 1500));
    }
    s.running = false;
  })();
  return 'started';
}
```
Confirm selectors against one `browser_snapshot` first. Keep raw `html` so a selector fix only needs a re-parse, not a re-scrape. Fail loudly if a page is empty while the site's header says there are records.
