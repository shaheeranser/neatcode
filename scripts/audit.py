#!/usr/bin/env python3
"""neatcode audit: rank files by structural cost so a cleanup can start where it matters.

Zero-dependency (Python 3.9+ standard library only). If `lizard` is already installed it is
used to sharpen function complexity/length; nothing is required for the core to run.
"""

from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Sequence, Set, Tuple

CONFIG_NAME = ".neatcode.json"

DEFAULT_EXCLUDES = [
    ".git", "node_modules", "dist", "build", "out", "target", "vendor",
    ".venv", "venv", "env", "__pycache__", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", ".next", ".nuxt", "coverage", "htmlcov", ".idea", ".vscode",
]

DEFAULT_THRESHOLDS = {
    "file_lines": 400,
    "function_lines": 50,
    "cyclomatic": 10,
    "nesting": 4,
    "import_cycles": 0,
}

JS_RESERVED = {
    "if", "for", "while", "switch", "catch", "return", "function", "else", "do",
    "try", "new", "typeof", "await", "yield", "with", "case", "throw", "delete",
    "void", "in", "instanceof",
}


@dataclass(frozen=True)
class Lang:
    name: str
    exts: Tuple[str, ...]
    line_comments: Tuple[str, ...]
    block_comments: Tuple[Tuple[str, str], ...]
    func: Tuple[re.Pattern, ...]
    imports: Tuple[re.Pattern, ...]
    decisions: Tuple[str, ...]
    decision_ops: Tuple[str, ...]
    brace: bool
    top: re.Pattern
    indent_unit: int = 4


LANGS: Tuple[Lang, ...] = (
    Lang(
        name="python",
        exts=(".py", ".pyi"),
        line_comments=("#",),
        block_comments=(),
        func=(
            re.compile(r"^(?P<indent>[ \t]*)(?:async[ \t]+)?def[ \t]+(?P<name>\w+)[ \t]*\(", re.M),
        ),
        imports=(
            re.compile(r"^[ \t]*from[ \t]+(?P<mod>[.\w]+)[ \t]+import[ \t]+", re.M),
            re.compile(r"^[ \t]*import[ \t]+(?P<mods>[.\w]+(?:[ \t]*,[ \t]*[.\w]+)*)", re.M),
        ),
        decisions=("if", "elif", "for", "while", "except", "and", "or", "case", "assert"),
        decision_ops=(),
        brace=False,
        top=re.compile(r"^(?:async[ \t]+)?def[ \t]+\w+|^class[ \t]+\w+", re.M),
    ),
    Lang(
        name="typescript",
        exts=(".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"),
        line_comments=("//",),
        block_comments=(("/*", "*/"),),
        func=(
            re.compile(r"(?<![\w$])(?:async[ \t]+)?function[ \t]*\*?[ \t]*(?P<name>[A-Za-z_$][\w$]*)"),
            re.compile(r"(?<![\w$])(?:const|let|var)[ \t]+(?P<name>[A-Za-z_$][\w$]*)[ \t]*(?::[^=\n]+)?=[ \t]*(?:async[ \t]*)?(?:function[ \t]*\(?|\([^)]*\)[ \t]*(?::[^={\n]+)?=>)"),
            re.compile(r"^[ \t]*(?:public[ \t]+|private[ \t]+|protected[ \t]+|static[ \t]+|async[ \t]+|get[ \t]+|set[ \t]+|\*[ \t]*)*(?P<name>[A-Za-z_$][\w$]*)[ \t]*\([^;{}]*\)[ \t]*(?::[^={\n]+)?\{", re.M),
        ),
        imports=(
            re.compile(r"""import[ \t]+(?:type[ \t]+)?(?:[^'"]*?[ \t]from[ \t]+)?['"](?P<mod>[^'"]+)['"]"""),
            re.compile(r"""require\([ \t]*['"](?P<mod>[^'"]+)['"][ \t]*\)"""),
            re.compile(r"""import\([ \t]*['"](?P<mod>[^'"]+)['"][ \t]*\)"""),
        ),
        decisions=("if", "for", "while", "case", "catch", "switch", "do"),
        decision_ops=("&&", "||", "??"),
        brace=True,
        top=re.compile(
            r"^(?:export[ \t]+(?:default[ \t]+)?)?(?:async[ \t]+)?function[ \t]+\w+"
            r"|^(?:export[ \t]+)?(?:abstract[ \t]+)?class[ \t]+\w+"
            r"|^(?:export[ \t]+)?(?:const|let|var)[ \t]+\w+[ \t]*=[ \t]*(?:async[ \t]*)?\(",
            re.M,
        ),
    ),
    Lang(
        name="go",
        exts=(".go",),
        line_comments=("//",),
        block_comments=(("/*", "*/"),),
        func=(re.compile(r"^func[ \t]+(?:\([^)]*\)[ \t]*)?(?P<name>\w+)[ \t]*\(", re.M),),
        imports=(),
        decisions=("if", "for", "case", "switch"),
        decision_ops=("&&", "||"),
        brace=True,
        top=re.compile(r"^func[ \t]", re.M),
    ),
    Lang(
        name="java",
        exts=(".java",),
        line_comments=("//",),
        block_comments=(("/*", "*/"),),
        func=(
            re.compile(
                r"^[ \t]*(?:public|private|protected|static|final|abstract|synchronized|native|default|strictfp|[ \t])*"
                r"[A-Za-z_<>\[\],.?]+[ \t]+(?P<name>\w+)[ \t]*\([^;]*\)[ \t]*(?:throws[^{]+)?\{",
                re.M,
            ),
        ),
        imports=(re.compile(r"^[ \t]*import[ \t]+(?:static[ \t]+)?(?P<mod>[\w.]+)[ \t]*;", re.M),),
        decisions=("if", "for", "while", "case", "catch", "switch"),
        decision_ops=("&&", "||"),
        brace=True,
        top=re.compile(r"^[ \t]*(?:public|private|protected|static|final|abstract|[ \t])*(?:class|interface|enum)[ \t]+\w+", re.M),
    ),
    Lang(
        name="rust",
        exts=(".rs",),
        line_comments=("//",),
        block_comments=(("/*", "*/"),),
        func=(
            re.compile(
                r"^[ \t]*(?:pub[ \t]+)?(?:async[ \t]+)?(?:unsafe[ \t]+)?(?:extern[ \t]+\"[^\"]*\"[ \t]+)?fn[ \t]+(?P<name>\w+)",
                re.M,
            ),
        ),
        imports=(),
        decisions=("if", "for", "while", "loop", "match"),
        decision_ops=("&&", "||"),
        brace=True,
        top=re.compile(r"^(?:pub[ \t]+)?(?:struct|enum|trait|impl)[ \t]|^(?:pub[ \t]+)?(?:async[ \t]+)?fn[ \t]", re.M),
    ),
)

