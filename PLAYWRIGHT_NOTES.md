# Playwright locator cheatsheet (personal notes)

My reference for migrating the Selenium scrapers to Playwright's **sync** API.
Not a committed standard — just notes.

```python
from playwright.sync_api import sync_playwright, Page
```

---

## Migration roadmap (effort tiers)

17 scrapers total. Tier is driven by anti-bot defenses and browser tricks, not line count.

| Scraper | Tier | Status | Why |
|---|---|---|---|
| RougueScrapper | 🟢 Easy | ✅ done | plain locators, one browser |
| UnderTheRaderScrapper | 🟢 Easy | ✅ done | list + detail, Load More loop |
| ValhallaScrapper | 🟢 Easy | ✅ done | scroll-to-load, plain locators |
| FringeScrapper | 🟢 Easy | ✅ done | plain locators |
| WellingtonHighschoolScrapper | 🟢 Easy | ✅ done | infinite scroll (`slow_scroll_to_bottom`) |
| WellingtonNZScrapper | 🟡 Medium | ✅ done | `switch_to.window(current)` was a no-op, not a real tab |
| EventFinderScrapper | 🟡 Medium | ⬜ todo | multi-date logic, larger |
| RoxyScrapper | 🟡 Medium | ⬜ todo | festival file output |
| EventbriteScrapper | 🟡 Medium | ✅ done | **iframe** (`frame_locator`); many find_element-as-existence bugs |
| AllEventsInScrapper | 🟡 Medium | ✅ done | new tabs + persistent profile (`launch_persistent_context`) |
| HumanitixScrapper | 🔴 Hard | ✅ done | anti-bot → `launch_stealth` (real UA + flags + webdriver hidden) |
| TicketekScrapper | 🔴 Hard | ⬜ todo | **undetected-chromedriver** + spawns a 2nd driver |
| FacebookScrapper | 🔴 Hard | ⬜ todo | login, ActionChains/send_keys, persistent profile, anti-bot |
| TicketmasterScrapper | 🔴 Hard | ⬜ todo | 423 lines, hybrid requests/bs4 + Selenium, **iframe** |
| SanFranScrapper | ⚪ None | — leave | `requests` + bs4, no browser |
| WoapScrapper | ⚪ None | — leave | `requests` + bs4, no browser |
| WellingtonHeritageFestivalScrapper | ⚪ None | — leave | `requests` + bs4, no browser |

🔴 Hard = plain Playwright may be blocked; needs `playwright-stealth` / real user-agent /
headed mode and trial-and-error. Do these last. See "Anti-bot" below.

---

## Why the `.` in `page.locator(".display_title_1")`

`page.locator(...)` uses **CSS selector syntax by default**. The `.` is CSS, not
Playwright — it means "class". Selenium's `By.CLASS_NAME` took the *bare* name
(`"display_title_1"`) and added the dot internally; Playwright makes you write the CSS
directly.

CSS basics:
- `.foo`   → element with class `foo`
- `#foo`   → element with id `foo`
- `a`      → all `<a>` tags
- `[name='email']` → attribute match
- `.card > a`      → direct child; `.card a` → any descendant

---

## Selenium `By.*` → Playwright

| Selenium | Playwright |
|---|---|
| `By.CLASS_NAME, "foo"` | `".foo"` |
| `By.ID, "foo"` | `"#foo"` |
| `By.TAG_NAME, "a"` | `"a"` |
| `By.NAME, "email"` | `"[name='email']"` |
| `By.CSS_SELECTOR, ".x > a"` | `".x > a"` (unchanged) |
| `By.XPATH, "//div/a"` | `"//div/a"` (auto-detected) or `"xpath=//div/a"` |
| `By.LINK_TEXT, "Book"` | `page.get_by_role("link", name="Book")` |

**`find_element` → `.first`** (Playwright is strict: a multi-match locator raises unless
you pick one). **`find_elements` → `.all()`** (returns `list[Locator]`).

