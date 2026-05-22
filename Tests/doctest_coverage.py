"""Report doctest coverage: ratio of public callables with runnable doctest examples.

Uses interrogate (denominator: total public callables) and xdoctest (numerator:
callables containing >>> examples). Run from the project root:

    python Tests/doctest_coverage.py
"""

import subprocess
import sys
from dataclasses import dataclass


@dataclass
class CoverageResult:
    label: str
    total_public: int
    with_doctests: int

    @property
    def percentage(self) -> float:
        if self.total_public == 0:
            return 0.0
        return 100.0 * self.with_doctests / self.total_public


TARGETS = [
    ("PyICe/ (overall)", "PyICe/", "PyICe"),
    ("PyICe/lab_utils/", "PyICe/lab_utils/", "PyICe.lab_utils"),
    ("PyICe/lab_core.py", "PyICe/lab_core.py", "PyICe/lab_core.py"),
    ("PyICe/virtual_instruments.py", "PyICe/virtual_instruments.py", "PyICe/virtual_instruments.py"),
]


def check_tool(module_name: str) -> bool:
    result = subprocess.run(
        [sys.executable, "-m", module_name, "--help"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"ERROR: '{module_name}' is not installed.", file=sys.stderr)
        print(f"  Install with: pip install {module_name}", file=sys.stderr)
        print(f"  Or: pip install -e '.[dev]'", file=sys.stderr)
        return False
    return True


def get_total_callables(path: str) -> int:
    """Run interrogate and extract total public callable count from the TOTAL row."""
    result = subprocess.run(
        [
            sys.executable, "-m", "interrogate",
            "-v",
            "--ignore-private",
            "--ignore-magic",
            "--ignore-init-method",
            "--ignore-module",
            path,
        ],
        capture_output=True,
        text=True,
    )
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|")]
        # parts[0] is empty (before first |), parts[-1] is empty (after last |)
        cells = [p for p in parts if p]
        if not cells:
            continue
        if cells[0].upper() == "TOTAL":
            try:
                return int(cells[1])
            except (IndexError, ValueError):
                pass
    # Fallback: sum per-file totals
    total = 0
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line.startswith("|") or "---" in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        cells = [p for p in parts if p]
        if len(cells) < 2:
            continue
        if cells[0] in ("Name", "TOTAL") or cells[0].upper() == "NAME":
            continue
        try:
            total += int(cells[1])
        except ValueError:
            continue
    return total


def get_doctest_callables(xdoctest_target: str) -> tuple[int, list[str]]:
    """Run xdoctest list and count unique callables with doctests.

    Returns (count, list_of_skipped_module_warnings).
    """
    result = subprocess.run(
        [sys.executable, "-m", "xdoctest", xdoctest_target, "list"],
        capture_output=True,
        text=True,
    )
    callables = set()
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line.startswith("python -m xdoctest "):
            continue
        token = line.rsplit(None, 1)[-1]
        if ":" in token:
            name = token.rsplit(":", 1)[0]
        else:
            name = token
        callables.add(name)

    warnings = []
    for line in result.stderr.splitlines():
        if "ImportError" in line or "ModuleNotFoundError" in line:
            warnings.append(line.strip())

    return len(callables), warnings


def compute_coverage(label: str, interrogate_path: str, xdoctest_target: str) -> tuple[CoverageResult, list[str]]:
    total = get_total_callables(interrogate_path)
    with_doctests, warnings = get_doctest_callables(xdoctest_target)
    return CoverageResult(label=label, total_public=total, with_doctests=with_doctests), warnings


def format_report(results: list[CoverageResult], all_warnings: list[str]) -> str:
    lines = []
    lines.append("Doctest Coverage Report")
    lines.append("=" * 23)
    lines.append("")
    header = f"{'Target':<30} {'Total Public':>12}    {'With Doctests':>13}    {'Coverage':>8}"
    lines.append(header)
    lines.append("-" * len(header))
    for r in results:
        lines.append(
            f"{r.label:<30} {r.total_public:>12}    {r.with_doctests:>13}    {r.percentage:>7.1f}%"
        )
    lines.append("-" * len(header))
    lines.append("")
    lines.append('Note: "Total Public" = public callables (interrogate --ignore-private --ignore-magic)')
    lines.append('      "With Doctests" = callables containing runnable >>> examples (xdoctest)')

    if all_warnings:
        lines.append("")
        lines.append(f"Skipped modules ({len(all_warnings)} import errors):")
        for w in all_warnings[:10]:
            lines.append(f"  {w}")
        if len(all_warnings) > 10:
            lines.append(f"  ... and {len(all_warnings) - 10} more")

    return "\n".join(lines)


def main() -> int:
    missing = []
    for tool in ("interrogate", "xdoctest"):
        if not check_tool(tool):
            missing.append(tool)
    if missing:
        return 1

    results = []
    all_warnings = []
    for label, interrogate_path, xdoctest_target in TARGETS:
        coverage, warnings = compute_coverage(label, interrogate_path, xdoctest_target)
        results.append(coverage)
        all_warnings.extend(warnings)

    print(format_report(results, all_warnings))
    return 0


if __name__ == "__main__":
    sys.exit(main())