EXT_TO_LANG: Dict[str, Lang] = {ext: lang for lang in LANGS for ext in lang.exts}


@dataclass
class Func:
    name: str
    line: int
    length: int
    complexity: int
    nesting: int


@dataclass
class FileMetrics:
    path: str
    language: str
    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    responsibilities: int = 0
    max_function_lines: int = 0
    max_cyclomatic: int = 0
    max_nesting: int = 0
    functions: List[Func] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    in_cycle: bool = False
    score: float = 0.0
    violations: List[str] = field(default_factory=list)


def strip_code(src: str, lang: Lang) -> str:
    """Blank out comments and string literals (preserving newlines) for structural analysis."""
    out: List[str] = []
    i, n = 0, len(src)
    quotes = ("'", '"', "`")
    while i < n:
        matched = False
        for tok in lang.line_comments:
            if src.startswith(tok, i):
                j = src.find("\n", i)
                j = n if j == -1 else j
                out.append(" " * (j - i))
                i = j
                matched = True
                break
        if matched:
            continue
        for start, end in lang.block_comments:
            if src.startswith(start, i):
                j = src.find(end, i + len(start))
                j = n if j == -1 else j + len(end)
                out.append("".join(ch if ch == "\n" else " " for ch in src[i:j]))
                i = j
                matched = True
                break
        if matched:
            continue
        c = src[i]
        if c in quotes:
            triple = c != "`" and src.startswith(c * 3, i)
            if triple:
                j = src.find(c * 3, i + 3)
                j = n if j == -1 else j + 3
            elif c == "`":
                j = i + 1
                while j < n and src[j] != "`":
                    j += 2 if src[j] == "\\" else 1
                j = min(j + 1, n)
            else:
                j = i + 1
                while j < n:
                    if src[j] == "\\":
                        j += 2
                        continue
                    if src[j] == c:
                        j += 1
                        break
                    if src[j] == "\n":
                        break
                    j += 1
            out.append("".join(ch if ch == "\n" else " " for ch in src[i:j]))
            i = j
            continue
        out.append(c)
        i += 1
    return "".join(out)


