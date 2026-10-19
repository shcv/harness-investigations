#!/usr/bin/env python3
"""Verify annotation claims against the actual pretty source.

For REMOVAL claims: searches the NEW-version source. If the primary evidence
term is found, the feature still exists — downgrade to 'refactor'.

For POSITIVE claims (new_feature, enhancement, bug_fix): searches the
NEW-version source. If the primary evidence term is NOT found, the claim
is flagged as low-confidence (annotator may have cited non-existent evidence).

Outputs a corrected annotations JSON with:
  _removal_verified: bool      (on removal claims)
  _evidence_verified: bool     (on all verified positive claims)
  _removal_note / _evidence_note: explanation string

Usage: python3 verify_annotations.py [version] [--min-importance N]
  e.g.: python3 verify_annotations.py v2.1.48
"""
import json
import sys
from pathlib import Path

from annotation_summary import POSITIVE_CLAIM_TYPES as POSITIVE_TYPES, primary_evidence_term


def verify_claims(version: str, min_importance: int = 2):
    annotations_file = Path(f"archive/claude-code/changes/{version}/annotations-{version}.json")
    pretty_file = Path(f"archive/claude-code/pretty/pretty-{version}.js")

    if not annotations_file.exists():
        print(f"Error: {annotations_file} not found. Run annotate_changes.py first.")
        sys.exit(1)
    if not pretty_file.exists():
        print(f"Error: {pretty_file} not found (needed to verify claims).")
        sys.exit(1)

    size_mb = pretty_file.stat().st_size // 1024 // 1024
    print(f"Loading {pretty_file.name} ({size_mb}MB) for verification...")
    new_source = pretty_file.read_text(encoding="utf-8", errors="replace")

    annotations = json.loads(annotations_file.read_text())
    candidates = [a for a in annotations if a.get("importance", 0) >= min_importance]
    print(f"Loaded {len(annotations)} annotations ({len(candidates)} at importance >= {min_importance})")

    # Partition by claim type
    removal_candidates = [a for a in candidates if a.get("change_type") == "removal"]
    positive_candidates = [a for a in candidates if a.get("change_type") in POSITIVE_TYPES]

    print(f"\nVerifying {len(removal_candidates)} removal claims against new version...")
    print(f"Verifying {len(positive_candidates)} positive claims against new version...")

    # ── Removal verification ─────────────────────────────────────────────────
    removal_false_positives = []  # feature still in new source
    removal_confirmed = []        # feature gone from new source
    removal_unverifiable = []     # no useful search terms

    for ann in removal_candidates:
        term = primary_evidence_term(ann)
        if not term:
            removal_unverifiable.append(ann)
            continue
        if term in new_source:
            removal_false_positives.append((ann, term))
        else:
            removal_confirmed.append((ann, term))

    # ── Positive claim verification ──────────────────────────────────────────
    positive_unverified = []   # evidence term NOT found in new source
    positive_verified = []     # evidence term IS found in new source
    positive_unverifiable = [] # no useful search terms

    for ann in positive_candidates:
        term = primary_evidence_term(ann)
        if not term:
            positive_unverifiable.append(ann)
            continue
        if term in new_source:
            positive_verified.append((ann, term))
        else:
            positive_unverified.append((ann, term))

    # ── Report ────────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"REMOVAL CLAIMS ({len(removal_candidates)} total)")
    print(f"{'='*60}")
    print(f"  False positives (feature still in source): {len(removal_false_positives)}")
    print(f"  Confirmed removals (not found in source):  {len(removal_confirmed)}")
    print(f"  Unverifiable (no search terms):            {len(removal_unverifiable)}")

    if removal_false_positives:
        print("\n  FALSE POSITIVE REMOVALS:")
        for ann, term in removal_false_positives:
            print(f"    [{ann['importance']}] {ann['name']}: {ann.get('summary','')[:70]}")
            print(f"      Found '{term}' in {version} source → still present")

    if removal_confirmed:
        print("\n  CONFIRMED REMOVALS:")
        for ann, term in removal_confirmed:
            print(f"    [{ann['importance']}] {ann['name']}: {ann.get('summary','')[:70]}")
            print(f"      '{term}' not in source ✓")

    print(f"\n{'='*60}")
    print(f"POSITIVE CLAIMS ({len(positive_candidates)} total)")
    print(f"{'='*60}")
    print(f"  Evidence confirmed in source:   {len(positive_verified)}")
    print(f"  Evidence NOT found (suspicious): {len(positive_unverified)}")
    print(f"  Unverifiable (no search terms): {len(positive_unverifiable)}")

    if positive_unverified:
        print("\n  SUSPICIOUS POSITIVE CLAIMS (evidence term not in new source):")
        for ann, term in positive_unverified:
            ct = ann.get("change_type", "?")
            print(f"    [{ann['importance']}][{ct}] {ann['name']}: {ann.get('summary','')[:70]}")
            print(f"      Searched for: '{term}' — not found")

    # ── Annotate and write updated JSON ──────────────────────────────────────
    removal_fp_names = {(a.get("name"), a.get("_batch_id")) for a, _ in removal_false_positives}
    positive_unv_names = {(a.get("name"), a.get("_batch_id")) for a, _ in positive_unverified}
    positive_v_names = {(a.get("name"), a.get("_batch_id")) for a, _ in positive_verified}

    updated = []
    for ann in annotations:
        key = (ann.get("name"), ann.get("_batch_id"))
        ann_copy = dict(ann)

        if ann.get("change_type") == "removal":
            if key in removal_fp_names:
                ann_copy["change_type"] = "refactor"
                ann_copy["_removal_verified"] = False
                # Find the matched term for the note
                term = next((t for a, t in removal_false_positives
                             if (a.get("name"), a.get("_batch_id")) == key), "?")
                ann_copy["_removal_note"] = f"Feature still present: '{term}' found in {version}"
            elif ann.get("importance", 0) >= min_importance:
                ann_copy["_removal_verified"] = True

        if ann.get("change_type") in POSITIVE_TYPES and ann.get("importance", 0) >= min_importance:
            if key in positive_unv_names:
                ann_copy["_evidence_verified"] = False
                term = next((t for a, t in positive_unverified
                             if (a.get("name"), a.get("_batch_id")) == key), "?")
                ann_copy["_evidence_note"] = f"Primary term '{term}' not found in {version} source"
            elif key in positive_v_names:
                ann_copy["_evidence_verified"] = True

        updated.append(ann_copy)

    # Write
    out_path = annotations_file.with_name(f"annotations-{version}-verified.json")
    out_path.write_text(json.dumps(updated, indent=2))

    fp_count = len(removal_false_positives)
    unv_count = len(positive_unverified)
    print(f"\nSummary: {fp_count} removals downgraded, {unv_count} positive claims flagged as unverified")
    print(f"Verified annotations written to {out_path}")
    return updated


if __name__ == "__main__":
    version = sys.argv[1] if len(sys.argv) > 1 else "v2.1.48"
    min_imp = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    verify_claims(version, min_imp)
