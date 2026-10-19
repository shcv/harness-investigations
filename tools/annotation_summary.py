"""Shared helpers for annotation pre-pass output.

Used by sync.py (hybrid changelog mode) and the standalone
verify_annotations.py / generate_annotated_changelog.py tools so that claim
verification and the prompt summary behave the same everywhere.
"""

import re

POSITIVE_CLAIM_TYPES = {"new_feature", "enhancement", "bug_fix", "infrastructure"}

# Distinctive names that make better search terms than anything regex-derived.
KNOWN_FEATURES = [
    "AskUserQuestion", "TodoWrite", "Skill", "ListMcpResources",
    "CreateWorktree", "TaskCreate", "TaskUpdate", "TaskList",
    "ListMcpResourcesTool", "SubagentStop", "PreToolUse", "PostToolUse",
    "mcp-cli", "ENABLE_EXPERIMENTAL_MCP_CLI", "--mcp-cli",
    "ConfigChange", "TaskCompleted", "HttpHook", "--worktree", "--tmux",
    "tengu_crystal_beam", "tengu_tool_input_aliasing",
    "claudeMdExcludes", "disableAllHooks", "remoteControlAtStartup",
    "replBridgeEnabled", "mcp-needs-auth-cache",
]
GENERIC_WORDS = {"CRITICAL", "IMPORTANT", "DISABLED", "ENABLED", "DEFAULT"}
GENERIC_FLAGS = {
    "--json", "--help", "--version", "--debug", "--verbose",
    "--output", "--format", "--ignore", "--include", "--exclude",
    "--timeout", "--host", "--port", "--path", "--config", "--log",
}


def _evidence_text(ann: dict, sep: str = " ") -> str:
    evidence = ann.get("evidence", "") or ""
    if isinstance(evidence, list):
        evidence = sep.join(str(e) for e in evidence)
    return evidence


def primary_evidence_term(ann: dict) -> "str | None":
    """Return the most distinctive searchable term for an annotation's claim.

    Priority: known feature names, env-var-like names, non-generic CLI flags,
    then long quoted strings from the evidence.
    """
    evidence = _evidence_text(ann)
    combined = f"{evidence} {ann.get('name') or ''} {ann.get('summary') or ''}"
    for name in KNOWN_FEATURES:
        if name in combined:
            return name
    for var in re.findall(r'\b([A-Z][A-Z0-9_]{7,})\b', combined)[:2]:
        if var not in GENERIC_WORDS:
            return var
    flags = [f for f in re.findall(r'(--[\w-]{4,})', combined) if f not in GENERIC_FLAGS]
    if flags:
        return flags[0]
    quoted = re.findall(r'"([^"]{10,})"', evidence)
    return quoted[0] if quoted else None


def format_annotation_summary(annotations: list, version: str) -> str:
    """Format annotations as a compact importance-tiered summary for a prompt."""
    tier1 = sorted(
        [a for a in annotations if a.get("importance", 0) >= 4],
        key=lambda a: (-a.get("importance", 0), not a.get("user_facing", False)),
    )
    tier2 = sorted(
        [a for a in annotations if a.get("importance", 0) == 3],
        key=lambda a: (not a.get("user_facing", False), a.get("component", "")),
    )
    tier3 = sorted(
        [a for a in annotations if a.get("importance", 0) <= 2],
        key=lambda a: a.get("component", ""),
    )

    def fmt(ann):
        comp = ann.get("component", "?")
        ct = (ann.get("change_type") or "?")[:8]
        imp = ann.get("importance", "?")
        name = ann.get("name", "?")
        summary = ann.get("summary", "")
        evidence = _evidence_text(ann, "; ")
        uf = "★" if ann.get("user_facing") else " "
        flag = ann.get("feature_flag", "")
        dis = ann.get("disabled", False)
        flag_str = f" [{flag}{'!disabled' if dis else ''}]" if flag else ""
        ev_short = evidence[:60].split("\n")[0] if evidence else ""
        return f"  [{comp}/{ct}]{uf}i={imp} {name}: {summary[:80]} | {ev_short}{flag_str}"

    lines = [
        f"## Pre-analyzed Changes for {version}",
        f"## Total: {len(annotations)} entries across 3 tiers",
        "##",
        "## Format: [component/type]★=user-facing i=importance | evidence [FLAG if gated]",
        "## Tiers: HIGH=4-5 (lead features), NOTABLE=3 (improvements), LOW=1-2 (internal)",
        "##",
        "## - HIGH: include all user-facing (★); summarize patterns for non-★",
        "## - NOTABLE: include if clearly user-visible, skip pure infrastructure",
        "## - LOW: context only; may note patterns (e.g. 'several internal refactors')",
        "## - [FLAG] items: if disabled=true, put in 'In Development' section",
        "## - refactor change_type: code reorganized but feature still exists",
        "",
        f"### HIGH IMPORTANCE (i=4-5, {len(tier1)} items)",
    ]
    lines.extend(fmt(ann) for ann in tier1)
    lines.append("")
    lines.append(f"### NOTABLE (i=3, {len(tier2)} items)")
    lines.extend(fmt(ann) for ann in tier2)
    lines.append("")
    lines.append(f"### LOW / INTERNAL (i=1-2, {len(tier3)} items — context only)")
    lines.extend(fmt(ann) for ann in tier3)
    return "\n".join(lines)