def expand_indent(prefix: str, unit: int = 4) -> int:
    return len(prefix.replace("\t", " " * unit))


def is_comment_line(line: str, lang: Lang) -> bool:
    s = line.strip()
    if not s:
        return False
    for tok in lang.line_comments:
        if s.startswith(tok):
            return True
    for start, end in lang.block_comments:
        if s.startswith(start) or s.startswith(end) or s.startswith("*"):
            return True
    return False


def count_decisions(body: str, lang: Lang) -> int:
    total = 0
    for kw in lang.decisions:
        total += len(re.findall(r"\b" + re.escape(kw) + r"\b", body))
    for op in lang.decision_ops:
        total += body.count(op)
    return total


def analyze_python(stripped: str, lang: Lang) -> List[Func]:
    lines = stripped.split("\n")
    funcs: List[Func] = []
    for m in lang.func[0].finditer(stripped):
        indent_col = expand_indent(m.group("indent"), lang.indent_unit)
        start = stripped.count("\n", 0, m.start())
        end = len(lines) - 1
        j = start + 1
        while j < len(lines):
            line = lines[j]
            if line.strip() == "":
                j += 1
                continue
            cur = expand_indent(line[: len(line) - len(line.lstrip(" \t"))], lang.indent_unit)
            if cur <= indent_col:
                end = j - 1
                break
            j += 1
        while end > start and lines[end].strip() == "":
            end -= 1
        body = "\n".join(lines[start : end + 1])
        deepest = 0
        for line in lines[start : end + 1]:
            if line.strip() == "":
                continue
            cur = expand_indent(line[: len(line) - len(line.lstrip(" \t"))], lang.indent_unit)
            deepest = max(deepest, cur - indent_col)
        funcs.append(
            Func(
                name=m.group("name"),
                line=start + 1,
                length=end - start + 1,
                complexity=1 + count_decisions(body, lang),
                nesting=max(0, deepest // lang.indent_unit),
            )
        )
    return funcs


def analyze_brace(stripped: str, lang: Lang) -> List[Func]:
    funcs: List[Func] = []
    for pat in lang.func:
        for m in pat.finditer(stripped):
            gd = m.groupdict()
            name = gd.get("name") or "<anonymous>"
            if name in JS_RESERVED:
                continue
            end = m.end()
            brace_start: Optional[int] = None
            if end - 1 >= m.start() and stripped[end - 1] == "{":
                brace_start = end - 1
            else:
                k = end
                limit = min(len(stripped), end + 400)
                while k < limit:
                    ch = stripped[k]
                    if ch == "{":
                        brace_start = k
                        break
                    if ch in ";\n":
                        break
                    k += 1
            start_line = stripped.count("\n", 0, m.start()) + 1
            if brace_start is None:
                funcs.append(Func(name, start_line, 1, 1 + count_decisions(stripped[m.start() : end + 120], lang), 0))
                continue
            depth = 0
            k = brace_start
            while k < len(stripped):
                ch = stripped[k]
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        break
                k += 1
            body = stripped[m.start() : k + 1]
            end_line = stripped.count("\n", 0, k) + 1
            nest = 0
            d = 0
            for ch in stripped[brace_start : k + 1]:
                if ch == "{":
                    d += 1
                    nest = max(nest, d)
                elif ch == "}":
                    d -= 1
            funcs.append(
                Func(
                    name=name,
                    line=start_line,
                    length=end_line - start_line + 1,
                    complexity=1 + count_decisions(body, lang),
                    nesting=nest,
                )
            )
    deduped: Dict[int, Func] = {}
    for f in funcs:
        prev = deduped.get(f.line)
        if prev is None or f.length > prev.length:
            deduped[f.line] = f
    return list(deduped.values())


def go_imports(code: str) -> List[str]:
    specs: List[str] = []
    for m in re.finditer(r"import[ \t]*\(", code):
        depth, k = 1, m.end()
        while k < len(code) and depth > 0:
            if code[k] == "(":
                depth += 1
            elif code[k] == ")":
                depth -= 1
            k += 1
        specs += re.findall(r'"([^"]+)"', code[m.end() : k - 1])
    specs += re.findall(r'^[ \t]*import[ \t]+"([^"]+)"', code, re.M)
    return specs


def extract_imports(code: str, lang: Lang) -> List[str]:
    specs: List[str] = []
    for pat in lang.imports:
        for m in pat.finditer(code):
            gd = m.groupdict()
            if gd.get("mod"):
                specs.append(gd["mod"])
            if gd.get("mods"):
                for part in gd["mods"].split(","):
                    part = part.strip().split()
                    if part:
                        specs.append(part[0])
    if lang.name == "go":
        specs += go_imports(code)
    return specs


def analyze_file(path: str, rel: str, lang: Lang) -> Optional[FileMetrics]:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except OSError:
        return None
    lines = src.splitlines()
    total = len(lines)
    blank = sum(1 for line in lines if not line.strip())
    comment = sum(1 for line in lines if is_comment_line(line, lang))
    stripped = strip_code(src, lang)
    funcs = analyze_python(stripped, lang) if not lang.brace else analyze_brace(stripped, lang)
    metrics = FileMetrics(
        path=rel,
        language=lang.name,
        total_lines=total,
        blank_lines=blank,
        comment_lines=comment,
        code_lines=max(0, total - blank - comment),
        responsibilities=len(lang.top.findall(stripped)),
        functions=funcs,
        imports=extract_imports(src, lang),
    )
    metrics.max_function_lines = max((f.length for f in funcs), default=0)
    metrics.max_cyclomatic = max((f.complexity for f in funcs), default=0)
    metrics.max_nesting = max((f.nesting for f in funcs), default=0)
    return metrics


def lizard_metrics(path: str) -> Optional[Tuple[int, int]]:
    try:
        import lizard  # type: ignore
    except Exception:
        return None
    try:
        info = lizard.analyze_file(path)
    except Exception:
        return None
    if not info.function_list:
        return None
    length = max(fn.length for fn in info.function_list)
    cyclo = max(fn.cyclomatic_complexity for fn in info.function_list)
    return length, cyclo


def resolve_imports(metrics: List[FileMetrics]) -> List[List[str]]:
    index: Dict[str, str] = {m.path: m.path for m in metrics}

    def first_existing(candidates: Sequence[str]) -> Optional[str]:
        for cand in candidates:
            cand = os.path.normpath(cand).replace(os.sep, "/")
            if cand in index:
                return cand
            hits = [p for p in index if p.endswith("/" + cand)]
            if len(hits) == 1:
                return hits[0]
        return None

    adj: Dict[str, Set[str]] = {m.path: set() for m in metrics}

    for m in metrics:
        lang = next((ln for ln in LANGS if ln.name == m.language), None)
        if lang is None:
            continue
        src_dir = os.path.dirname(m.path)
        for spec in m.imports:
            target: Optional[str] = None
            if lang.name == "python":
                if spec.startswith("."):
                    level = len(spec) - len(spec.lstrip("."))
                    rest = spec[level:]
                    base = src_dir
                    for _ in range(max(0, level - 1)):
                        base = os.path.dirname(base)
                    parts = rest.split(".") if rest else []
                    target = os.path.join(base, *parts) if parts else base
                else:
                    target = os.path.join(*spec.split("."))
                cands = [target + ".py", target + ".pyi", os.path.join(target, "__init__.py")]
            else:
                if not spec.startswith("."):
                    continue
                target = os.path.join(src_dir, spec)
                cands = [target]
                for ext in lang.exts:
                    cands.append(target + ext)
                    cands.append(os.path.join(target, "index" + ext))
            hit = first_existing(cands)
            if hit and hit != m.path:
                adj[m.path].add(hit)

    cycles = find_cycles(list(adj.keys()), adj)
    in_cycle: Set[str] = set()
    for comp in cycles:
        in_cycle.update(comp)
    for m in metrics:
        m.in_cycle = m.path in in_cycle
    return cycles


def find_cycles(nodes: Sequence[str], adj: Dict[str, Set[str]]) -> List[List[str]]:
    index: Dict[str, int] = {}
    low: Dict[str, int] = {}
    onstack: Dict[str, bool] = {}
    stack: List[str] = []
    result: List[List[str]] = []
    counter = [0]

    for root in nodes:
        if root in index:
            continue
        work: List[Tuple[str, int]] = [(root, 0)]
        while work:
            v, pi = work[-1]
            if pi == 0:
                index[v] = counter[0]
                low[v] = counter[0]
                counter[0] += 1
                stack.append(v)
                onstack[v] = True
            recurse = False
            neighbors = list(adj.get(v, ()))
            i = pi
            while i < len(neighbors):
                w = neighbors[i]
                if w not in index:
                    work[-1] = (v, i + 1)
                    work.append((w, 0))
                    recurse = True
                    break
                if onstack.get(w):
                    low[v] = min(low[v], index[w])
                i += 1
            if recurse:
                continue
            if low[v] == index[v]:
                comp: List[str] = []
                while True:
                    w = stack.pop()
                    onstack[w] = False
                    comp.append(w)
                    if w == v:
                        break
                if len(comp) > 1 or v in adj.get(v, ()):
                    result.append(sorted(comp))
            work.pop()
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[v])
    return result


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def percentile(values: List[int], p: float) -> Optional[int]:
    vals = sorted(v for v in values if v > 0)
    if not vals:
        return None
    k = min(int(len(vals) * p), len(vals) - 1)
    return vals[k]