```python
driver.find_element(By.CLASS_NAME, "title").text          # Selenium
page.locator(".title").first.inner_text()                 # Playwright

driver.find_elements(By.CLASS_NAME, "vevent")             # Selenium
page.locator(".vevent").all()                             # Playwright
```

---

## XPath in Playwright

Auto-detected when the string starts with `//`, `.//`, or `..`. Add `xpath=` when it
doesn't start that way (or to be explicit/safe).

```python
driver.find_element(By.XPATH, "//div[@class='event']//a")     # Selenium
page.locator("//div[@class='event']//a").first                # Playwright (auto)
el.locator("xpath=.//a").first                                # relative from a parent locator
```

### `contains(@class, 'foo')` — the one to watch

XPath `contains(@class, 'foo')` is a **substring** match on the whole class attribute, so
it also matches `foobar`, `unfoo`, etc. The CSS translations:

| XPath | CSS | Meaning |
|---|---|---|
| `//div[contains(@class,'foo')]` | `[class*='foo']` | substring (matches `foobar` too) — faithful to XPath |
| `//div[@class='foo']` | `.foo` (or `[class='foo']` for exact-attr) | has class `foo` |
| `//div[contains(concat(' ',@class,' '),' foo ')]` | `.foo` | the "proper has-class" XPath idiom → just `.foo` |

Rule of thumb: if the XPath was *really* trying to say "has class foo" (the usual case),
migrate it to `.foo` — shorter and robust. Only use `[class*='foo']` when you genuinely
want the loose substring behavior.

More `contains` examples:

```python
# //a[contains(text(),'Load more')]
page.get_by_text("Load more")                 # exact-ish, semantic (best)
page.locator("a", has_text="Load more")       # <a> containing that text
page.locator("a:has-text('Load more')")       # CSS pseudo, same idea

# //div[contains(@class,'card')]//h2
page.locator(".card h2")                      # if 'card' is a real class
page.locator("[class*='card'] h2")            # if you need substring

# //input[contains(@id,'search')]
page.locator("[id*='search']")

# //li[contains(@data-status,'active')]
page.locator("[data-status*='active']")
```

Playwright's team recommends CSS / role / text locators over XPath: XPath is brittle,
**doesn't pierce shadow DOM**, and reads worse. For semantic lookups prefer:

```python
page.get_by_role("button", name="Submit")
page.get_by_text("Sold out")
page.get_by_label("Email")
page.get_by_placeholder("Search events")
```

---

## Other things that bit / will bite

**Strict mode.** `.locator(sel)` matching >1 element raises when you call an action —
including `.inner_text()`, `.click()`, `.get_attribute()`, and **`.wait_for()`** (yes, even
the wait: `locator(".vevent").wait_for()` throws "strict mode violation" if 148 match). Use
`.first`, `.last`, or `.nth(i)`: to wait for a list to appear, `locator(sel).first.wait_for()`.
`.all()` and `.count()` never raise.

**`.count()` checks existence, NOT visibility — for a `.click()`, use `.is_visible()`.** A
control can be in the DOM (`.count()` > 0) but hidden, and `.click()` then blocks the FULL
timeout (30s) waiting for it to become visible, then throws. Guard clicks on possibly-hidden
elements with visibility:
```python
more = page.get_by_text("more dates").first
if more.is_visible():          # instant; count() would pass even when hidden
    more.click()
```
`.count()` is the right guard for **reads** (`inner_text`/`get_attribute` on a present element);
`.is_visible()` is the right guard for **clicking** something that might be hidden. (Bit
Humanitix: a hidden "More dates" span passed `.count()` and hung the click 30s.)

**Waiting for things to pop up (instead of `sleep`).** This is where Playwright beats
Selenium — prefer waiting for a *condition*, not a fixed delay.

