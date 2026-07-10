# web-fetch

Extract article content from any URL as clean Markdown.

`web-fetch` is a Claude Code skill that fetches web pages and returns structured,
readable Markdown — headings, links, images, lists, and code blocks are preserved.
It uses [Scrapling](https://github.com/D4Vinci/Scrapling) as the primary fetcher,
[CloakBrowser](https://github.com/CloakHQ/CloakBrowser) as a final fallback for
heavily protected sites, and [Jina Reader](https://r.jina.ai/) as a lightweight
alternative when neither browser-based method is available.

## Features

- **Fast mode** — plain HTTP fetch for static sites (~1–3s)
- **Stealth mode** — headless browser for JS-rendered or anti-scraping sites
- **CloakBrowser mode** — anti-detection Chromium for advanced bot protection
- **Auto fallback** — fast → stealth → cloak without manual intervention
- **Clean Markdown output** — selectors for most blog/article platforms
- **JSON output** — metadata including URL, mode, selector, content length

## Install

```bash
git clone https://github.com/mars-base/web-fetch.git
cd web-fetch
pip install scrapling html2text cloakbrowser
```

On Windows, **install Python from the Microsoft Store** (`python3` is available out of the box). Alternatively, ensure `python3` is available in PATH. On macOS/Linux with system-managed Python, add `--break-system-packages` or use a venv.

## Usage

### As a script

```bash
python3 scripts/fetch.py "https://example.com/article"

# Force stealth for JS-heavy sites
python3 scripts/fetch.py "https://mp.weixin.qq.com/s/xxx" --stealth

# Force CloakBrowser for protected sites
python3 scripts/fetch.py "https://example.com/protected" --cloak

# Limit output and return JSON
python3 scripts/fetch.py "https://example.com" 15000 --json
```

### As a Claude Code skill

Symlink or copy the skill into your Claude Code skills directory:

```bash
ln -s ~/bucket/web-fetch ~/.claude/skills/web-fetch
```

Then invoke it with:

```
/web-fetch https://example.com/article
```

> **Tip:** If the built-in `WebFetch` tool fails (blocked by anti-scraping, JS rendering, etc.), use `/web-fetch` skill as a drop-in replacement — it supports anti-bot bypass, JS rendering, and CloakBrowser.

### Configure global CLAUDE.md (recommended)

To make Claude Code always use `/web-fetch` instead of the built-in `Fetch` and `WebFetch` tools, add the following to your `~/.claude/CLAUDE.md`:

```markdown
## Web Fetch

Always use the `/web-fetch` skill for fetching web content — do not use the built-in Fetch or WebFetch tools.
`/web-fetch` supports anti-scraping bypass, JS rendering, and CloakBrowser for higher quality output.
```

## Domain routing tips

| Domain | Suggested command |
|--------|-------------------|
| `mp.weixin.qq.com` | default (auto → cloak) |
| `zhuanlan.zhihu.com` | `--stealth` |
| `juejin.cn` | `--stealth` |
| `sspai.com`, `blog.csdn.net`, `ruanyifeng.com` | default (fast) |
| Heavily protected / captcha sites | `--cloak` |

## Project structure

```
web-fetch/
├── SKILL.md              # Claude Code skill definition
├── README.md             # This file
└── scripts/
    └── fetch.py          # Main fetch/extract script
```

## License

MIT
