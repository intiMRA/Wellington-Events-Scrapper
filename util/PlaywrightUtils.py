import random
import re
from pathlib import Path

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, Error as PlaywrightError

from util.Logger import Logger

# Sites the first-run setup opens so you can log in (Facebook) and/or clear an anti-bot /
# cookie-consent challenge (Ticketek, Ticketmaster) once — that state then persists in the profile.
_SETUP_SITES = [
    ("Facebook", "https://www.facebook.com/login"),
    ("Ticketek", "https://premier.ticketek.co.nz/search/SearchResults.aspx?k=wellington"),
    ("Ticketmaster", "https://www.ticketmaster.co.nz/search?q=wellington"),
]


def chrome_profile_dir() -> str:
    # One shared Chrome profile for every stealth scraper, anchored to the repo root via this
    # file's location so it resolves identically regardless of the current working directory or
    # machine. Created if missing, so a fresh clone / other laptop just works: run once, log in,
    # and the session persists across runs. Gitignored (see .gitignore: .chrome-profile/).
    profile = Path(__file__).resolve().parent.parent / ".chrome-profile"
    profile.mkdir(parents=True, exist_ok=True)
    return str(profile)

# Anti-automation launch flags mirroring the old undetected-chromedriver scrapers.
_STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--start-maximized",
]

# Non-breaking / narrow / thin space variants Playwright's inner_text() preserves.
_UNICODE_SPACES = re.compile(r"[     ]")


def real_user_agent(browser: Browser) -> str:
    # Playwright's bundled Chromium reports "HeadlessChrome/<version>", which some sites' WAFs
    # block (e.g. cecwellington.ac.nz 404s the whole page). Read the live UA and drop the
    # "Headless" marker so it matches a normal Chrome of the exact version we run — derived from
    # the browser, so it tracks whatever `playwright install` provides with no version to hardcode.
    page = browser.new_page()
    try:
        ua = page.evaluate("() => navigator.userAgent")
    finally:
        page.close()
    return ua.replace("HeadlessChrome", "Chrome")


def new_context(browser: Browser) -> BrowserContext:
    # Browser context with a real-Chrome UA (see real_user_agent) so headless-blocking WAFs
    # let us through. Use this instead of a bare browser.new_page().
    return browser.new_context(user_agent=real_user_agent(browser))


def human_delay(page: Page, min_seconds: float = 0.8, max_seconds: float = 2.5) -> None:
    # Look less robotic on bot-protected sites: a few random mouse moves (with intermediate
    # steps so the path is smooth, not teleporting), then a randomized pause.
    size = page.viewport_size or {"width": 1280, "height": 800}
    for _ in range(random.randint(2, 4)):
        page.mouse.move(random.randint(0, size["width"]), random.randint(0, size["height"]),
                        steps=random.randint(4, 12))
        page.wait_for_timeout(random.randint(60, 250))
    page.wait_for_timeout(int(random.uniform(min_seconds, max_seconds) * 1000))


def launch_stealth(playwright: Playwright, headless: bool = False) -> BrowserContext:
    # Anti-bot setup for the scrapers that used undetected-chromedriver (Ticketek, Humanitix,
    # Ticketmaster, Facebook, AllEventsIn): automation flags stripped, a maximized window, and
    # navigator.webdriver hidden. Headed by default (headless is more easily detected). Uses ONE
    # shared persistent Chrome profile (chrome_profile_dir) so logins/cookies persist across runs
    # and every stealth scraper shares the same session. If a site still blocks you,
    # `pip install playwright-stealth` and call stealth_sync(page) after new_page().
    profile = chrome_profile_dir()
    Logger.info(f"launching stealth Chrome (profile: {profile})")
    context = playwright.chromium.launch_persistent_context(
        profile, headless=headless, args=_STEALTH_ARGS, no_viewport=True,
        # Drop Playwright's default --enable-automation switch: it's what shows the "Chrome is
        # being controlled by automated test software" infobar and sets navigator.webdriver.
        ignore_default_args=["--enable-automation"])
    context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    _ensure_profile_setup(context, headless)
    return context


def _ensure_profile_setup(context: BrowserContext, headless: bool) -> None:
    # First run on a fresh profile: open each setup site so the user can log in / clear any
    # anti-bot challenge, then persist. Guarded by a marker file so it only happens once.
    profile = Path(chrome_profile_dir())
    # Per-site markers, so setup is resumable: if you set up some sites then kill the script,
    # a re-run only prompts for the sites you haven't confirmed yet.
    pending = [(name, url) for name, url in _SETUP_SITES if not (profile / f".setup_{name.lower()}").exists()]
    if not pending:
        return
    if headless:
        Logger.warning("New Chrome profile but running headless — run headed once to log in; "
                       "walled scrapers may fail until then.")
        return
    page = stealth_page(context)
    Logger.info("Profile setup — log in / clear any check for each site, then press Enter to SAVE it.")
    for name, url in pending:
        try:
            page.goto(url, wait_until="domcontentloaded")
        except PlaywrightError as error:
            Logger.warning(f"could not open {name} for setup ({error})")
        try:
            input(f"[setup] Set up {name}, then press Enter here to save it (don't kill the script)... ")
        except EOFError:
            Logger.warning("No interactive input available — skipping the rest of setup (sites you "
                           "already saved stay saved). Re-run from an interactive console to finish.")
            return
        # Mark this site done the instant you confirm — a later kill won't re-prompt for it.
        (profile / f".setup_{name.lower()}").write_text("done\n")
        Logger.info(f"{name} setup saved.")
    Logger.info(f"Profile setup complete — saved to {profile}")


def stealth_page(context: BrowserContext) -> Page:
    # A persistent context already has a default page open — reuse it instead of opening a second
    # window with new_page().
    return context.pages[0] if context.pages else context.new_page()


def wait_for_items(locator: Locator, timeout_ms: int = 10000) -> int:
    # Wait (event-driven, up to timeout) for at least one match to attach, so a lazily-rendered
    # listing isn't read with `.all()` before it has populated (which silently skips events).
    # Non-throwing: returns the final match count (0 if none appeared within the timeout).
    try:
        locator.first.wait_for(state="attached", timeout=timeout_ms)
    except PlaywrightError:
        pass
    return locator.count()


def normalize_text(text: str) -> str:
    # Playwright's inner_text() preserves non-breaking / narrow spaces that Selenium's .text
    # collapsed to regular spaces, which breaks string splitting and date parsing on scraped
    # text (e.g. Eventbrite renders "date  •  time"). Fold them to regular spaces.
    return _UNICODE_SPACES.sub(" ", text)


def goto_with_retry(page: Page, url: str, attempts: int = 3, wait_ms: int = 2000, wait_until: str = "domcontentloaded") -> None:
    # Retries transient navigation failures (e.g. net::ERR_NETWORK_CHANGED from a
    # Wi-Fi/VPN blip) so one hiccup doesn't abort a whole scrape run.
    # Defaults to "domcontentloaded" (HTML parsed) rather than "load" (all images/ads/trackers):
    # locators auto-wait for their targets anyway, so waiting for full load just wastes time on
    # ad-heavy sites. Pass wait_until="networkidle"/"load" explicitly where a page needs it.
    for attempt in range(attempts):
        try:
            page.goto(url, wait_until=wait_until)
            return
        except PlaywrightError as error:
            if attempt == attempts - 1:
                raise
            Logger.warning(f"goto {url} failed ({error}); retry {attempt + 1}/{attempts - 1}")
            page.wait_for_timeout(wait_ms)