- **Single element:** don't wait at all. Actions/reads (`.inner_text()`, `.click()`,
  `.get_attribute()`) auto-wait for attached+visible+stable (default 30s). Most `goto` +
  `sleep` pairs → just delete the sleep. `WebDriverWait`/`expected_conditions` disappear.
- **`.all()` / `.count()` do NOT wait** — they snapshot the DOM *now*. Before collecting a
  list, wait for the first match:
  ```python
  page.locator(".event-date").first.wait_for()   # blocks until it appears
  dates = page.locator(".event-date").all()       # now safe
  ```
- **`wait_for()` defaults to `state="visible"` — Selenium's `presence_of_element_located` is
  `attached`.** If an element is in the DOM but not visible (covered by a region-specific
  overlay, zero-size, `display:none` until interaction), the default `wait_for()` times out
  after 30s even though it's present. Port `presence_of_element_located` → `wait_for(state="attached")`,
  and read its text with `text_content()` (works when hidden; `inner_text()` returns "" for
  non-visible). This bit WellingtonNZ — passed from a US probe, timed out from NZ.
- **Explicit waits when you need a condition:**
  ```python
  loc.wait_for(state="visible")                 # or "attached"/"hidden"/"detached"
  page.wait_for_load_state("networkidle")       # after an action that fires XHRs
  page.goto(url, wait_until="networkidle")      # navigation variant
  from playwright.sync_api import expect
  expect(loc).to_be_visible()                   # auto-retrying assertion
  page.wait_for_function("() => document.querySelectorAll('.card').length > 5")  # arbitrary JS
  ```
- **Genuine random delay only:** `page.wait_for_timeout(ms)` — Playwright's honest "this is
  a real sleep". Use it when nothing deterministic exists to wait on (rare).

**`inner_text()` vs `text_content()`.**
- `.inner_text()` ≈ Selenium `.text` — rendered, visible, whitespace-normalized. Use this.
- `.text_content()` — raw DOM text incl. hidden nodes, not normalized.

**`get_attribute()` returns `Optional[str]`.** Guard it (that's why the migrated code has
`... or ""` and `if event_url is None: continue`).

**`find_element` used as an existence check → `.count()`, and mind the iframe scope.**
Selenium's `find_element` *throws* when absent, so `try: find_element(X); return []; except: pass`
means "if X exists, bail." A naive port to `page.locator(X)` / `page.get_by_text(X)` does NOT
throw — the `return []` runs unconditionally and the function always bails. Translate the
existence test explicitly:
```python
if page.get_by_text("not found").count():   # or page.locator(sel).count()
    return []
```
And for iframes: `page.frame_locator(...)` is lazy — you must **assign it and query through it**
(`frame = page.frame_locator(...); frame.locator(...)`); calling it and then using
`page.locator(...)` searches the main document, not the frame. (Both bit Eventbrite — two
`return []`s that always fired, and a discarded `frame_locator`.)

**`get_attribute` returns the RAW HTML attribute, not the resolved DOM property.** This is a
Selenium trap: Selenium's `get_attribute("href")` gave you the *property* (always absolute);
Playwright gives you the literal attribute, so a relative `href="/events-1/foo"` stays
relative and `page.goto(...)` throws `Cannot navigate to invalid URL`. For `href`/`src`, read
the property to get an absolute URL:
```python
url = link.get_attribute("href")          # "/events-1/foo"  (raw, may be relative)
url = link.evaluate("a => a.href")         # "https://site.com/events-1/foo"  (resolved)
img = el.evaluate("img => img.src")        # resolved src the same way
# or: from urllib.parse import urljoin; url = urljoin(page.url, raw_href)
```

**Locators are lazy + chainable/scoped.** A `Locator` is a query, not an element — it
re-resolves each use (no stale-element errors). Scope by chaining:
```python
card = page.locator(".vevent").first
card.locator("a").first.get_attribute("href")     # searches WITHIN card
```

