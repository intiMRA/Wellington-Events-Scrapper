#!/usr/bin/env python3
"""Catch the common Selenium -> Playwright migration mistakes.

Only lints files that import Playwright, so not-yet-migrated Selenium scrapers and the
requests/bs4 ones are skipped automatically.

Usage:
    python scripts/lint_playwright.py                 # lint scrapers/
    python scripts/lint_playwright.py scrapers/X.py   # lint specific files
    python scripts/lint_playwright.py --strict        # treat warnings as failures

Exit code 1 if any ERROR (or any WARN with --strict) is found — CI/pre-commit friendly.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List, Tuple

# Per-line checks: (compiled regex, level, message). Lines that are pure comments are skipped.
LINE_CHECKS: List[Tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"\bfrom selenium\b|\bimport selenium\b|\bwebdriver\b|\bBy\.[A-Z]|\.find_element|"
                r"\bswitch_to\b|\.execute_script\(|undetected_chromedriver|\buc\.Chrome"),
     "ERROR", "Selenium leftover — port to Playwright (locator / frame_locator / page.evaluate)"),
    (re.compile(r'\.evaluate\(\s*f?["\']\s*return\b'),
     "ERROR", 'evaluate() takes an expression, not a statement — drop "return" (or use an arrow fn)'),
    (re.compile(r"""locator\(\s*['"]\[@"""),
     "ERROR", "XPath predicate [@...] inside a CSS locator — use [attr=...] or an xpath= selector"),
    (re.compile(r"""locator\(\s*['"]//\["""),
     "ERROR", "XPath with no node test (//[...]) — use //*[...] or a CSS selector"),
    (re.compile(r"""=['"][^'"\]]*\]['"]"""),
     "ERROR", "Malformed selector — unclosed quote before ] (e.g. [class*='foo] )"),
    (re.compile(r"""\.get_attribute\(\s*['"](href|src)['"]"""),
     "WARN", "get_attribute('href'/'src') returns the RAW attribute (may be relative) — "
             "use .evaluate('e => e.href') for an absolute URL"),
    (re.compile(r"^\s*except\s*:"),
     "ERROR", "Bare except — narrow it (e.g. except PlaywrightError:)"),
    (re.compile(r"(?<![\w.])print\("),
     "ERROR", "Use Logger (util/Logger.py), not print() — a migrated scraper should have no prints"),
    (re.compile(r"\bbrowser\.new_page\(\)"),
     "WARN", "Bare browser.new_page() — use new_context(browser).new_page() for the real UA"),
    (re.compile(r"(?<![\w.])page\.goto\("),
     "WARN", "Bare page.goto() — use goto_with_retry(page, url) for transient-error resilience"),
    (re.compile(r"(?<![\w.])\.text\b(?!_)"),
     "WARN", ".text is a Selenium-ism — Playwright locators use .inner_text() / .text_content()"),
]

# Extracts the quoted selector string from locator(...) / frame_locator(...) to bracket-check it.
_LOCATOR_ARG = re.compile(r"""(?:locator|frame_locator)\(\s*(['"])(.*?)\1""")


def lint_file(path: Path) -> List[Tuple[int, str, str]]:
    text = path.read_text(encoding="utf-8")
    if "playwright" not in text:
        return []  # not a migrated Playwright file — skip
    lines = text.splitlines()
    issues: List[Tuple[int, str, str]] = []

    # whole-file: exactly one sync_playwright() context (never nest)
    contexts = len(re.findall(r"sync_playwright\(\)", text))
    if contexts > 1:
        issues.append((0, "ERROR", f"{contexts} sync_playwright() contexts — must be exactly 1 "
                                   f"per run (helpers take `page`, never open their own)"))

    for lineno, line in enumerate(lines, start=1):
        if line.lstrip().startswith("#"):
            continue
        for pattern, level, message in LINE_CHECKS:
            if pattern.search(line):
                issues.append((lineno, level, message))
        for m in _LOCATOR_ARG.finditer(line):
            selector = m.group(2)
            if selector.count("[") != selector.count("]"):
                issues.append((lineno, "ERROR", f"Malformed selector (unbalanced brackets): {selector!r}"))
    return issues


_DIVIDER_ARGS = {'"-"*100', "'-'*100", '"_"*100', "'_'*100"}


def _convert_print(match: "re.Match[str]") -> str:
    indent, arg = match.group(1), match.group(2).strip()
    if arg.replace(" ", "") in _DIVIDER_ARGS:
        return f"{indent}Logger.divider()"
    if arg == "e":
        return f"{indent}Logger.warning(str(e))"
    return f"{indent}Logger.info({arg})"


def fix_file(path: Path) -> int:
    # Auto-fix the two mechanically safe transforms: bare `except:` and `print(...)`.
    # (Selector / evaluate-return / etc. are NOT auto-fixed — no safe universal rewrite.)
    text = path.read_text(encoding="utf-8")
    if "playwright" not in text:
        return 0
    original = text

    # Bare except -> narrow (PlaywrightError if imported, else Exception).
    exc_repl = "except PlaywrightError:" if "PlaywrightError" in text else "except Exception:"
    text, n_exc = re.subn(r"(?m)^([ \t]*)except[ \t]*:", lambda m: m.group(1) + exc_repl, text)

    # print(...) -> Logger.{divider,warning,info} (single-line prints only).
    text, n_print = re.subn(r"(?m)^([ \t]*)print\((.*)\)[ \t]*$", _convert_print, text)
    if n_print and "from util.Logger import Logger" not in text:
        text = re.sub(r"(from playwright\.sync_api import [^\n]*\n)",
                      r"\1from util.Logger import Logger\n", text, count=1)

    if text != original:
        path.write_text(text, encoding="utf-8")
    return n_exc + n_print


def main(argv: List[str]) -> int:
    strict = "--strict" in argv
    fix = "--fix" in argv
    args = [a for a in argv if a not in ("--strict", "--fix")]
    targets = [Path(a) for a in args] if args else sorted(Path("scrapers").glob("*.py"))

    files: List[Path] = []
    for t in targets:
        files.extend(sorted(t.glob("*.py")) if t.is_dir() else [t])

    if fix:
        for path in files:
            fixed = fix_file(path)
            if fixed:
                print(f"FIXED {path}: auto-fixed {fixed} issue(s) (bare excepts / prints)")

    errors = warnings = 0
    for path in files:
        for lineno, level, message in lint_file(path):
            loc = f"{path}:{lineno}" if lineno else str(path)
            print(f"{level:5} {loc}: {message}")
            if level == "ERROR":
                errors += 1
            else:
                warnings += 1

    print(f"\n{errors} error(s), {warnings} warning(s) across {len(files)} file(s).")
    return 1 if errors or (strict and warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
