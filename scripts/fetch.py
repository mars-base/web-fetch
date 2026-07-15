#!/usr/bin/env python3
"""
Universal web content extractor (Scrapling + html2text).
Returns clean Markdown with headings, links, images, lists, and code blocks.

Usage:
  python3 fetch.py <url> [max_chars] [--stealth] [--cloak] [--json] [--proxy PROXY]

Modes:
  (default)   Fast HTTP fetch via Fetcher — works for most sites (~1-3s)
  --stealth   Headless browser via StealthyFetcher — for JS-rendered or
              anti-scraping sites like WeChat, Zhihu, Juejin (~5-15s)
  --cloak     CloakBrowser — stealth Chromium for advanced bot detection

Proxy:
  --proxy PROXY  Proxy URL (e.g. "http://127.0.0.1:8118").
                  If not set, reads from HTTPS_PROXY / HTTP_PROXY /
                  https_proxy / http_proxy / all_proxy env vars.

Examples:
  python3 fetch.py https://sspai.com/post/73145
  python3 fetch.py https://mp.weixin.qq.com/s/xxx 30000 --stealth
  python3 fetch.py https://zhuanlan.zhihu.com/p/12345 --stealth
  python3 fetch.py https://example.com --proxy http://127.0.0.1:8118
"""

import sys
import os
import re
import json
import logging


def check_dependencies():
    """Check if required packages are installed and provide install instructions."""
    required = []
    optional = []

    try:
        import scrapling  # noqa: F401
    except ImportError:
        required.append("scrapling")
    try:
        import html2text  # noqa: F401
    except ImportError:
        required.append("html2text")

    try:
        import cloakbrowser  # noqa: F401
    except ImportError:
        optional.append("cloakbrowser")
    try:
        import curl_cffi  # noqa: F401
    except ImportError:
        optional.append("curl_cffi")
    try:
        import browserforge  # noqa: F401
    except ImportError:
        optional.append("browserforge")

    if required:
        print(
            f"Error: missing required dependencies: {', '.join(required)}\n"
            f"Install with:\n"
            f"  python3 -m pip install {' '.join(required)}",
            file=sys.stderr,
        )
        sys.exit(1)

    if optional:
        print(
            f"Warning: missing optional dependencies: {', '.join(optional)}\n"
            f"Some features may not work (e.g. CloakBrowser mode, stealth enhancement).\n"
            f"Install with:\n"
            f"  python3 -m pip install {' '.join(optional)}",
            file=sys.stderr,
        )


def fix_lazy_images(html_raw):
    """
    Promote data-src to src for lazy-loaded images (WeChat, Zhihu, etc.).
    Many Chinese platforms use data-src for the real image URL while src
    holds a tiny placeholder. html2text only reads src, so we swap them.
    """
    return re.sub(
        r'<img([^>]*?)\sdata-src="([^"]+)"([^>]*?)>',
        lambda m: f'<img{m.group(1)} src="{m.group(2)}"{m.group(3)}>',
        html_raw,
    )


# CSS selectors in priority order — the first match with enough content wins.
# Covers most blog/article platforms without needing per-site customization.
CONTENT_SELECTORS = [
    "article",
    "main",
    ".post-content",
    ".entry-content",
    ".article-content",
    ".article-body",
    ".article-detail",         # 36kr
    ".article-holder",         # InfoQ
    ".post_body",              # 163.com (NetEase)
    ".markdown-body",          # GitHub
    ".Post-RichText",          # Zhihu
    "#article_content",        # CSDN
    ".article-area",           # Juejin
    ".ssa-article",            # Toutiao
    '[role="article"]',
    '[itemprop="articleBody"]',
]

# WeChat has a unique DOM structure — try these first for mp.weixin.qq.com
WECHAT_SELECTORS = [
    "div#js_content",
    "div.rich_media_content",
]

# Minimum characters for a selector match to be considered "real content"
MIN_CONTENT_LENGTH = 200