**Useful locator methods.**
```python
loc.count()                       # int, no wait
loc.nth(2)                        # 3rd match
loc.filter(has_text="Music")      # narrow a set
loc.all()                         # list[Locator]
loc.is_visible()                  # bool
loc.get_attribute("href")         # Optional[str]
loc.inner_text() / loc.text_content()
```

**`execute_script` → `evaluate` — and the `return` trap.**
Selenium's `execute_script` runs a *function body*, so it needs `return`. Playwright's
`evaluate` takes a JS **expression** (or an arrow function) — a bare `return` throws
`SyntaxError: Illegal return statement`.
```python
driver.execute_script("return document.body.scrollHeight")   # Selenium
page.evaluate("document.body.scrollHeight")                   # ✅ expression, NO return

driver.execute_script("return arguments[0].innerText", el)   # Selenium, with arg
el.evaluate("e => e.innerText")                               # ✅ arrow fn on a locator

page.evaluate("() => { const h = document.body.scrollHeight; return h; }")  # multi-stmt → arrow fn, return OK
```
`evaluate` returns `Any`; coerce/annotate at the call site (`height: int = page.evaluate(...)`).

**Scrolling.**
```python
driver.execute_script("window.scrollBy(0, 1000)")            # Selenium (no return → unchanged)
page.evaluate("window.scrollBy(0, 1000)")                    # literal port
page.mouse.wheel(0, 1000)                                    # ✅ native; fires a real wheel event (lazy-load friendly)
page.locator(".load-more").scroll_into_view_if_needed()     # ✅ scroll to an element — no pixels
page.evaluate("window.scrollTo(0, document.body.scrollHeight)")   # jump to bottom once
```
**Confirm the pagination mechanism before writing a scroll loop.** Not all "more content" is
scroll-triggered. Three kinds: (1) true infinite scroll — scrolling loads more; (2) a
Load-more button — click to append; (3) a cumulative URL param — `?page=N` returns N pages of
items at once. Probe first: scroll to the bottom and check whether the item count actually grows
(`locator(".item").count()`). If it doesn't, scrolling is a no-op and you need the button or the
URL param. WellingtonNZ looked like lazy-scroll but was cumulative `&page=N` (page 2 = 50 items,
page 3 = 75, ...) — the fix was looping that URL, not scrolling.

Infinite-scroll loop (the Selenium `slow_scroll_to_bottom` pattern):
```python
prev = 0
while True:
    page.mouse.wheel(0, 2000)
    page.wait_for_timeout(500)                     # Playwright's sleep; let content load
    height = page.evaluate("document.body.scrollHeight")   # NO return
    if height == prev:
        break
    prev = height
```

