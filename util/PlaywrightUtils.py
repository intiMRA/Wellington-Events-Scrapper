import random
import re

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, Error as PlaywrightError

from util.Logger import Logger

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


def launch_stealth(playwright: Playwright, headless: bool = False, user_data_dir: str = "") -> BrowserContext:
    # Anti-bot setup for the scrapers that used undetected-chromedriver (Ticketek, Humanitix,
    # ...): automation flags stripped, real UA, a maximized real window, and navigator.webdriver
    # hidden. Headed by default (headless is more easily detected). Pass user_data_dir to use a
    # persistent Chrome profile (keeps logins across runs, e.g. Facebook) WITH the stealth flags.
    # If a site still blocks you, add `pip install playwright-stealth` + stealth_sync(page).
    if user_data_dir:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir, headless=headless, args=_STEALTH_ARGS, no_viewport=True)
    else:
        browser = playwright.chromium.launch(headless=headless, args=_STEALTH_ARGS)
        context = browser.new_context(user_agent=real_user_agent(browser), no_viewport=True)
    context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return context


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
