#!/usr/bin/env python3
"""
Changelog Cleanup Tool

Cleans up LLM-generated changelogs by:
1. Removing duplicate headers and meta-commentary
2. Removing emoji from section headers
3. Collapsing empty sections
4. Removing horizontal rules (---) that Discord doesn't render
5. Standardizing formatting
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from colors import Colors, colored, print_success, print_warning, print_error

# Shared patterns that identify LLM meta-commentary (not changelog content).
# Used by both pre-heading and post-heading preamble removal.
LLM_META_PATTERNS = [
    r'(?i)now\s+i\s+have\s+enough\s+information',
    r'(?i)let\s+me\s+summarize',
    r'(?i)let\s+me\s+analyze',
    r'(?i)based\s+on\s+(the\s+)?diff',
    r'(?i)i\'ll\s+analyze',
    r'(?i)i\s+will\s+analyze',
    r'(?i)here\'s\s+(the\s+)?changelog',
    r'(?i)here\s+is\s+(the\s+)?changelog',
    r'(?i)after\s+reviewing',
    r'(?i)after\s+analyzing',
    r'(?i)looking\s+at\s+the\s+diff',
    r'(?i)that\'?s\s+the\s+complete',
    r'(?i)that\'?s\s+my\s+analysis',
    r'(?i)this\s+completes\s+the',
    r'(?i)i\'?ve\s+completed',
    r'(?i)i\s+have\s+completed',
    r'(?i)i\'?ve\s+analyzed',
    r'(?i)i\s+have\s+analyzed',
    r'(?i)the\s+above\s+covers',
    r'(?i)this\s+is\s+(the\s+)?complete',
]


def print_info(msg: str):
    """Print a cyan info message with info symbol prefix"""
    print(colored(f"ℹ {msg}", Colors.CYAN))


def remove_preamble(content: str) -> Tuple[str, bool]:
    """
    Remove LLM preamble text that appears before the changelog heading.

    Common patterns:
      - "Now I have enough information..."
      - "Let me summarize the changes..."
      - "Based on the diff..."
      - Bullet point summaries before the actual heading
    """
    lines = content.split('\n')

    # Find the first H1 changelog header
    h1_pattern = re.compile(r'^#\s+Changelog\s+for\s+v?(ersion\s+)?', re.IGNORECASE)
    h1_index = None
    for i, line in enumerate(lines):
        if h1_pattern.match(line):
            h1_index = i
            break

    if h1_index is None or h1_index == 0:
        return content, False

    # Check if content before the H1 looks like preamble
    preamble_content = '\n'.join(lines[:h1_index]).strip()

    # Common LLM preamble patterns
    preamble_patterns = LLM_META_PATTERNS + [
        r'(?i)^\*\*new\s+features?\*\*',  # Markdown bold summary headers
        r'(?i)^\*\*internal',
        r'(?i)^\*\*improvements?\*\*',
    ]

    is_preamble = any(re.search(pat, preamble_content) for pat in preamble_patterns)

    if is_preamble:
        # Remove everything before the first H1
        cleaned_lines = lines[h1_index:]
        return '\n'.join(cleaned_lines), True

    return content, False


def remove_duplicate_headers(content: str, version: str) -> Tuple[str, bool]:
    """
    Remove duplicate H1 headers and meta-commentary between them.

    Pattern to fix:
      # Changelog for version X.X.X

      [LLM commentary about generating changelog]

      # Changelog for version X.X.X  <-- Remove from first H1+1 to second H1

      ## Actual Content...
    """
    lines = content.split('\n')

    # Find all H1 changelog headers
    h1_pattern = re.compile(r'^#\s+Changelog\s+for\s+v?(ersion\s+)?', re.IGNORECASE)
    h1_indices = [i for i, line in enumerate(lines) if h1_pattern.match(line)]

    if len(h1_indices) <= 1:
        return content, False

    first_h1 = h1_indices[0]
    second_h1 = h1_indices[1]

    # Check if content between is just meta-commentary
    # Use a larger threshold and also check for preamble patterns
    between_content = '\n'.join(lines[first_h1 + 1:second_h1]).strip()

    # Common patterns that indicate meta-commentary between duplicate headers
    meta_patterns = [
        r'(?i)now\s+i\s+have',
        r'(?i)let\s+me',
        r'(?i)^\*\*',  # Markdown bold (often used in quick summaries)
        r'(?i)^-\s+',  # Bullet points
        r'(?i)^\d+\.',  # Numbered lists
    ]

    is_meta = (
        len(between_content) < 1500 or  # Increased threshold
        any(re.search(pat, between_content) for pat in meta_patterns)
    )

    if is_meta:
        # Keep first H1, skip to content after second H1
        cleaned_lines = lines[:first_h1 + 1] + [''] + lines[second_h1 + 1:]
        return '\n'.join(cleaned_lines), True

    return content, False


def remove_post_heading_preamble(content: str) -> Tuple[str, bool]:
    """
    Remove LLM meta-commentary that appears AFTER the H1 heading.

    This handles the case where sync.py prepends "# Changelog for version X"
    and the LLM output starts with meta-commentary like "That's the complete
    analysis..." before any ## section, or between the H1 and first H2.
    """
    lines = content.split('\n')

    # Find H1 and first sub-heading (## or ### or deeper)
    h1_index = None
    sub_heading_index = None
    h1_pattern = re.compile(r'^#\s+(?!#)')
    sub_heading_pattern = re.compile(r'^#{2,}\s+')

    for i, line in enumerate(lines):
        if h1_index is None and h1_pattern.match(line):
            h1_index = i
        elif h1_index is not None and sub_heading_pattern.match(line):
            sub_heading_index = i
            break

    if h1_index is None:
        return content, False

    # Get content between H1 and first sub-heading (or end of file)
    end_index = sub_heading_index if sub_heading_index is not None else len(lines)
    between_lines = lines[h1_index + 1:end_index]
    between_content = '\n'.join(between_lines).strip()

    if not between_content:
        return content, False

    # Check if content starts with meta-commentary
    if not any(re.search(pat, between_content) for pat in LLM_META_PATTERNS):
        return content, False

    if sub_heading_index is not None:
        # Has structured sections after — strip meta-text between H1 and first section
        cleaned_lines = lines[:h1_index + 1] + [''] + lines[sub_heading_index:]
        return '\n'.join(cleaned_lines), True

    # No sub-headings at all — content is an unstructured paragraph
    # Strip the leading meta sentence, keep factual content
    sentence_split = re.split(r'\.\s+', between_content, maxsplit=1)
    if len(sentence_split) > 1:
        stripped = sentence_split[1].strip()
    else:
        stripped = ''

    if stripped:
        # Wrap surviving factual content in a ## Summary section
        cleaned_lines = lines[:h1_index + 1] + ['', '## Summary', '', stripped, '']
    else:
        # Nothing left — keep just the heading
        cleaned_lines = lines[:h1_index + 1] + ['']

    return '\n'.join(cleaned_lines), True


def remove_emoji_from_headers(content: str) -> Tuple[str, bool]:
    """
    Remove emoji from markdown headers (## lines).

    Examples:
      ## 🎯 Highlights  ->  ## Highlights
      ## 🚀 New Features  ->  ## New Features
      ## ⚡ Improvements  ->  ## Improvements
    """
    # Pattern matches: ## followed by optional emoji(s) and text
    # Emoji ranges: most common emoji are in these Unicode ranges
    emoji_pattern = re.compile(
        r'^(#{1,6})\s*'  # Header markers
        r'[\U0001F300-\U0001F9FF\U00002600-\U000027BF\U0001FA00-\U0001FAFF\u2300-\u23FF\u2B50\u26A0\u2705\u274C\u2728\u2764\u200D]*'  # Emoji
        r'\s*'  # Optional space after emoji
        r'(.+)$',  # Actual header text
        re.MULTILINE
    )

    new_content = emoji_pattern.sub(r'\1 \2', content)

    # Clean up any double spaces that might result
    new_content = re.sub(r'^(#{1,6})\s+', r'\1 ', new_content, flags=re.MULTILINE)

    return new_content, new_content != content


def collapse_empty_sections(content: str) -> Tuple[str, bool]:
    """
    Remove sections that have a header but no content.

    Examples:
      ## Bug Fixes

      ## Notes  ->  (Bug Fixes section removed entirely)
    """
    lines = content.split('\n')
    result_lines = []
    i = 0
    modified = False

    while i < len(lines):
        line = lines[i]

        # Check if this is a section header (## or ###)
        header_match = re.match(r'^(#{2,3})\s+', line)
        if header_match:
            level = len(header_match.group(1))
            # Look ahead to see if there's content before next header or end
            j = i + 1
            has_content = False

            while j < len(lines):
                next_line = lines[j].strip()

                # Skip blank lines
                if not next_line:
                    j += 1
                    continue

                # Check if we hit another header
                next_header = re.match(r'^(#{1,6})\s+', next_line)
                if next_header:
                    # A deeper heading is a sub-section — i.e. this header's
                    # content. Only a same-or-shallower heading means this
                    # section truly has no body (e.g. "## New Features" whose
                    # only content is "### Feature" must be kept).
                    if len(next_header.group(1)) > level:
                        has_content = True
                    break

                # Check if we hit a horizontal rule (section separator)
                if next_line == '---':
                    j += 1
                    continue

                # Found actual content
                has_content = True
                break

            if has_content:
                result_lines.append(line)
            else:
                # Skip this empty section header
                modified = True
                # Also skip any trailing blank lines or ---
                while i + 1 < len(lines) and (not lines[i + 1].strip() or lines[i + 1].strip() == '---'):
                    i += 1
        else:
            result_lines.append(line)

        i += 1

    return '\n'.join(result_lines), modified


def remove_trailing_separators(content: str) -> Tuple[str, bool]:
    """
    Remove trailing --- separators at the end of the document.
    """
    lines = content.rstrip().split('\n')

    # Remove trailing --- and blank lines
    while lines and (not lines[-1].strip() or lines[-1].strip() == '---'):
        lines.pop()

    new_content = '\n'.join(lines) + '\n'
    return new_content, new_content != content


def remove_horizontal_rules(content: str) -> Tuple[str, bool]:
    """
    Remove horizontal rule separators (---) from the document.

    Discord doesn't render --- as horizontal rules, so these just appear
    as literal text. Remove them and rely on blank lines for visual separation.
    """
    lines = content.split('\n')
    result_lines = []
    modified = False

    for line in lines:
        # Check if this is a standalone horizontal rule (just --- or ---)
        if line.strip() == '---':
            modified = True
            # Skip this line entirely
            continue
        result_lines.append(line)

    return '\n'.join(result_lines), modified


def debold_field_labels(content: str) -> Tuple[str, bool]:
    """
    Remove bold formatting from field labels like **What**: → What:

    Bold labels compete visually with ### feature headings, making it hard
    to distinguish heading hierarchy. Plain text labels with colons are
    sufficient visual cues.
    """
    label_pattern = re.compile(
        r'^\*\*(What|Evidence|Details|Status|Usage|Orphaned Tip)\*\*:',
        re.MULTILINE
    )
    new_content = label_pattern.sub(r'\1:', content)
    return new_content, new_content != content


def add_feature_spacing(content: str) -> Tuple[str, bool]:
    """
    Ensure a double blank line before ### feature headings.

    Within a feature, subsections (What/Evidence/Details) are separated by
    single blank lines. Between features, a double blank line provides
    clear visual separation.
    """
    # Match ### headings that don't already have a double blank line before them.
    # But skip the very first ### after a ## section heading.
    lines = content.split('\n')
    result = []
    modified = False

    for i, line in enumerate(lines):
        if re.match(r'^###\s+', line) and i >= 2:
            # Check what's above: skip if preceded by ## heading (with optional blank)
            prev_nonblank = None
            for j in range(i - 1, -1, -1):
                if lines[j].strip():
                    prev_nonblank = lines[j]
                    break

            if prev_nonblank and re.match(r'^##\s+(?!#)', prev_nonblank):
                # This ### directly follows a ## section heading — don't add extra space
                result.append(line)
                continue

            # Count blank lines immediately before this ###
            blank_count = 0
            for j in range(i - 1, -1, -1):
                if lines[j].strip() == '':
                    blank_count += 1
                else:
                    break

            if blank_count < 2:
                # Add blank lines to reach 2
                needed = 2 - blank_count
                for _ in range(needed):
                    result.append('')
                    modified = True

        result.append(line)

    return '\n'.join(result), modified


def normalize_blank_lines(content: str) -> Tuple[str, bool]:
    """
    Normalize multiple consecutive blank lines to at most 2.
    """
    # Replace 3+ consecutive newlines with 2
    new_content = re.sub(r'\n{4,}', '\n\n\n', content)
    return new_content, new_content != content


def cleanup_changelog(content: str, version: str) -> Tuple[str, bool]:
    """
    Apply all cleanup transformations to a changelog.

    Returns:
        tuple of (cleaned_content, was_modified)
    """
    original_content = content
    modified = False

    # Apply each transformation in order
    transformations = [
        ('preamble', remove_preamble),
        ('duplicate headers', lambda c: remove_duplicate_headers(c, version)),
        ('post-heading preamble', remove_post_heading_preamble),
        ('emoji in headers', remove_emoji_from_headers),
        ('bold field labels', debold_field_labels),
        ('feature spacing', add_feature_spacing),
        ('empty sections', collapse_empty_sections),
        ('trailing separators', remove_trailing_separators),
        ('horizontal rules', remove_horizontal_rules),
        ('blank lines', normalize_blank_lines),
    ]

    for name, transform in transformations:
        content, changed = transform(content)
        if changed:
            modified = True

    return content, modified


def process_file(file_path: Path, dry_run: bool = False, verbose: bool = False) -> bool:
    """Process a single changelog file."""
    try:
        content = file_path.read_text()
    except Exception as e:
        print_error(f"Could not read {file_path.name}: {e}")
        return False

    # Extract version from filename
    match = re.match(r'changelog-v?(.+)\.md$', file_path.name)
    version = match.group(1) if match else "unknown"

    cleaned_content, was_modified = cleanup_changelog(content, version)

    if not was_modified:
        if verbose:
            print_info(f"{file_path.name}: No changes needed")
        return True

    if dry_run:
        print_warning(f"{file_path.name}: Would be modified (dry run)")
        orig_lines = len(content.split('\n'))
        new_lines = len(cleaned_content.split('\n'))
        print_info(f"  Lines: {orig_lines} → {new_lines} ({orig_lines - new_lines} removed)")
        return True

    try:
        file_path.write_text(cleaned_content)
        orig_lines = len(content.split('\n'))
        new_lines = len(cleaned_content.split('\n'))
        print_success(f"{file_path.name}: Cleaned ({orig_lines - new_lines} lines removed)")
        return True
    except Exception as e:
        print_error(f"Could not write {file_path.name}: {e}")
        return False


def find_changelog_dir() -> Optional[Path]:
    """Find the changelog directory, searching up from cwd if needed."""
    # Try relative path first
    changelog_dir = Path("archive/claude-code/changelog")
    if changelog_dir.exists():
        return changelog_dir

    # Try from project root
    project_root = Path.cwd()
    while project_root != project_root.parent:
        test_dir = project_root / "archive" / "claude-code" / "changelog"
        if test_dir.exists():
            return test_dir
        # Also try without claude-code subdir for other projects
        test_dir = project_root / "archive" / "changelog"
        if test_dir.exists():
            return test_dir
        project_root = project_root.parent

    return None


def main():
    parser = argparse.ArgumentParser(
        description="Clean up changelog files by removing redundant content and standardizing format"
    )

    parser.add_argument(
        "files",
        nargs="*",
        help="Specific changelog files to process (default: all in archive/*/changelog/)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show status for unchanged files too"
    )

    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output"
    )

    args = parser.parse_args()

    if args.no_color or not sys.stdout.isatty():
        Colors.disable()

    # Determine files to process
    if args.files:
        files_to_process = [Path(f) for f in args.files]
    else:
        changelog_dir = find_changelog_dir()
        if not changelog_dir:
            print_error("Could not find changelog directory")
            print_info("Run from project root or specify files explicitly")
            return 1

        files_to_process = sorted(changelog_dir.glob("changelog-*.md"))

    if not files_to_process:
        print_warning("No changelog files found")
        return 0

    mode_str = " (dry run)" if args.dry_run else ""
    print_info(f"Processing {len(files_to_process)} file(s){mode_str}...")
    print()

    success_count = 0
    modified_count = 0

    for file_path in files_to_process:
        if not file_path.exists():
            print_error(f"File not found: {file_path}")
            continue

        try:
            original = file_path.read_text()
            if process_file(file_path, args.dry_run, args.verbose):
                success_count += 1
                if not args.dry_run:
                    current = file_path.read_text()
                    if current != original:
                        modified_count += 1
        except Exception as e:
            print_error(f"Error processing {file_path.name}: {e}")

    print()
    print(colored("=== Summary ===", Colors.BOLD + Colors.BLUE))
    print_success(f"Processed {success_count} of {len(files_to_process)} file(s)")
    if not args.dry_run and modified_count > 0:
        print_success(f"Modified {modified_count} file(s)")

    return 0 if success_count == len(files_to_process) else 1


if __name__ == "__main__":
    sys.exit(main())