**Lifecycle (sync).**
```python
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    ...
    browser.close()
```
**One `sync_playwright()` per run — never nest it.** Opening a second `with sync_playwright()`
while one is already active (e.g. a `get_categories()` helper that starts its own browser)
throws `It looks like you are using Playwright Sync API inside the asyncio loop`. The sync API
runs its own event loop and there can only be one. Open the browser once in `fetch_events` and
pass `page` into every helper. Need a second page/tab? `browser.new_page()` — not a new
`sync_playwright()`. (This is the trap when porting a helper that used to build its own driver,
like Ticketek's `sub_driver`.)

`headless=True` is the scraping default. For anti-bot sites (Ticketek/Facebook that used
`undetected_chromedriver`), plain Playwright may get blocked — that's where you'll need
`playwright-stealth` or a real user-agent/headed mode, and it's the risky part of the
migration.

**Default user agent gets blocked — set one.** Playwright's default UA string contains
`HeadlessChrome`, and some sites' WAFs silently reject it — e.g. cecwellington.ac.nz returns a
**404 with an empty page** (no error, no elements, `title == ''`), so it looks like your
selectors broke when really the page never loaded. This bit WellingtonHighschool. Selenium's
`webdriver.Chrome()` sent a normal Chrome UA, so it never showed. Fix — set a real UA on the
context (not just headed mode; headed with the default UA is *still* blocked). Derive it from
the running browser and strip `Headless`, so it tracks the actual bundled version — no hardcoded
`Chrome/126` to bump; `playwright install` updates it for you:
```python
from util.PlaywrightUtils import new_context   # or real_user_agent(browser)
browser = p.chromium.launch(headless=True)
context = new_context(browser)                 # browser.new_context(user_agent=real_user_agent(browser))
page = context.new_page()
```
`real_user_agent` reads `navigator.userAgent` off a throwaway page and does
`.replace("HeadlessChrome", "Chrome")`. Don't hardcode a version string — the old UC scrapers
pinned `Chrome/randint(100,115)`, which is already stale.
Symptom to recognize: empty `page.title()`, `locator("a").count() == 0` — check the response
status (`resp = page.goto(url); print(resp.status)`); a 404/403 on a page that works in your
browser means UA/bot blocking, not a selector bug.

**Headed vs headless / debugging.** Playwright defaults to **headless** (no window), unlike
Selenium's `webdriver.Chrome()` which was headed — that's why the browser stopped popping up
after migrating. To watch it run:
```python
browser = p.chromium.launch(headless=False)              # show the window
browser = p.chromium.launch(headless=False, slow_mo=500) # + 500ms pause between actions
page.pause()                                             # freeze + open the Playwright Inspector to step through
```
Keep `headless=True` for the real scraper (faster, works on CI); flip to `False` only while
debugging locally. To avoid editing code each time, drive it off an env var:
```python
import os
browser = p.chromium.launch(headless=os.getenv("HEADFUL") != "1")   # run with HEADFUL=1 to see it
```

**Timeouts.** Per-call: `page.locator(".x").first.inner_text(timeout=5000)` (ms).
Page-wide default: `page.set_default_timeout(15000)`.

**Transient navigation errors.** `page.goto` can throw `net::ERR_NETWORK_CHANGED`,
`ERR_CONNECTION_RESET`, timeouts, etc. from a passing Wi-Fi/VPN blip — nothing to do with your
code. One bad `goto` aborts the whole run (especially painful after all URLs are collected), so
navigate through a retry helper instead of calling `goto` directly:
```python
from util.PlaywrightUtils import goto_with_retry   # catches playwright.sync_api.Error, retries
goto_with_retry(page, url)                          # instead of page.goto(url)
```
`playwright.sync_api.Error` (aliased `PlaywrightError`) is the base class for these — catch it,
`page.wait_for_timeout(...)`, retry a few times, re-raise on the last attempt.

---

## Constructs used by the other scrapers (full coverage)

Everything below appears somewhere in the remaining Selenium scrapers. This is the complete
translation set for this repo.

**iframes** (`TicketmasterScrapper`, `EventbriteScrapper`). Selenium switches context; Playwright
scopes into the frame with `frame_locator` — no switching, no switching back.
```python
# Selenium
driver.switch_to.frame(iframe_element)
driver.find_element(By.ID, "x").click()
driver.switch_to.default_content()
# Playwright
frame = page.frame_locator("iframe[src*='checkout']")   # or "iframe#id"
frame.locator("#x").click()
# no default_content() needed — page.locator(...) calls are unaffected
```

**New tabs / windows** (`AllEventsInScrapper`, `WellingtonNZScrapper`). Don't poll
`window_handles`; capture the popup as it opens.
```python
# Selenium
all_windows = driver.window_handles
driver.switch_to.window(all_windows[-1])
# Playwright — `a.opens-new-tab` is a PLACEHOLDER; use the real link the site opens a tab with
with page.expect_popup() as popup_info:
    page.locator("a.opens-new-tab").click()
new_page = popup_info.value
new_page.wait_for_load_state()
# already-open tabs: context.pages ; focus one: page.bring_to_front()
```
⚠️ Only use `expect_popup` when a click **genuinely opens a new tab**. Many Selenium scrapers
call `driver.switch_to.window(driver.current_window_handle)` — that switches to the tab you're
*already on*, i.e. a **no-op**. There is no popup; just **delete it** and keep using `page`.
(WellingtonNZ had exactly this — a copied `expect_popup` + placeholder selector made `click()`
hang for 30s on an element that never existed.)

**Form input** (`FacebookScrapper`). `send_keys` → `fill` (clears + types); key presses →
`press`.
```python
el.clear(); el.send_keys("Wellin")      # Selenium
loc.fill("Wellin")                       # Playwright — clears then types (preferred)
loc.press_sequentially("Wellin")         # char-by-char (old .type()), for autocompletes
loc.press("Enter")                       # send_keys(Keys.ENTER)
loc.click()                              # auto-waits for actionable
```

**ActionChains / hover / drag** (`FacebookScrapper`).
```python
ActionChains(driver).move_to_element(el).perform()   # Selenium
loc.hover()                                           # Playwright
source.drag_to(target)                               # drag & drop
page.mouse.move(x, y) / page.mouse.click(x, y)       # raw pointer
```

**Persistent Chrome profile** — `user-data-dir` (`AllEventsInScrapper`, `FacebookScrapper`, for
staying logged in). Use a *persistent context*, which replaces `launch()` + `new_context()` and
returns a context (no separate browser object).
```python
# Selenium
options.add_argument(f"user-data-dir={profile_path}")
driver = webdriver.Chrome(options=options)
# Playwright
context = playwright.chromium.launch_persistent_context(
    user_data_dir=profile_path,
    headless=False,
)
page = context.new_page()
...
context.close()
```

**Anti-bot / undetected-chromedriver** (`TicketekScrapper`, `HumanitixScrapper`). Use the shared
helper — `context = launch_stealth(playwright, headless=False); page = context.new_page()` — which
bundles the automation flags, real UA, maximized window, and hidden `navigator.webdriver`. It maps
the old `ChromeOptions` args to `launch(args=...)` + `new_context(user_agent=...)`:
```python
# Selenium (undetected)
options = uc.ChromeOptions()
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument(f"user-agent=Mozilla/5.0 ... Chrome/120.0.0.0 Safari/537.36")
driver = uc.Chrome(options=options, headless=False)
# Playwright
browser = playwright.chromium.launch(
    headless=False,
    args=["--disable-blink-features=AutomationControlled", "--disable-infobars"],
)
context = browser.new_context(
    user_agent="Mozilla/5.0 ... Chrome/120.0.0.0 Safari/537.36",
    viewport={"width": 1920, "height": 1080},   # replaces --start-maximized
)
page = context.new_page()
```
Plain Playwright ≠ undetected-chromedriver. If a site blocks you: `pip install playwright-stealth`
→ `from playwright_stealth import stealth_sync; stealth_sync(page)`, keep `headless=False`, use a
real user agent. **These (Ticketek / Humanitix / Facebook) are the high-risk migrations** — expect
trial and error, unlike the drop-in ones.

**Second browser / sub-driver** (`TicketekScrapper` spawns `sub_driver = uc.Chrome(...)`). Don't
launch a whole second browser — open another page (or context for isolation):
```python
sub_page = browser.new_page()          # shares browser, cheap
sub_ctx = browser.new_context()        # isolated cookies/storage, then sub_ctx.new_page()
```

**Not migrated:** `SanFranScrapper`, `WoapScrapper`, `WellingtonHeritageFestivalScrapper` use
`requests` + BeautifulSoup only (no browser) — leave them as-is. `TicketmasterScrapper` mixes
`requests`/bs4 with Selenium; only its Selenium parts (iframe, `execute_script`, `get_attribute`)
need porting.