def discover_thresholds(metrics: List[FileMetrics]) -> Dict[str, int]:
    fl = percentile([m.code_lines for m in metrics], 0.75)
    fn = percentile([m.max_function_lines for m in metrics], 0.75)
    cx = percentile([m.max_cyclomatic for m in metrics], 0.75)
    ns = percentile([m.max_nesting for m in metrics], 0.75)
    return {
        "file_lines": clamp(fl or 400, 200, 500),
        "function_lines": clamp(fn or 50, 30, 60),
        "cyclomatic": clamp(cx or 10, 8, 15),
        "nesting": clamp(ns or 4, 3, 5),
        "import_cycles": 0,
    }


def load_config(path: str) -> Optional[dict]:
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def score_file(m: FileMetrics, t: Dict[str, int]) -> Tuple[float, List[str]]:
    violations: List[str] = []
    if m.code_lines > t["file_lines"]:
        violations.append("file_lines")
    if m.max_function_lines > t["function_lines"]:
        violations.append("function_lines")
    if m.max_cyclomatic > t["cyclomatic"]:
        violations.append("cyclomatic")
    if m.max_nesting > t["nesting"]:
        violations.append("nesting")
    if m.in_cycle and t.get("import_cycles", 0) == 0:
        violations.append("import_cycle")
    s = max(1.0, m.code_lines / max(1, t["file_lines"]))
    s *= 1 + max(0.0, m.max_function_lines / max(1, t["function_lines"]) - 1)
    s *= 1 + max(0.0, m.max_cyclomatic / max(1, t["cyclomatic"]) - 1)
    s *= 1 + max(0.0, m.max_nesting / max(1, t["nesting"]) - 1)
    if m.responsibilities > 8:
        s *= 1 + 0.15 * (m.responsibilities - 8)
    if m.in_cycle:
        s *= 1.5
    return round(s, 3), violations


