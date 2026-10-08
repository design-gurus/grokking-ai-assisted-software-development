"""Lab 2, map the review assistant: a map with cited claims and a trace with marked hops."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, bullets, check, finish, sections, skip  # noqa: E402

LAB = "labs/check-02"
MAP = "labs/02/map.md"
TRACE = "labs/02/trace.md"
CITATION = re.compile(r"`([^`#\s]+)#([A-Za-z_][\w.]*)`\s*$")
ENTRY_POINTS = {"webhook": r"webhook", "command line": r"command line|cli", "worker": r"worker"}
BOUNDARIES = {"core": r"\bcore\b", "provider": r"provider", "storage": r"storage|ledger"}


def symbol_defined(path: Path, symbol: str) -> bool:
    """True when the file defines the symbol as a function, class, method or module-level name."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return symbol in path.read_text(encoding="utf-8", errors="replace")
    wanted = symbol.split(".")[-1]
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) and node.name == wanted:
            return True
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == wanted:
                    return True
    return False


def main() -> None:
    if not (ROOT / MAP).exists() and not (ROOT / TRACE).exists():
        skip(LAB, f"neither {MAP} nor {TRACE} exists")
    check((ROOT / MAP).exists(), f"{MAP} exists")
    check((ROOT / TRACE).exists(), f"{TRACE} exists")

    map_text = (ROOT / MAP).read_text(encoding="utf-8") if (ROOT / MAP).exists() else ""
    parts = sections(map_text)
    claims: list[tuple[str, str]] = []
    for heading in ("Arrows", "Dotted line"):
        for claim in bullets(parts.get(heading, "")):
            claims.append((heading, claim))
    cited = 0
    for heading, claim in claims:
        match = CITATION.search(claim)
        if not match:
            check(False, f"{heading}: claim lacks a trailing `path#symbol` citation: {claim[:70]}")
            continue
        path, symbol = match.group(1), match.group(2)
        file = ROOT / path
        if not file.exists():
            check(False, f"{heading}: cited path does not exist: {path}")
            continue
        if not symbol_defined(file, symbol):
            check(False, f"{heading}: {symbol} is not defined in {path}")
            continue
        cited += 1
    check(cited >= 8 and cited == len(claims), f"every claim ends with a valid `path#symbol` citation, at least eight ({cited}/{len(claims)})")

    boundaries = parts.get("Boundaries", "")
    for name, pattern in {**ENTRY_POINTS, **BOUNDARIES}.items():
        check(re.search(pattern, boundaries, re.IGNORECASE) is not None, f"## Boundaries names {name}")
    dotted = bullets(parts.get("Dotted line", ""))
    check(len(dotted) == 1 and CITATION.search(dotted[0]) is not None, "## Dotted line has exactly one claim, with a citation")

    trace_text = (ROOT / TRACE).read_text(encoding="utf-8") if (ROOT / TRACE).exists() else ""
    hops = [ln for ln in trace_text.splitlines() if re.match(r"^- (STATIC|DYNAMIC|BOTH):", ln)]
    disagreements = [ln for ln in trace_text.splitlines() if ln.startswith("- DISAGREEMENT:")]
    check(len(hops) >= 5, f"{TRACE} has at least five hop lines marked STATIC, DYNAMIC or BOTH ({len(hops)})")
    check(len(disagreements) >= 1, f"{TRACE} has at least one DISAGREEMENT line ({len(disagreements)})")
    finish(LAB)


if __name__ == "__main__":
    main()
