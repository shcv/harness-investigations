#!/usr/bin/env python3
"""
Parse a filtered astdiff changes file into batches suitable for annotation.

Two batching modes:
  linear    (default) — consecutive changes grouped by section, fixed batch size
  callgraph           — group by call-graph connectivity among changed functions

Output: list of dicts with section, names, content.
"""

import re
import json
import sys
from pathlib import Path
from collections import Counter
from pipeline_io import write_json


SECTION_PATTERNS = {
    "added":      re.compile(r'^\+\+\+ Added (\S+)'),
    "removed":    re.compile(r'^--- Removed (\S+)'),
    # Structural/string headers: @@@ function 'PHz' (was 'b2z') — structural
    # Capture the quoted identifier, not the type keyword (function/class/variable)
    "structural": re.compile(r"^@@@ \S+ '([^']+)' .*\u2014 structural"),
    "string":     re.compile(r"^@@@ \S+ '([^']+)' .*\u2014 string-only"),
    "import":     re.compile(r'^"([^"]+)":'),  # import section module headers
}

SECTION_HEADER = re.compile(r'^=== (.+) ===$')

# Regex to extract identifiers from minified JS bodies.
# Matches JS identifiers (including $/_) preceded/followed by non-identifier chars.
IDENT_RE = re.compile(r'(?<![A-Za-z0-9_$])([A-Za-z_$][A-Za-z0-9_$]*)(?![A-Za-z0-9_$])')
MAX_BATCH_CHARS = 60_000