def is_excluded(rel: str, name: str, patterns: Sequence[str]) -> bool:
    parts = rel.split("/")
    if any(part in DEFAULT_EXCLUDES for part in parts):
        return True
    for pat in patterns:
        if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(rel, "*/" + pat):
            return True
    return False


def collect_files(roots: Sequence[str], patterns: Sequence[str]) -> List[Tuple[str, str, Lang]]:
    found: List[Tuple[str, str, Lang]] = []
    for root in roots:
        if os.path.isfile(root):
            ext = os.path.splitext(root)[1]
            lang = EXT_TO_LANG.get(ext)
            if lang:
                found.append((root, os.path.basename(root), lang))
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in DEFAULT_EXCLUDES and not d.startswith(".")]
            for fname in filenames:
                ext = os.path.splitext(fname)[1]
                lang = EXT_TO_LANG.get(ext)
                if not lang:
                    continue
                full = os.path.join(dirpath, fname)
                rel = os.path.relpath(full, root).replace(os.sep, "/")
                if is_excluded(rel, fname, patterns):
                    continue
                found.append((full, rel, lang))
    found.sort(key=lambda item: item[1])
    return found


def render_text(report: dict, top: int) -> str:
    t = report["thresholds"]
    lines = [
        "neatcode audit",
        f"  files scanned : {report['summary']['files']}",
        f"  flagged       : {report['summary']['flagged']}",
        f"  thresholds    : file_lines={t['file_lines']} function_lines={t['function_lines']} "
        f"cyclomatic={t['cyclomatic']} nesting={t['nesting']}",
        f"  analysis      : {', '.join(report['tools'])}",
        "",
    ]
    rows = report["files"][:top]
    if not rows:
        lines.append("  no files over threshold — structure looks healthy")
    else:
        header = f"  {'#':>3}  {'score':>6}  {'lines':>6}  {'maxfn':>6}  {'cc':>4}  {'nest':>4}  {'resp':>4}  {'cyc':>3}  file"
        lines.append(header)
        for i, f in enumerate(rows, 1):
            lines.append(
                f"  {i:>3}  {f['score']:>6.2f}  {f['code_lines']:>6}  {f['max_function_lines']:>6}  "
                f"{f['max_cyclomatic']:>4}  {f['max_nesting']:>4}  {f['responsibilities']:>4}  "
                f"{'yes' if f['in_cycle'] else 'no':>3}  {f['path']}"
            )
    if report["cycles"]:
        lines.append("")
        lines.append("  import cycles:")
        for comp in report["cycles"][:10]:
            lines.append("    " + " -> ".join(comp))
    lines.append("")
    lines.append("  note: a high rank is a candidate, not a verdict. Check cohesion before splitting.")
    return "\n".join(lines)


