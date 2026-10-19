"""Build the per-version changelog prompt and the generation trailer.

Pure text assembly: sync.py gathers the inputs for a version into a
ChangelogInputs and these functions turn it into the agent prompt (which
refers to input files by path, so large diffs never travel as CLI arguments)
and the two-line trailer appended to the accepted changelog.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# How each primary-diff kind is labelled in the changelog trailer.
PRIMARY_DIFF_LABELS = {
    "astdiff": "astdiff",
    "astdiff-unfiltered": "astdiff (unfiltered)",
    "raw": "raw diff",
}


@dataclass
class ChangelogInputs:
    version: str
    primary_diff_path: Path
    primary_diff_kind: str  # a key of PRIMARY_DIFF_LABELS
    string_diff_path: Optional[Path] = None
    modules_path: Optional[Path] = None
    release_notes_path: Optional[Path] = None
    unreleased_tag: Optional[str] = None
    annotation_summary: Optional[str] = None


def _modules_section(path: Path) -> str:
    return (
        f'\nSource extraction: this version uses split Bun modules. '
        f'The single JS file is an esbuild analysis snapshot; original '
        f'module sources are in {path.resolve()}. Rebundling '
        f'changes wrappers, names, and module order. Do not treat those '
        f'artifact changes as new product features. Read the original '
        f'module sources when the snapshot is unclear.\n'
    )


def _unreleased_section(tag_name: str) -> str:
    return f"""

## Release Status

The source tag `{tag_name}` exists, but no published GitHub Release was found
when this sync ran. Treat this as a significant intermediate/development
snapshot, not as an official published release. Do not invent official release
notes or imply that binaries/assets were published.
"""


def _release_notes_section(path: Path) -> str:
    return f"""

## Official Release Notes

Read the file `{path.resolve()}` first. It contains the published upstream release notes
for this version (or says that none were published).

Treat the published items as a floor: each one should appear in your changelog,
in whichever section its impact warrants, using the normal section order. Do
not add a separate section for them. If notable changes are missing from the
published notes, say so briefly in the summary.
"""


def _annotations_section(summary: str) -> str:
    return f"""

## Pre-analyzed Change Annotations (Agent Pre-pass)

The following annotations were produced by a fast model analyzing each change in
the diff. Use them as a prioritized guide — but also read the diff files below for
completeness, as the annotations may miss some features.

{summary}
"""


def primary_diff_section(path: Path, kind: str) -> str:
    """Describe the primary code diff for the changelog agent."""
    rel = path.resolve()
    if kind == "astdiff":
        return f"""

## Code Changes (Filtered AST Diff)

Read the file `{rel}` to see structural code changes between versions.
Known version/build metadata changes have been filtered. Structural changes remain,
including matches scored at 100.0%; that score does not establish unchanged behavior.
Import changes are grouped by module. Use the Read tool with offset/limit if the
file is large.
"""
    if kind == "astdiff-unfiltered":
        return f"""

## Code Changes (AST Diff, Unfiltered)

Read the file `{rel}` to see structural code changes between versions.
Version-bump and build-metadata noise has NOT been filtered; skip those entries.
Use the Read tool with offset/limit if the file is large.
"""
    return f"""

## Code Changes (Raw Unified Diff)

Read the file `{rel}` to see code changes between versions in unified diff
format (`diff -u` output, or `git diff` for GitHub-based projects). No noise
filtering has been applied — skip formatting-only or version-bump hunks. Use
the Read tool with offset/limit if the file is large.
"""


def _string_diff_section(path: Path) -> str:
    return f"""

## String Literal Changes (AST-Extracted)

Read the file `{path.resolve()}` to see added/removed string literals between versions
(identifiers and code fragments filtered). Use this to identify user-facing
message changes, new settings, or renamed features.
"""


def _output_section(version: str, write_path: Optional[Path]) -> str:
    if write_path is not None:
        # Have the agent write the file itself. This avoids the "last
        # assistant message wins" failure mode where a wrap-up summary
        # overwrites the real body in ResultMessage.result.
        return f"""

## Output Instructions (CRITICAL)

Write the COMPLETE changelog to the file `{write_path}` using the Write tool.

- Begin the file with `# Changelog for version {version}` followed by a blank line.
- Follow the section structure in the system prompt.
- After calling the Write tool, your final assistant message should be a brief
  confirmation only (e.g. "Wrote changelog to {write_path}"). Do not echo
  the changelog body back in your final message.
"""
    # Read-only providers (Codex exec) return the body as the final message
    # and the caller writes the file.
    return f"""

## Output Instructions (CRITICAL)

Return the COMPLETE changelog markdown as your final answer.

- Begin with `# Changelog for version {version}` followed by a blank line.
- Follow the section structure in the system prompt.
- Do NOT edit files.
- Do NOT wrap the changelog in a Markdown code fence.
"""


def build_prompt(inputs: ChangelogInputs, write_path: Optional[Path]) -> str:
    """Assemble the user prompt; ``write_path`` selects Write-tool output."""
    parts = [f"Generate a changelog for version {inputs.version}."]
    if inputs.modules_path is not None:
        parts.append(_modules_section(inputs.modules_path))
    if inputs.unreleased_tag:
        parts.append(_unreleased_section(inputs.unreleased_tag))
    if inputs.release_notes_path is not None:
        parts.append(_release_notes_section(inputs.release_notes_path))
    if inputs.annotation_summary:
        parts.append(_annotations_section(inputs.annotation_summary))
    parts.append(primary_diff_section(inputs.primary_diff_path, inputs.primary_diff_kind))
    if inputs.string_diff_path is not None:
        parts.append(_string_diff_section(inputs.string_diff_path))
    parts.append(_output_section(inputs.version, write_path))
    return "".join(parts)


def retry_addendum(reason: str, write_path: Optional[Path]) -> str:
    """Extra instructions appended after a rejected attempt."""
    if write_path is not None:
        action = f"call the Write tool to write the COMPLETE changelog to `{write_path}`"
        noun = "file"
    else:
        action = "return the COMPLETE changelog markdown as your final answer"
        noun = "final answer"
    return f"""

## RETRY — previous attempt was rejected

Your previous output was rejected by the validator. Reason: {reason}

Do NOT produce a summary, an outline, or an overview. Read the diff files
fully (use Read with offset/limit if needed), then {action}.
The {noun} must contain multiple `## ` section headings with full
per-feature explanations.
"""


def format_trailer(
    inputs: ChangelogInputs,
    *,
    tool_version: str,
    provider: str,
    model: str,
    effort: Optional[str] = None,
    annotation_model: Optional[str] = None,
    expects_astdiff: bool = False,
) -> str:
    """Two lines: who generated the changelog, and from which inputs.

    The inputs line exists mainly to make a degraded run obvious: a project
    that expects astdiff but fell back to a raw diff produces noticeably
    weaker changelogs.
    """
    generator = f"Generated by `harness-investigations@{tool_version}` using {provider} `{model}`"
    if effort:
        generator += f" ({effort} effort)"

    used = []
    if inputs.annotation_summary:
        used.append(f"annotations (`{annotation_model}`)")
    label = PRIMARY_DIFF_LABELS[inputs.primary_diff_kind]
    if expects_astdiff and inputs.primary_diff_kind == "raw":
        label += " (astdiff unavailable)"
    used.append(label)
    if inputs.string_diff_path is not None:
        used.append("strings")
    if inputs.modules_path is not None:
        used.append("module sources")
    if inputs.release_notes_path is not None:
        used.append("release notes")
    return f"{generator}\nInputs: {', '.join(used)}"
