---
name: web-fetch
description: >
  Extract article content from any URL as clean Markdown.
  Uses Scrapling script as primary method (with auto fast→stealth fallback,
  and CloakBrowser as final fallback for advanced bot detection).
  Jina Reader as alternative for simple pages.
  Preserves headings, links, images, lists, and code blocks.
  Use this skill whenever the user wants to fetch, read, extract, scrape, or summarize
  content from a URL — including blog posts, news articles, WeChat articles (微信公众号),
  documentation pages, or any web page. Also trigger when the user says things like
  "帮我读一下这篇文章", "抓取这个网页", "提取正文", or "read this page for me".
---

# Web Content Fetcher

Given a URL, return its main content as clean Markdown — headings, links, images, lists, code blocks all preserved.

No initialization step needed. Works on Linux, macOS, and Windows.

## Recommended: Replace Built-in Fetch & WebFetch

To make Claude Code always use `/web-fetch` instead of the built-in `Fetch` and `WebFetch` tools, add the following to your `~/.claude/CLAUDE.md`:

```markdown
## Web Fetch

Always use the `/web-fetch` skill for fetching web content — do not use the built-in Fetch or WebFetch tools.
`/web-fetch` supports anti-scraping bypass, JS rendering, and CloakBrowser for higher quality output.
```

This ensures every project automatically prefers `/web-fetch` over the default tools.

## Skill Invocation

When this skill is invoked, treat `args` as a URL (and optional flags) and run `fetch.py`.

### Fetch command

```bash
python3 <SKILL_DIR>/scripts/fetch.py "<url>" [max_chars] [--stealth] [--cloak] [--json]
```

`<SKILL_DIR>` is the directory where this SKILL.md lives.

## Extraction Strategy

Always try **one method per URL** — don't cascade blindly. Pick the right one upfront.

```
URL
 │
 ├─ 1. Scrapling script (preferred)
 │     Run fetch.py — check the domain routing table to decide fast vs --stealth.
 │     Works for most sites. Returns clean Markdown directly.
 │
 ├─ 2. CloakBrowser (fallback when Scrapling is blocked)
 │     fetch.py --cloak
 │     Stealth Chromium with anti-detection patches. Useful for advanced bot
 │     protection, captchas, or when Scrapling stealth fails.
 │
 └─ 3. Jina Reader (fallback — only if Scrapling/CloakBrowser fails or dependencies not installed)
       web_fetch("https://r.jina.ai/<url>")
       Free tier: 200 req/day. Fast (~1-2s), good Markdown output.
       Does NOT work for: WeChat (403), some Chinese platforms.
```

### Scrapling script

```bash
python3 <SKILL_DIR>/scripts/fetch.py "<url>" [max_chars] [--stealth] [--cloak] [--json]
```

`<SKILL_DIR>` is the directory where this SKILL.md lives.

> **Model instruction:** Run `fetch.py` with the provided URL/flags.

The script has three modes built in:
- **Default (fast):** HTTP fetch, ~1-3s, works for most sites
- **`--stealth`:** Headless browser, ~5-15s, for JS-rendered or anti-scraping sites
- **`--cloak`:** CloakBrowser stealth Chromium, ~10-20s, for advanced bot protection

When run without flags, the script automatically falls back through the chain:
fast → stealth → cloak. So you rarely need to specify `--cloak` manually — the only
reason to force it is when you already know the site needs it (see routing table),
which saves the earlier attempts.

## Domain Routing

Use this table to pick the right mode on the first call:

| Domain | Command | Why |
|--------|---------|-----|
| `mp.weixin.qq.com` | `fetch.py <url>` (auto → cloak) | WeChat blocks fast/stealth, CloakBrowser required |
| `zhuanlan.zhihu.com` | `fetch.py <url> --stealth` | Anti-scraping + JS |
| `juejin.cn` | `fetch.py <url> --stealth` | JS-rendered SPA |
| `sspai.com` | `fetch.py <url>` | Static HTML |
| `blog.csdn.net` | `fetch.py <url>` | Static HTML |
| `ruanyifeng.com` | `fetch.py <url>` | Static blog |
| `openai.com` | `fetch.py <url>` | Static HTML |
| `blog.google` | `fetch.py <url>` | Static HTML |
| Heavily protected / captcha sites | `fetch.py <url> --cloak` | CloakBrowser anti-detection |
| Everything else | `fetch.py <url>` | Auto-fallback handles it |

## Script Options

```bash
# Basic — auto-selects fast, stealth, or cloak
python3 <SKILL_DIR>/scripts/fetch.py "https://sspai.com/post/73145"

# Force stealth for known JS-heavy sites
python3 <SKILL_DIR>/scripts/fetch.py "https://mp.weixin.qq.com/s/xxx" --stealth

# Force cloak for sites with advanced bot protection
python3 <SKILL_DIR>/scripts/fetch.py "https://example.com/protected" --cloak

# Limit output to 15000 characters (default: 30000)
python3 <SKILL_DIR>/scripts/fetch.py "https://example.com/article" 15000

# JSON output with metadata (url, mode, selector, content_length)
python3 <SKILL_DIR>/scripts/fetch.py "https://example.com" --json
```

## Install Dependencies

First use only — the script checks and tells you if anything is missing:

```bash
pip install scrapling html2text cloakbrowser
```

If on system-managed Python (macOS/Linux), add `--break-system-packages` or use a venv. On Windows, install Python from the Microsoft Store or ensure `python3` is available in PATH.

## Failure Rules

- Same URL fails once → give up, tell the user "unable to extract content from this URL"
- Do not retry — each failed call wastes context tokens
