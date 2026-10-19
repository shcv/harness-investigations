"""Filter astdiff output down to changes worth a changelog agent's attention.

Pure functions over astdiff text: drop entries whose only change is
version/build metadata, and pair default-import removals with destructured
re-imports of the same module so they read as one style change.
"""

import re

# Patterns for detecting version bump noise in astdiff output
_VERSION_BUMP_RE = re.compile(r'VERSION:\s*"[^"]*"')
_BUILD_TIME_RE = re.compile(r'BUILD_TIME:\s*"[^"]*"')
_BUILD_PATH_RE = re.compile(r'claude-cli-external-build-\d+')
_ASTDIFF_SECTION_RE = re.compile(
    r"(?m)^=== (?:Removed(?: Functions)?|Added(?: Functions)?|"
    r"Modified Functions|Structural Changes|String(?:-only)? Changes) ===$"
)
_ASTDIFF_ENTRY_RE = re.compile(r"(?m)^@@@ .+")


def looks_like_astdiff(content: str) -> bool:
    """Return True when diff content matches known astdiff output shapes."""
    header_lines = content.splitlines()[:8]
    has_astdiff_summary = any(
        line.startswith(
            (
                "Structural similarity:",
                "Matched:",
                "Matched declarations:",
                "Diff size:",
                "Changes:",
            )
        )
        for line in header_lines
    )
    has_astdiff_body = (
        _ASTDIFF_SECTION_RE.search(content) is not None
        or _ASTDIFF_ENTRY_RE.search(content) is not None
    )
    return has_astdiff_summary and has_astdiff_body


def filter_astdiff(content: str) -> str:
    """Parse astdiff output and remove known version-only changes."""
    sections = _parse_astdiff_sections(content)

    # Filter structural changes
    kept_structural = []
    version_bump_count = 0

    for entry in sections["structural"]:
        # Similarity scores describe declaration matching, not semantic
        # equivalence. Even 100.0% matches can change property accesses or
        # constants; astdiff has already classified this entry as changed.
        if _is_version_bump_entry(entry):
            version_bump_count += 1
            continue

        kept_structural.append(entry)

    # Filter string-only changes (version bumps can appear here too)
    kept_string = []
    string_version_bumps = 0

    for entry in sections["string"]:
        if _is_version_bump_entry(entry):
            string_version_bumps += 1
            continue
        kept_string.append(entry)

    version_bump_count += string_version_bumps

    # Pair removed/added imports by module
    paired_imports, unpaired_removed, unpaired_added = _pair_imports(
        sections["removed"], sections["added"]
    )

    # Build filtered output
    parts = [sections["header"]]

    if version_bump_count > 0:
        parts.append("")
        parts.append(f"Filtered: {version_bump_count} version bumps")

    # Import style changes (paired old→new for same module)
    if paired_imports:
        parts.append("")
        parts.append("=== Import Style Changes ===")
        parts.append("")
        for mod in sorted(paired_imports):
            pair = paired_imports[mod]
            old_stmts = []
            for e in pair["removed"]:
                for ln in e.split("\n"):
                    if ln.startswith("- "):
                        old_stmts.append(ln[2:])
            new_stmts = []
            for e in pair["added"]:
                for ln in e.split("\n"):
                    if ln.startswith("+ "):
                        new_stmts.append(ln[2:])
            parts.append(f'"{mod}":')
            for s in old_stmts:
                parts.append(f"  - {s}")
            for s in new_stmts:
                parts.append(f"  + {s}")
            parts.append("")

    # Unpaired removals (non-import declarations that were removed)
    if unpaired_removed:
        parts.append("=== Removed ===")
        parts.append("")
        for entry in unpaired_removed:
            parts.append(entry)
            parts.append("")

    # Unpaired additions (non-import declarations that were added)
    if unpaired_added:
        parts.append("=== Added ===")
        parts.append("")
        for entry in unpaired_added:
            parts.append(entry)
            parts.append("")

    # Structural changes (filtered)
    if kept_structural:
        parts.append("=== Structural Changes ===")
        parts.append("")
        for entry in kept_structural:
            parts.append(entry)
            parts.append("")

    # String-only changes (filtered)
    if kept_string:
        parts.append("=== String Changes ===")
        parts.append("")
        for entry in kept_string:
            parts.append(entry)
            parts.append("")

    return "\n".join(parts)