def html_to_markdown(html_raw, max_chars=30000):
    """Convert raw HTML to clean Markdown."""
    import html2text

    html_raw = fix_lazy_images(html_raw)

    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.body_width = 0       # No line wrapping
    h.skip_internal_links = True
    h.ignore_emphasis = False

    md = h.handle(html_raw)
    md = re.sub(r"\n{3,}", "\n\n", md).strip()
    return md[:max_chars]


def extract_content(page, url, max_chars=30000):
    """
    Try content selectors to find the article body.
    Returns (markdown_text, matched_selector).
    """
    is_wechat = "mp.weixin.qq.com" in url
    selectors = (WECHAT_SELECTORS + CONTENT_SELECTORS) if is_wechat else CONTENT_SELECTORS

    for selector in selectors:
        els = page.css(selector)
        if els:
            md = html_to_markdown(els[0].html_content, max_chars)
            if len(md) >= MIN_CONTENT_LENGTH:
                return md, selector

    # Fallback: convert the entire page
    md = html_to_markdown(page.html_content, max_chars)
    return md, "body(fallback)"


def _suppress_scrapling_logs():
    """Scrapling's logger is noisy (deprecation warnings, fetch info). Silence it."""
    logging.getLogger("scrapling").setLevel(logging.CRITICAL)


def fetch_fast(url, max_chars=30000, timeout=15, proxy=None):
    """
    Fast HTTP fetch — no JavaScript execution.
    Works for most blogs and static sites.
    """
    from scrapling.fetchers import Fetcher
    _suppress_scrapling_logs()

    kwargs = {"timeout": timeout, "stealthy_headers": True}
    if proxy:
        kwargs["proxy"] = proxy
    page = Fetcher().get(url, **kwargs)
    return extract_content(page, url, max_chars)


def fetch_stealth(url, max_chars=30000, timeout=30000, proxy=None):
    """
    Headless browser fetch — executes JavaScript, bypasses anti-scraping.
    Required for: WeChat articles, Zhihu, Juejin, and other JS-rendered pages.
    Slower (~5-15s) but more reliable for protected content.
    """
    from scrapling.fetchers import StealthyFetcher
    _suppress_scrapling_logs()

    kwargs = {"headless": True, "network_idle": True, "timeout": timeout}
    if proxy:
        kwargs["proxy"] = proxy

    page = StealthyFetcher().fetch(url, **kwargs)
    return extract_content(page, url, max_chars)


def fetch_cloakbrowser(url, max_chars=30000, timeout=60000, proxy=None):
    """
    CloakBrowser fallback — stealth Chromium with anti-detection patches.
    Use when both Scrapling modes fail or are blocked by advanced bot detection.
    """
    import cloakbrowser

    launch_kwargs = {"headless": True}
    if proxy:
        launch_kwargs["proxy"] = {"server": proxy}

    browser = cloakbrowser.launch(**launch_kwargs)
    try:
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=timeout)

        # Wrap playwright page so extract_content can use CSS selectors
        class _Element:
            def __init__(self, html):
                self.html_content = html

        class _Page:
            def __init__(self, page):
                self._page = page
                self.html_content = page.content()

            def css(self, selector):
                try:
                    elements = self._page.query_selector_all(selector)
                    return [_Element(e.evaluate("el => el.outerHTML")) for e in elements]
                except Exception:
                    return []

        return extract_content(_Page(page), url, max_chars)
    finally:
        browser.close()


def get_proxy(cli_proxy=None):
    """
    Resolve proxy from CLI arg or environment variables.
    Priority: --proxy > HTTPS_PROXY > HTTP_PROXY > https_proxy > http_proxy > all_proxy
    Returns None if no proxy is configured.
    """
    if cli_proxy:
        return cli_proxy
    for var in ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy", "all_proxy"):
        val = os.environ.get(var)
        if val:
            return val
    return None


