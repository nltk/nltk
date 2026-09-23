#!/usr/bin/env python3
# Natural Language Toolkit: line-by-line sink sweep
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""List every line in the package that opens, reads, writes, prints, executes
or builds a filesystem path, with the guard context around it.

This is deliberately a per-line regex sweep, not an AST walk: a sink can hide
in a string, an f-string, a lambda or a docstring example that an AST call
scan never reports. Each matched line is classified (open / read / write /
print / exec / path / pointer), tagged CODE, DOC or COMMENT, and marked with
whether a pathsec / termsec / trusted-exec guard appears on the line, within
five lines either side, or nowhere. Files with rows in
``nltk/test/unit/PATHSEC_FILE_IO_AUDIT.md`` are cross-referenced so the
ledger shows which sinks a human verdict already covers.

The output is ``SINK_LEDGER.md`` at the repository root (a summary table and
every matched line) and, optionally, a JSON dump. It does not fail the build;
its job is to make the residue reviewable and to keep the review repeatable.
"""

import argparse
import collections
import io
import json
import re
import sys
import tokenize
from pathlib import Path

CATEGORIES = [
    (
        "open",
        re.compile(
            r"\b(open|io\.open|codecs\.open|os\.open|os\.fdopen|gzip\.open|bz2\.open"
            r"|lzma\.open|tarfile\.open|zipfile\.ZipFile|GzipFile|BZ2File|ZipFile"
            r"|OpenOnDemandZipFile|shelve\.open|sqlite3\.connect|dbm\.open)\s*\("
        ),
    ),
    (
        "pointer",
        re.compile(
            r"\b(self|reader|ixreader|path|fileid|root|_root|self\._root)\.open\s*\("
            r"|\.abspath\([^)]*\)\.open\s*\(|\.join\([^)]*\)\.open\s*\("
        ),
    ),
    (
        "read",
        re.compile(
            r"\.(read|readline|readlines|read_text|read_bytes|readinto)\s*\("
            r"|\b(json\.load|json\.loads|pickle\.load|pickle\.loads|np\.load|numpy\.load"
            r"|np\.loadtxt|loadtxt|load_from_json|urlopen|urlretrieve"
            r"|requests\.(get|post)|etree\.parse|ElementTree\.parse|minidom\.parse"
            r"|yaml\.load|yaml\.safe_load|csv\.reader|csv\.DictReader|shutil\.copy"
            r"|shutil\.copyfile|shutil\.copytree|shutil\.move)\b"
        ),
    ),
    (
        "write",
        re.compile(
            r"\.(write|writelines|write_text|write_bytes|writerow|writerows"
            r"|writeheader|savefig|save|dump|to_csv|tofile)\s*\("
            r"|\b(json\.dump|pickle\.dump|np\.save|numpy\.save|np\.savetxt|savetxt"
            r"|os\.(makedirs|mkdir|remove|unlink|rename|replace|rmdir|removedirs"
            r"|chmod|chown|symlink|link|utime|truncate)"
            r"|shutil\.(rmtree|move|copy|copy2|copyfile|copytree|unpack_archive"
            r"|make_archive)|tempfile\.\w+|extractall|extract)\s*\("
        ),
    ),
    (
        "print",
        re.compile(
            r"\b(print|safe_print|pprint|input)\s*\(|sys\.std(out|err)|\.flush\s*\("
            r"|\b(logging|logger|log)\.(debug|info|warning|warn|error|critical"
            r"|exception)\s*\(|warnings\.warn\s*\("
        ),
    ),
    (
        "exec",
        re.compile(
            r"\b(subprocess\.\w+|Popen|os\.system|os\.popen|os\.exec\w*|os\.spawn\w*"
            r"|eval|exec|compile|__import__|importlib\.import_module"
            r"|pickle\.Unpickler|Unpickler)\s*\("
        ),
    ),
    (
        "path",
        re.compile(
            r"\b(os\.path\.(join|expanduser|expandvars|abspath|realpath|normpath)"
            r"|os\.(listdir|walk|scandir|stat|lstat|chdir|environ)|pathlib\.Path"
            r"|glob\.glob|glob\.iglob|FileSystemPathPointer|ZipFilePathPointer"
            r"|__file__|nltk\.data\.path)\b"
        ),
    ),
]

GUARDS = re.compile(
    r"pathsec|validate_path|validate_tool_dir|validate_model_resource"
    r"|make_staging_dir|staging_tempdir|_secure_open|pathsec_open|open_datafile"
    r"|resolve_trusted_executable|allowlisted_pickle_load|restricted_pickle_load"
    r"|safe_json_load|safe_parse|safe_fromstring|redos\.|termsec|safe_print"
    r"|sanitize_terminal|sanitize_csv_field|register_data_root|is_private_dir"
    r"|O_NOFOLLOW|dir_fd|dir=|# sandboxed-open ok|# pathsec ok|# noqa"
)

CONTEXT = 5


def _string_and_comment_lines(source):
    marks = {}
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == tokenize.STRING and tok.start[0] != tok.end[0]:
                for number in range(tok.start[0], tok.end[0] + 1):
                    marks[number] = "DOC"
            elif tok.type == tokenize.COMMENT:
                marks.setdefault(tok.start[0], "COMMENT")
    except (tokenize.TokenError, SyntaxError):
        pass
    return marks


def _audited_files(audit_path):
    """File paths the audit document has a verdict row for.

    Rows name a file directly (``chunk/named_entity.py``), a directory glob
    (``app/*.py``), a glob with a name list (``corpus/reader/*.py (api, util)``)
    or a brace list (``classify/{megam,tadm}.py``); every spelling expands to
    the package-relative paths it covers, and a bare glob is kept as a prefix.
    """
    if not audit_path.exists():
        return set(), ()
    files, prefixes = set(), []
    for row in re.findall(
        r"^\|\s*([^|]+?)\s*\|", audit_path.read_text(encoding="utf-8"), re.M
    ):
        for group in re.finditer(r"([\w/]+)/\*\.py\s*\(([^)]*)\)", row):
            for name in re.split(r"[\s,]+", group.group(2).strip()):
                if name:
                    files.add(f"{group.group(1)}/{name}.py")
        for group in re.finditer(r"([\w/]*)\{([^}]*)\}\.py", row):
            for name in group.group(2).split(","):
                files.add(f"{group.group(1)}{name.strip()}.py")
        for glob in re.finditer(r"([\w/]+)/\*\.py", row):
            prefixes.append(glob.group(1) + "/")
        files.update(re.findall(r"\b([\w/]+\.py)\b", row))
    return files, tuple(prefixes)


def sweep(package_dir, audit_path):
    package_dir = Path(package_dir)
    audited, prefixes = _audited_files(audit_path)
    rows = []
    for path in sorted(package_dir.rglob("*.py")):
        rel = path.relative_to(package_dir).as_posix()
        if rel.startswith("test/"):
            continue
        source = path.read_text(encoding="utf-8", errors="replace")
        lines = source.splitlines()
        marks = _string_and_comment_lines(source)
        in_audit = rel in audited or rel.startswith(prefixes)
        for number, line in enumerate(lines, 1):
            cats = [name for name, rx in CATEGORIES if rx.search(line)]
            if not cats:
                continue
            if "pointer" in cats and "open" in cats:
                cats.remove("open")
            stripped = line.strip()
            where = marks.get(number, "CODE")
            if where == "CODE" and stripped.startswith("#"):
                where = "COMMENT"
            around = "\n".join(lines[max(0, number - 1 - CONTEXT) : number + CONTEXT])
            if GUARDS.search(line):
                guard = "line"
            elif GUARDS.search(around):
                guard = "near"
            else:
                guard = "none"
            rows.append(
                {
                    "file": rel,
                    "line": number,
                    "cats": cats,
                    "where": where,
                    "guard": guard,
                    "audited": in_audit,
                    "text": stripped[:160],
                }
            )
    return rows


def render(rows):
    code = [r for r in rows if r["where"] == "CODE"]
    by_cat = collections.Counter(c for r in code for c in r["cats"])
    by_guard = collections.Counter((c, r["guard"]) for r in code for c in r["cats"])
    out = [
        "# Sink ledger: every open / read / write / print / exec / path line in nltk/",
        "",
        "Generated by `tools/security_sink_sweep.py` (tests excluded). Re-run after any",
        "change to a sink; review the `none` guard column against",
        "`nltk/test/unit/PATHSEC_FILE_IO_AUDIT.md` and the security probes.",
        "",
        f"{len(rows)} matched lines, {len(code)} in code, "
        f"{len(rows) - len(code)} in docstrings or comments.",
        "",
        "| category | code lines | guard on line | guard within 5 lines | no guard |",
        "|---|---|---|---|---|",
    ]
    for cat, total in sorted(by_cat.items()):
        out.append(
            f"| {cat} | {total} | {by_guard[(cat, 'line')]} | "
            f"{by_guard[(cat, 'near')]} | {by_guard[(cat, 'none')]} |"
        )
    out += [
        "",
        "## Every matched line",
        "",
        "| file:line | where | categories | guard | audited | text |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        text = r["text"].replace("|", "\\|")[:110]
        out.append(
            f"| {r['file']}:{r['line']} | {r['where']} | {','.join(r['cats'])} | "
            f"{r['guard']} | {'yes' if r['audited'] else 'no'} | `{text}` |"
        )
    return "\n".join(out) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    root = Path(__file__).resolve().parent.parent
    parser.add_argument("package_dir", nargs="?", default=str(root / "nltk"))
    parser.add_argument("--ledger", default=str(root / "SINK_LEDGER.md"))
    parser.add_argument("--json", default=None, help="also dump the rows as JSON")
    parser.add_argument(
        "--audit",
        default=str(root / "nltk" / "test" / "unit" / "PATHSEC_FILE_IO_AUDIT.md"),
    )
    args = parser.parse_args(argv)
    rows = sweep(args.package_dir, Path(args.audit))
    Path(args.ledger).write_text(render(rows), encoding="utf-8")
    if args.json:
        Path(args.json).write_text(json.dumps(rows), encoding="utf-8")
    code = [r for r in rows if r["where"] == "CODE"]
    residue = [
        r
        for r in code
        if r["guard"] == "none"
        and not r["audited"]
        and set(r["cats"]) & {"open", "write", "read", "exec"}
    ]
    print(f"{len(rows)} lines matched, {len(code)} in code; ledger: {args.ledger}")
    print(
        f"{len(residue)} unguarded open/read/write/exec code lines in unaudited files"
    )
    for f, n in collections.Counter(r["file"] for r in residue).most_common(60):
        print(f"  {n:3d} {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