def detect_tools(use_lizard: bool) -> List[str]:
    tools = ["core (stdlib)"]
    if use_lizard:
        tools.append("lizard")
    elif importlib.util.find_spec("lizard") is not None:
        tools.append("lizard (available, unused)")
    if shutil.which("cloc"):
        tools.append("cloc (available, unused)")
    if importlib.util.find_spec("tree_sitter") is not None:
        tools.append("tree-sitter (available, unused)")
    return tools


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="audit.py", description="Rank files by structural cost.")
    parser.add_argument("paths", nargs="*", default=["."], help="files or directories to scan (default: .)")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--top", type=int, default=25, help="max files to list (default: 25)")
    parser.add_argument("--exclude", action="append", default=[], help="glob to exclude (repeatable)")
    parser.add_argument("--config", default=None, help=f"path to {CONFIG_NAME}")
    parser.add_argument("--init", action="store_true", help="re-discover thresholds and rewrite config")
    parser.add_argument("--no-write-config", action="store_true", help="never write a config file")
    args = parser.parse_args(argv)

    roots = args.paths or ["."]
    root_for_config = roots[0] if len(roots) == 1 and os.path.isdir(roots[0]) else "."
    config_path = args.config or os.path.join(root_for_config, CONFIG_NAME)
    config = load_config(config_path)

    exclude = list(args.exclude)
    if config:
        for pat in config.get("exclude", []):
            if pat not in exclude:
                exclude.append(pat)

    files = collect_files(roots, exclude)
    lizard_available = importlib.util.find_spec("lizard") is not None
    metrics: List[FileMetrics] = []
    used_lizard = False
    for full, rel, lang in files:
        m = analyze_file(full, rel, lang)
        if m is None:
            continue
        if lizard_available:
            extra = lizard_metrics(full)
            if extra:
                m.max_function_lines = max(m.max_function_lines, extra[0])
                m.max_cyclomatic = max(m.max_cyclomatic, extra[1])
                used_lizard = True
        metrics.append(m)

    cycles = resolve_imports(metrics)

    write_config = False
    if config is None or args.init:
        config = {
            "version": 1,
            "exclude": exclude or ["node_modules", "dist", "build", ".venv", "**/migrations/**"],
            "languages": sorted({m.language for m in metrics}),
            "thresholds": discover_thresholds(metrics),
            "baseline_file": ".neatcode-baseline.json",
        }
        write_config = not args.no_write_config
    thresholds = {**DEFAULT_THRESHOLDS, **config.get("thresholds", {})}

    flagged = 0
    for m in metrics:
        m.score, m.violations = score_file(m, thresholds)
        if m.violations:
            flagged += 1
    metrics.sort(key=lambda m: (-m.score, m.path))

    if write_config:
        try:
            with open(config_path, "w", encoding="utf-8") as fh:
                json.dump(config, fh, indent=2)
                fh.write("\n")
        except OSError:
            pass

    report = {
        "config": config_path,
        "thresholds": thresholds,
        "tools": detect_tools(used_lizard),
        "summary": {"files": len(metrics), "flagged": flagged, "cycles": len(cycles)},
        "cycles": cycles,
        "files": [
            {
                "path": m.path,
                "language": m.language,
                "code_lines": m.code_lines,
                "total_lines": m.total_lines,
                "comment_lines": m.comment_lines,
                "responsibilities": m.responsibilities,
                "max_function_lines": m.max_function_lines,
                "max_cyclomatic": m.max_cyclomatic,
                "max_nesting": m.max_nesting,
                "in_cycle": m.in_cycle,
                "score": m.score,
                "violations": m.violations,
            }
            for m in metrics[: max(args.top, 0) or len(metrics)]
        ],
    }

    if args.json:
        json.dump(report, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print(render_text(report, args.top))
        if write_config:
            print(f"  wrote config  : {config_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