def fetch(url, max_chars=30000, stealth=False, cloak=False, proxy=None):
    """
    Main entry point. Fetches URL and returns (markdown, selector, mode).
    Strategy:
      1. cloak (CloakBrowser) — for WeChat, which blocks Scrapling fast/stealth
      2. fast (HTTP) — unless stealth or cloak is forced
      3. stealth (Scrapling headless) — auto-fallback when fast result is too short
      4. cloak (CloakBrowser) — final fallback when stealth also fails

    proxy: optional proxy URL string (e.g. "http://127.0.0.1:8118").
           If not set, reads from HTTPS_PROXY / HTTP_PROXY / all_proxy env vars.
    """
    resolved_proxy = get_proxy(proxy)
    if cloak:
        md, selector = fetch_cloakbrowser(url, max_chars, proxy=resolved_proxy)
        return md, selector, "cloak"

    if stealth:
        md, selector = fetch_stealth(url, max_chars, proxy=resolved_proxy)
        return md, selector, "stealth"

    # WeChat aggressively blocks Scrapling fast/stealth modes — go straight to cloak.
    if "mp.weixin.qq.com" in url:
        md, selector = fetch_cloakbrowser(url, max_chars, proxy=resolved_proxy)
        return md, selector, "cloak(wechat-direct)"

    # Try fast mode first
    md, selector = fetch_fast(url, max_chars, proxy=resolved_proxy)

    # If fast mode got barely any content, the page likely needs JS rendering
    if len(md) < MIN_CONTENT_LENGTH:
        try:
            md_stealth, sel_stealth = fetch_stealth(url, max_chars, proxy=resolved_proxy)
            if len(md_stealth) > len(md):
                return md_stealth, sel_stealth, "stealth(auto-fallback)"
        except Exception:
            pass  # Fall through to cloakbrowser
        else:
            # Stealth returned short/empty content too
            if len(md_stealth) < MIN_CONTENT_LENGTH:
                pass  # Fall through to cloakbrowser
            else:
                return md_stealth, sel_stealth, "stealth(auto-fallback)"

        # Final fallback: CloakBrowser
        try:
            md_cloak, sel_cloak = fetch_cloakbrowser(url, max_chars, proxy=resolved_proxy)
            if len(md_cloak) > len(md):
                return md_cloak, sel_cloak, "cloak(auto-fallback)"
        except Exception:
            pass  # Stick with the best result so far

    return md, selector, "fast"


def main():
    # Force UTF-8 output on Windows (default codepage can't encode Chinese chars)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    if len(sys.argv) < 2:
        print(
            "Usage: python3 fetch.py <url> [max_chars] [--stealth] [--cloak] [--json] [--proxy PROXY]\n"
            "\n"
            "Options:\n"
            "  max_chars   Maximum output characters (default: 30000)\n"
            "  --stealth   Use Scrapling headless browser for JS-rendered pages\n"
            "  --cloak     Use CloakBrowser (anti-detection Chromium)\n"
            "  --json      Output as JSON with metadata\n"
            "  --proxy     Proxy URL (e.g. 'http://127.0.0.1:8118').\n"
            "              Also reads from HTTPS_PROXY / HTTP_PROXY env vars.\n",
            file=sys.stderr,
        )
        sys.exit(1)

    url = sys.argv[1]
    args = sys.argv[2:]

    stealth = "--stealth" in args
    cloak = "--cloak" in args
    json_output = "--json" in args

    # Parse --proxy VALUE
    proxy = None
    try:
        proxy_idx = args.index("--proxy")
        proxy = args[proxy_idx + 1]
        # Remove --proxy and its value from args
        args.pop(proxy_idx)      # value
        args.pop(proxy_idx)      # flag
    except (ValueError, IndexError):
        pass

    args = [a for a in args if not a.startswith("--")]
    max_chars = int(args[0]) if args else 30000

    try:
        md, selector, mode = fetch(url, max_chars, stealth=stealth, cloak=cloak, proxy=proxy)

        if json_output:
            result = {
                "url": url,
                "mode": mode,
                "selector": selector,
                "content_length": len(md),
                "content": md,
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(md)

    except Exception as e:
        error_msg = f"Error fetching {url}: {type(e).__name__}: {e}"
        if json_output:
            print(json.dumps({"url": url, "error": error_msg}, ensure_ascii=False))
        else:
            print(error_msg, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    check_dependencies()
    main()
