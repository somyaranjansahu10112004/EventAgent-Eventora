from playwright.async_api import async_playwright

_playwright = None
_browser = None
_context = None


async def init_browser():
    """
    Initialize Playwright once and reuse the browser.
    """
    global _playwright, _browser, _context

    if _browser:
        return

    try:
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(headless=True)
        _context = await _browser.new_context(locale="en-US", timezone_id="Asia/Kolkata")
    except Exception:
        await close_browser()
        raise


async def close_browser():
    """
    Close browser and Playwright gracefully.
    """
    global _playwright, _browser, _context

    try:
        if _context:
            await _context.close()
    except Exception:
        pass

    try:
        if _browser:
            await _browser.close()
    except Exception:
        pass

    try:
        if _playwright:
            await _playwright.stop()
    except Exception:
        pass

    _playwright = None
    _browser = None
    _context = None


def clean_text(text: str):
    """
    Minimal cleanup.
    Removes common social media UI while keeping
    the event description intact.
    """

    stop_words = [
        "Add a comment",
        "Reply",
        "See translation"
    ]

    for word in stop_words:
        idx = text.find(word)
        if idx != -1:
            text = text[:idx]

    return text.strip()


async def scrape_page(url: str):
    """
    Scrape a page and return BOTH:

    - raw HTML (for Facebook parser)
    - cleaned visible text (for Gemini)
    """

    global _context

    if _context is None:
        await init_browser()

    page = await _context.new_page()

    try:

        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=15000
        )

        await page.wait_for_timeout(4000)

        try:
            await page.wait_for_load_state(
                "networkidle",
                timeout=3000
            )
        except Exception:
            pass

        # Full HTML source
        html = await page.content()

        # Visible text
        body = await page.locator("body").inner_text()

        text = clean_text(body)

        return {
            "html": html,
            "text": text
        }

    except Exception as e:

        print(f"⚠️ Scraping failed: {url}")
        print(e)

        return {
            "html": "",
            "text": ""
        }

    finally:

        try:
            await page.close()
        except Exception:
            pass