def bound_batches(batches: list[dict], max_chars: int = MAX_BATCH_CHARS) -> list[dict]:
    """Bound requests even when one changed function is enormous.

    Preserve every character; label partial code so absence in an excerpt is
    not mistaken for a removed capability. Prefer splitting at line endings.
    """
    bounded = []
    for batch in batches:
        content = batch["content"]
        if len(content) <= max_chars:
            bounded.append({**batch, "id": len(bounded) + 1})
            continue
        context = "Original identifiers: " + ", ".join(batch["names"])
        budget = max_chars - len(context) - 192
        if budget < 1:
            raise ValueError("max_chars is too small for the batch identifiers")
        parts = []
        start = 0
        while start < len(content):
            end = min(start + budget, len(content))
            if end < len(content):
                newline = content.rfind("\n", start + budget // 2, end)
                if newline != -1:
                    end = newline + 1
            parts.append(content[start:end])
            start = end
        for index, part in enumerate(parts, 1):
            prefix = (f"Partial batch excerpt {index}/{len(parts)}. "
                      "Code may continue in other excerpts; do not infer removal from absence here.\n"
                      f"{context}\n\n")
            bounded.append({**batch, "id": len(bounded) + 1,
                            "content": prefix + part, "_part": index, "_parts": len(parts)})
    return bounded


def write_batches(batches: list[dict], out: Path) -> None:
    """Refresh slicer-owned inputs and discard batches no longer in the diff."""
    out.mkdir(parents=True, exist_ok=True)
    expected = {f"batch-{batch['id']:03d}.json" for batch in batches}
    for path in out.glob("batch-*.json"):
        match = re.fullmatch(r"(batch-[0-9]+)(?:-annotations)?\.json", path.name)
        if match and match[1] + ".json" not in expected:
            path.unlink()
    for batch in batches:
        write_json(out / f"batch-{batch['id']:03d}.json", batch)


def parse_slices(path: Path) -> list[dict]:
    """Return list of {section, name, content} dicts, one per change block."""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    if any(line.startswith("diff --git ") for line in lines):
        return parse_unified_slices(lines)
    slices = []
    current_section = None
    current_name = None
    current_lines = []
    i = 0

    def flush():
        if current_name and current_lines:
            slices.append({
                "section": current_section,
                "name": current_name,
                "content": "".join(current_lines).rstrip(),
            })

    while i < len(lines):
        line = lines[i]

        # Section headers
        m = SECTION_HEADER.match(line)
        if m:
            flush()
            current_section = m.group(1).lower().replace(" ", "_")
            current_name = None
            current_lines = []
            i += 1
            continue

        # Skip import section entirely (grouped separately)
        if current_section == "import_style_changes":
            i += 1
            continue

        # Change block headers
        matched = False
        for sect_key, pat in SECTION_PATTERNS.items():
            if sect_key == "import":
                continue
            m = pat.match(line)
            # Match if section key is a prefix of current_section
            if m and current_section is not None and current_section.startswith(sect_key):
                flush()
                current_name = m.group(1)
                current_lines = [line]
                matched = True
                break

        if not matched:
            if current_name is not None:
                current_lines.append(line)

        i += 1

    flush()
    return slices


def parse_unified_slices(lines: list[str]) -> list[dict]:
    """Keep file context on each Git diff hunk for non-AST projects."""
    slices = []
    header = []
    body = []
    name = ""
    section = "modified"

    def flush():
        if body:
            slices.append({"section": section, "name": name,
                           "content": "".join(header + body).rstrip()})

    for line in lines:
        if line.startswith("diff --git "):
            flush()
            header, body = [line], []
            name = line.strip()
            section = "modified"
        elif line.startswith("@@ "):
            flush()
            body = [line]
        elif body:
            body.append(line)
        else:
            header.append(line)
            if line.startswith("new file mode "):
                section = "added"
            elif line.startswith("deleted file mode "):
                section = "removed"
    flush()
    return slices


# ── Linear batching ───────────────────────────────────────────────────────────

def make_batches(slices: list[dict], batch_size: int = 12) -> list[dict]:
    """Group slices into batches by section, each at most batch_size items."""
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    from itertools import islice as _islice

    def chunked(iterable, n):
        it = iter(iterable)
        while True:
            chunk = list(_islice(it, n))
            if not chunk:
                break
            yield chunk

    batches = []
    sections = {}
    for s in slices:
        sections.setdefault(s["section"], []).append(s)

    batch_id = 0
    for section, items in sections.items():
        for chunk in chunked(items, batch_size):
            batch_id += 1
            content = "\n\n".join(
                f"[{s['name']}]\n{s['content']}" for s in chunk
            )
            batches.append({
                "id": batch_id,
                "section": section,
                "names": [s["name"] for s in chunk],
                "count": len(chunk),
                "content": content,
            })

    return bound_batches(batches)


# ── Call graph batching ───────────────────────────────────────────────────────

def build_call_graph(slices: list[dict]) -> dict[int, set[int]]:
    """Build an undirected call graph among changed functions.

    Nodes: slice indices (each slice is a changed function/variable).
    Edges: slice i → slice j if j's name appears as an identifier in i's body,
           or vice versa.

    The same function name may appear in multiple sections (e.g., both 'removed'
    and 'added' when a function is reimplemented). All slices with the same name
    are connected to each other and to slices that reference that name.
    """
    # Map name → list of slice indices (name may appear in multiple sections)
    name_to_idx: dict[str, list[int]] = {}
    for i, s in enumerate(slices):
        name_to_idx.setdefault(s["name"], []).append(i)

    all_names = set(name_to_idx)
    graph: dict[int, set[int]] = {i: set() for i in range(len(slices))}

    # First: connect all slices sharing the same name (reimplemented functions)
    for name, indices in name_to_idx.items():
        for i in indices:
            for j in indices:
                if i != j:
                    graph[i].add(j)
                    graph[j].add(i)

    # Second: connect slices that reference each other's names in their bodies
    for i, s in enumerate(slices):
        tokens = set(IDENT_RE.findall(s["content"]))
        refs = tokens & all_names - {s["name"]}
        for ref in refs:
            for j in name_to_idx[ref]:
                if j != i:
                    graph[i].add(j)
                    graph[j].add(i)

    return graph


def connected_components(graph: dict[int, set[int]], n: int) -> list[list[int]]:
    """BFS to find all connected components. Returns list of node-index lists."""
    visited: set[int] = set()
    components: list[list[int]] = []
    for start in range(n):
        if start not in visited:
            comp: list[int] = []
            queue = [start]
            while queue:
                node = queue.pop()
                if node in visited:
                    continue
                visited.add(node)
                comp.append(node)
                queue.extend(graph[node] - visited)
            components.append(comp)
    return components


def callgraph_stats(slices: list[dict], graph: dict, components: list[list[int]]) -> None:
    """Print call graph analysis statistics."""
    n = len(slices)
    edges = sum(len(nbrs) for nbrs in graph.values()) // 2

    print(f"\n{'='*60}")
    print("CALL GRAPH STATISTICS")
    print(f"{'='*60}")
    print(f"  Nodes (changed functions): {n}")
    print(f"  Edges (cross-references):  {edges}")
    print(f"  Components:                {len(components)}")

    sizes = [len(c) for c in components]
    singleton = sum(1 for s in sizes if s == 1)
    print(f"  Singletons (isolated):     {singleton} ({100*singleton//n}%)")
    print(f"  Largest component:         {max(sizes)}")
    print(f"  Median component size:     {sorted(sizes)[len(sizes)//2]}")

    # Histogram
    print("\n  Component size distribution:")
    size_hist = Counter()
    for s in sizes:
        bucket = s if s <= 5 else (10 if s <= 10 else (20 if s <= 20 else (50 if s <= 50 else 999)))
        size_hist[bucket] += 1
    for bucket in sorted(size_hist):
        label = str(bucket) if bucket <= 20 else ("21-50" if bucket == 50 else "51+")
        bar = "█" * size_hist[bucket]
        print(f"    size {label:>5}: {size_hist[bucket]:4d}  {bar[:50]}")

    # Show large components
    large = sorted([c for c in components if len(c) >= 5], key=lambda c: -len(c))[:5]
    if large:
        print(f"\n  Largest components (top {len(large)}):")
        for comp in large:
            names = [slices[i]["name"] for i in comp]
            sections = Counter(slices[i]["section"] for i in comp)
            sec_str = ", ".join(f"{k}:{v}" for k, v in sections.most_common())
            print(f"    size={len(comp):3d} [{sec_str}]: {', '.join(names[:8])}{'...' if len(names)>8 else ''}")

    # Hub nodes: high-degree nodes that connect many components
    degrees = [(len(graph[i]), slices[i]["name"]) for i in range(n)]
    degrees.sort(reverse=True)
    print("\n  Top hub nodes (most connections):")
    for deg, name in degrees[:10]:
        sec = slices[next(i for i in range(n) if slices[i]["name"] == name)]["section"]
        print(f"    {name:12s} [{sec:12s}] degree={deg}")


def majority_section(comp: list[int], slices: list[dict]) -> str:
    """Return the most common section among slices in component."""
    votes: dict[str, int] = {}
    for i in comp:
        sec = slices[i]["section"]
        votes[sec] = votes.get(sec, 0) + 1
    return max(votes, key=votes.get)  # type: ignore[arg-type]


def make_batches_callgraph(
    slices: list[dict],
    batch_size: int = 12,
    max_hub_degree: int = 0,
) -> tuple[list[dict], dict, list[list[int]]]:
    """Group slices by call-graph connectivity.

    Returns (batches, graph, components) so callers can inspect the graph.

    max_hub_degree: if > 0, nodes with degree > this threshold are treated as
    "hub" nodes (popular utilities) and do NOT create edges to other nodes —
    they're placed in their own batch. Set 0 to disable (include all edges).
    """
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    graph = build_call_graph(slices)

    if max_hub_degree > 0:
        # Remove hub edges: hubs are still in the graph as nodes but don't bridge
        hub_indices = {i for i, nbrs in graph.items() if len(nbrs) > max_hub_degree}
        if hub_indices:
            print(f"  Filtering {len(hub_indices)} hub nodes (degree > {max_hub_degree})")
            for i in hub_indices:
                for j in list(graph[i]):
                    graph[j].discard(i)
                graph[i] = set()

    components = connected_components(graph, len(slices))
    # Sort: process largest components first (greedy bin-packing works better)
    components_sorted = sorted(components, key=lambda c: -len(c))

    batches: list[dict] = []
    batch_id = 0
    current_batch_indices: list[int] = []
    current_section: str = ""

    def flush_batch():
        nonlocal batch_id, current_batch_indices, current_section
        if not current_batch_indices:
            return
        batch_id += 1
        items = [slices[i] for i in current_batch_indices]
        content = "\n\n".join(f"[{s['name']}]\n{s['content']}" for s in items)
        batches.append({
            "id": batch_id,
            "section": current_section or "mixed",
            "names": [s["name"] for s in items],
            "count": len(items),
            "content": content,
            "_mode": "callgraph",
        })
        current_batch_indices = []
        current_section = ""

    for comp in components_sorted:
        sec = majority_section(comp, slices)

        if len(comp) > batch_size:
            # Large component: split into sub-batches (lose some context, unavoidable)
            flush_batch()
            for chunk_start in range(0, len(comp), batch_size):
                chunk = comp[chunk_start : chunk_start + batch_size]
                batch_id += 1
                items = [slices[i] for i in chunk]
                content = "\n\n".join(f"[{s['name']}]\n{s['content']}" for s in items)
                batches.append({
                    "id": batch_id,
                    "section": sec,
                    "names": [s["name"] for s in items],
                    "count": len(items),
                    "content": content,
                    "_mode": "callgraph",
                    "_component_size": len(comp),
                    "_split": True,
                })
        elif len(current_batch_indices) + len(comp) > batch_size:
            # Current batch full: flush and start new
            flush_batch()
            current_batch_indices = list(comp)
            current_section = sec
        else:
            current_batch_indices.extend(comp)
            if not current_section:
                current_section = sec

    flush_batch()
    return bound_batches(batches), graph, components


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("changes_file")
    p.add_argument("--batch-size", type=int, default=12)
    p.add_argument("--mode", choices=["linear", "callgraph"], default="linear",
                   help="Batching mode: linear (default) or callgraph")
    p.add_argument("--hub-degree", type=int, default=0,
                   help="(callgraph mode) Max degree before a node is treated as a hub. 0=disabled.")
    p.add_argument("--out-dir", help="Write batch files here (one JSON per batch)")
    p.add_argument("--summary", action="store_true",
                   help="Print summary statistics (callgraph mode also shows graph stats)")
    args = p.parse_args()

    path = Path(args.changes_file)
    slices = parse_slices(path)

    if args.mode == "callgraph":
        print(f"Building call graph for {len(slices)} slices...")
        batches, graph, components = make_batches_callgraph(
            slices, args.batch_size, args.hub_degree
        )

        if args.summary:
            callgraph_stats(slices, graph, components)
            print(f"\nCall-graph batches (size {args.batch_size}): {len(batches)}")
            for b in batches:
                split_note = " [split]" if b.get("_split") else ""
                comp_note = f" (component={b.get('_component_size',len(b['names']))})" if b.get("_split") else ""
                print(f"  batch {b['id']:02d} [{b['section']}]: {b['count']} items{split_note}{comp_note}")

    else:  # linear
        batches = make_batches(slices, args.batch_size)

        if args.summary:
            section_counts: dict[str, int] = {}
            for s in slices:
                section_counts[s["section"]] = section_counts.get(s["section"], 0) + 1
            print(f"Total slices: {len(slices)}")
            for k, v in section_counts.items():
                print(f"  {k}: {v}")
            print(f"Total batches (size {args.batch_size}): {len(batches)}")
            for b in batches:
                print(f"  batch {b['id']:02d} [{b['section']}]: {b['count']} items")

    if args.out_dir:
        out = Path(args.out_dir)
        write_batches(batches, out)
        print(f"Wrote {len(batches)} batch files to {out}")
    elif not args.summary:
        json.dump(batches, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