def _parse_astdiff_sections(content: str) -> dict:
    """Parse astdiff output into header + per-section entry lists."""
    section_markers = {
        "=== Removed ===": "removed",
        "=== Removed Functions ===": "removed",
        "=== Added ===": "added",
        "=== Added Functions ===": "added",
        "=== Modified Functions ===": "structural",
        "=== Structural Changes ===": "structural",
        "=== String Changes ===": "string",
        "=== String-only Changes ===": "string",
    }

    # Split on section markers, keeping them as delimiters
    pattern = r"\n(" + "|".join(
        re.escape(m) for m in section_markers
    ) + r")\n"
    parts = re.split(pattern, content)

    result = {
        "header": parts[0].rstrip(),
        "removed": [],
        "added": [],
        "structural": [],
        "string": [],
    }

    # parts = [header, marker1, content1, marker2, content2, ...]
    for i in range(1, len(parts), 2):
        marker = parts[i]
        section_content = parts[i + 1] if i + 1 < len(parts) else ""
        key = section_markers.get(marker)
        if key:
            result[key] = _split_astdiff_entries(section_content, key)

    return result


def _split_astdiff_entries(text: str, section_type: str) -> list:
    """Split a section's text into individual entry strings."""
    if section_type == "removed":
        marker = "--- Removed"
    elif section_type == "added":
        marker = "+++ Added"
    else:
        marker = "@@@"

    entries = []
    current = []

    for line in text.split("\n"):
        if line.startswith(marker) and current:
            entry = "\n".join(current).strip()
            if entry:
                entries.append(entry)
            current = []
        current.append(line)

    if current:
        entry = "\n".join(current).strip()
        if entry:
            entries.append(entry)

    return entries


def _is_version_bump_entry(entry_text: str) -> bool:
    """Check if a structural/string entry's diff is only VERSION/BUILD_TIME changes."""
    changed_minus = []
    changed_plus = []
    in_hunk = False

    for line in entry_text.split("\n"):
        if line.startswith("@@ "):
            in_hunk = True
            continue
        # Skip file path lines (--- file, +++ file)
        if line.startswith("--- ") or line.startswith("+++ "):
            continue
        if in_hunk:
            if line.startswith("-"):
                changed_minus.append(line[1:])
            elif line.startswith("+"):
                changed_plus.append(line[1:])

    if not changed_minus or not changed_plus:
        return False

    def normalize_version_strings(text):
        text = _VERSION_BUMP_RE.sub('VERSION: ""', text)
        text = _BUILD_TIME_RE.sub('BUILD_TIME: ""', text)
        text = _BUILD_PATH_RE.sub("claude-cli-external-build-0", text)
        return text

    norm_minus = normalize_version_strings(" ".join(changed_minus))
    norm_plus = normalize_version_strings(" ".join(changed_plus))

    return norm_minus == norm_plus


def _pair_imports(removed_entries, added_entries):
    """Pair removed default imports with added destructured imports for same module.

    Returns (paired_dict, unpaired_removed, unpaired_added) where
    paired_dict maps module_name -> {"removed": [...], "added": [...]}.
    """
    import_from_re = re.compile(r'from\s+"([^"]+)"')

    def get_module(entry_text):
        m = import_from_re.search(entry_text)
        return m.group(1) if m else None

    def is_import_entry(entry_text):
        first_line = entry_text.split("\n")[0]
        return "import@" in first_line or "import " in first_line

    removed_by_mod = {}
    removed_other = []
    for entry in removed_entries:
        if is_import_entry(entry):
            mod = get_module(entry)
            if mod:
                removed_by_mod.setdefault(mod, []).append(entry)
            else:
                removed_other.append(entry)
        else:
            removed_other.append(entry)

    added_by_mod = {}
    added_other = []
    for entry in added_entries:
        if is_import_entry(entry):
            mod = get_module(entry)
            if mod:
                added_by_mod.setdefault(mod, []).append(entry)
            else:
                added_other.append(entry)
        else:
            added_other.append(entry)

    # Modules present in both removed and added = import style changes
    paired = {}
    for mod in set(removed_by_mod) & set(added_by_mod):
        paired[mod] = {
            "removed": removed_by_mod[mod],
            "added": added_by_mod[mod],
        }

    # Unpaired: imports for modules only in one side + non-imports
    unpaired_removed = removed_other[:]
    for mod, entries in removed_by_mod.items():
        if mod not in paired:
            unpaired_removed.extend(entries)

    unpaired_added = added_other[:]
    for mod, entries in added_by_mod.items():
        if mod not in paired:
            unpaired_added.extend(entries)

    return paired, unpaired_removed, unpaired_added
