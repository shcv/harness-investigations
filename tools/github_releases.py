"""GitHub release and tag discovery for GitHub-based projects (e.g. codex).

Mixed into ClaudeCodeSync: these methods share its caches, project config,
and directories, so they stay methods rather than free functions.
"""

import json
import os
import re
import sys
import time
from pathlib import Path
from subprocess import run
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import quote

import requests
from packaging import version

from colors import print_error, print_info, print_warning


class GitHubReleaseMixin:
    # A stable numeric tag without a GitHub Release may be a staged release,
    # rather than noise.  Keep only tags whose snapshot is substantial enough
    # to justify a changelog when there is no published release metadata.
    _INTERMEDIATE_TAG_MIN_FILES = 5
    _INTERMEDIATE_TAG_MIN_LINES = 100

    def _get_github_release(self, version_str: str) -> Optional[Dict[str, Any]]:
        """Return release metadata only for the requested tag.

        Version discovery starts with local Git tags.  The release API is used
        only for one uncatalogued tag at a time, and the result is reused as
        optional published notes for a newly generated changelog.
        """
        if not self.project.release_notes_repo:
            return None

        tag_name = f"{self.project.release_notes_tag_prefix or ''}{version_str}"
        if tag_name in self._github_release_cache:
            return self._github_release_cache[tag_name]

        cache_path = self.archive_dir / '.github-release-cache.json'
        try:
            cache = json.loads(cache_path.read_text())
        except (OSError, ValueError):
            cache = {}
        cached = cache.get(tag_name)
        if isinstance(cached, dict) and time.time() - cached.get('checked_at', 0) < 3600:
            release = cached.get('release')
            self._github_release_cache[tag_name] = release
            return release

        api_url = (
            f"https://api.github.com/repos/{self.project.release_notes_repo}"
            f"/releases/tags/{quote(tag_name, safe='')}"
        )
        headers = {"Accept": "application/vnd.github+json"}
        github_token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        if github_token:
            headers["Authorization"] = f"Bearer {github_token}"

        try:
            response = requests.get(api_url, headers=headers, timeout=30)
            if response.status_code == 404:
                # A source tag does not necessarily have a published release.
                release = None
            else:
                response.raise_for_status()
                release = response.json()
                if not isinstance(release, dict):
                    raise ValueError("GitHub release response was not an object")
                if release.get('draft') or release.get('prerelease'):
                    release = None
        except requests.RequestException as exc:
            # Official notes are enrichment; a transient API failure should
            # not prevent a diff-backed changelog from being generated.
            print_warning(
                f"Failed to fetch optional release notes for {tag_name}: {exc}"
            )
            self._github_release_lookup_failures.add(tag_name)
            release = None
        except (TypeError, ValueError) as exc:
            print_warning(
                f"Invalid optional release metadata for {tag_name}: {exc}"
            )
            self._github_release_lookup_failures.add(tag_name)
            release = None

        self._github_release_cache[tag_name] = release
        if tag_name not in self._github_release_lookup_failures:
            cache[tag_name] = {'checked_at': time.time(), 'release': release}
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = cache_path.with_suffix('.tmp')
            temporary.write_text(json.dumps(cache) + '\n')
            temporary.replace(cache_path)
        return release

    def _git_tag_change_size(
        self, tag_name: str, previous_tag_name: Optional[str]
    ) -> Optional[Tuple[int, int]]:
        """Return ``(changed_files, changed_lines)`` between two tags.

        ``None`` means that there is no safe baseline or that Git could not
        calculate the comparison.  The tags are peeled so annotated tags and
        lightweight tags behave identically.
        """
        if not previous_tag_name:
            return None

        result = run(
            [
                "git",
                "-C",
                str(self.source_dir),
                "diff",
                "--shortstat",
                f"{previous_tag_name}^{{}}",
                f"{tag_name}^{{}}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None

        summary = result.stdout.strip()
        files_match = re.search(r"(\d+)\s+files? changed", summary)
        if not files_match:
            return (0, 0)

        insertions_match = re.search(r"(\d+)\s+insertions?\(\+\)", summary)
        deletions_match = re.search(r"(\d+)\s+deletions?\(-\)", summary)
        insertions = int(insertions_match.group(1)) if insertions_match else 0
        deletions = int(deletions_match.group(1)) if deletions_match else 0
        return int(files_match.group(1)), insertions + deletions

    def _is_significant_intermediate_tag(
        self, tag_name: str, previous_tag_name: Optional[str]
    ) -> bool:
        """Return whether an unpublished stable tag merits a changelog."""
        change_size = self._git_tag_change_size(tag_name, previous_tag_name)
        if change_size is None:
            return False

        changed_files, changed_lines = change_size
        significant = (
            changed_files >= self._INTERMEDIATE_TAG_MIN_FILES
            or changed_lines >= self._INTERMEDIATE_TAG_MIN_LINES
        )
        if not significant:
            print_info(
                f"Tag {tag_name} requires a published release: "
                f"only {changed_files} files and {changed_lines} changed lines"
            )
        return significant

    def _has_local_git_tag(self, tag_name: str) -> bool:
        """Return True when a tag exists locally."""
        result = run(
            [
                "git",
                "-C",
                str(self.source_dir),
                "rev-parse",
                "--verify",
                "--quiet",
                f"refs/tags/{tag_name}^{{}}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0

    def _ensure_local_git_tag(self, tag_name: str) -> None:
        """Fetch a missing tag directly from origin and verify it exists locally."""
        if self._has_local_git_tag(tag_name):
            return

        print_info(f"Fetching missing tag {tag_name}...")
        result = run(
            [
                "git",
                "-C",
                str(self.source_dir),
                "fetch",
                "origin",
                f"refs/tags/{tag_name}:refs/tags/{tag_name}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0 or not self._has_local_git_tag(tag_name):
            stderr = result.stderr.strip() or result.stdout.strip() or "unknown git fetch error"
            raise RuntimeError(
                f"required tag {tag_name} is unavailable locally after fetch: {stderr}"
            )

    def _write_official_release_notes(self, version_str: str) -> Optional[Path]:
        """Persist the published GitHub release notes for the changelog prompt."""
        if not self.project.release_notes_repo:
            return None

        release = self._get_github_release(version_str)
        if not release:
            release_tag_name = (
                f"{self.project.release_notes_tag_prefix or ''}{version_str}"
            )
            if (
                self.project.is_github_based
                and release_tag_name not in self._github_release_lookup_failures
            ):
                self._github_unreleased_versions.add(version_str)
                print_info(
                    f"No published GitHub release found for v{version_str}; "
                    "tracking the significant tag as an unreleased snapshot"
                )
            elif release_tag_name in self._github_release_lookup_failures:
                print_warning(
                    f"No GitHub release metadata found for v{version_str}; skipping official release-note input"
                )
            else:
                print_info(
                    f"No published GitHub release found for v{version_str}; "
                    "skipping official release-note input"
                )
            return None

        release_notes_path = self.changes_dir / f"release-notes-v{version_str}.md"
        title = release.get("name") or release.get("tag_name") or version_str
        body = (release.get("body") or "").rstrip()
        html_url = release.get("html_url") or ""
        published_at = release.get("published_at") or "unknown"
        tag_name = release.get("tag_name") or (
            f"{self.project.release_notes_tag_prefix or ''}{version_str}"
        )

        lines = [
            f"# Official release notes for {title}",
            "",
            f"- repository: `{self.project.release_notes_repo}`",
            f"- tag: `{tag_name}`",
            f"- published_at: `{published_at}`",
        ]

        if html_url:
            lines.append(f"- url: {html_url}")

        lines.extend(["", "## Published Notes", ""])
        if body:
            lines.append(body)
        else:
            lines.append("_No official release-note body was published for this release._")

        release_notes_path.parent.mkdir(parents=True, exist_ok=True)
        release_notes_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return release_notes_path

    def get_github_releases(self) -> List[str]:
        """Get stable versions from the synchronized repository's Git tags."""
        print_info(f"Reading stable tags from {self.project.github_repo}...")

        if not (self.source_dir / ".git").exists():
            print_error(
                f"GitHub source repository is not synchronized: {self.source_dir}"
            )
            sys.exit(1)

        tag_prefix = self.project.github_tag_prefix or ""
        result = run(
            [
                "git",
                "-C",
                str(self.source_dir),
                "for-each-ref",
                "--format=%(refname:strip=2)",
                f"refs/tags/{tag_prefix}*",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            message = (
                result.stderr.strip()
                or result.stdout.strip()
                or "unknown git tag error"
            )
            print_error(f"Failed to list Git tags: {message}")
            sys.exit(1)

        versions: Set[str] = set()
        known_versions: Set[str] = set()
        known_release_note_versions: Set[str] = set()
        for directory, pattern in (
            (self.changelog_dir, "changelog-v*.md"),
            (self.changes_dir, "release-notes-v*.md"),
        ):
            for artifact in directory.glob(pattern):
                match = re.fullmatch(r"(?:changelog|release-notes)-v([0-9.]+)\.md", artifact.name)
                if match:
                    known_versions.add(match.group(1))
                    if artifact.name.startswith("release-notes-"):
                        known_release_note_versions.add(match.group(1))

        candidate_tags: List[Tuple[str, str]] = []
        for tag_name in result.stdout.splitlines():
            if not tag_name.startswith(tag_prefix):
                continue
            version_str = tag_name[len(tag_prefix):]
            # Ignore malformed/internal tags and prereleases.  The old
            # release-list path used GitHub's prerelease flag; the equivalent
            # local-tag check is packaging.version's prerelease property.
            if not re.fullmatch(r"\d+(?:\.\d+)+", version_str):
                continue
            try:
                parsed_version = version.parse(version_str)
            except version.InvalidVersion:
                continue
            if parsed_version.is_prerelease or parsed_version.is_devrelease:
                continue

            candidate_tags.append((version_str, tag_name))

        candidate_tags.sort(key=lambda item: version.parse(item[0]))
        for index, (version_str, tag_name) in enumerate(candidate_tags):
            if self._is_before_since(version_str):
                continue

            if version_str in known_versions:
                versions.add(version_str)
                # Older generated changelogs may predate release-note
                # enrichment.  Treat those as candidates if a later --redo
                # needs to establish whether the tag was unpublished.
                if version_str not in known_release_note_versions:
                    self._github_intermediate_candidates.add(version_str)
                continue

            previous_tag_name = (
                candidate_tags[index - 1][1] if index > 0 else None
            )
            if self._is_significant_intermediate_tag(tag_name, previous_tag_name):
                versions.add(version_str)
                self._github_intermediate_candidates.add(version_str)
            else:
                # Size limits apply only to unpublished tags. A one-line fix
                # with a published release must still be archived. Cache 404s
                # for an hour so the five-minute scheduler does not hammer API.
                release = self._get_github_release(version_str)
                if release or tag_name in self._github_release_lookup_failures:
                    versions.add(version_str)

        sorted_versions = sorted(
            versions, key=version.parse, reverse=self.new_first
        )
        self.stats.total_versions = len(sorted_versions)

        if self.since:
            print_info(f"Filtered to {len(sorted_versions)} versions since {self.since}")

        return sorted_versions

    def _is_unreleased_github_version(self, version_str: str) -> bool:
        """Return whether this run classified the tag as an unreleased snapshot."""
        return (
            self.project.is_github_based
            and version_str in self._github_unreleased_versions
        )

    def _mark_unreleased_github_changelog(
        self, changelog_file: Path, version_str: str
    ) -> None:
        """Add a deterministic status note for a tag without a published release."""
        if not self._is_unreleased_github_version(version_str):
            return

        content = changelog_file.read_text(encoding="utf-8")
        marker = (
            f"`{self.project.github_tag_prefix or ''}{version_str}` is present in Git, "
            "but no published GitHub Release was found at sync time."
        )
        if marker in content:
            return

        lines = content.splitlines()
        h1_index = next(
            (index for index, line in enumerate(lines) if line.startswith("# ")),
            None,
        )
        if h1_index is None:
            return

        status_lines = [
            "",
            "## Release Status",
            "",
            f"> **Not yet released:** {marker} This may be an intermediate development snapshot or a release prepared ahead of publication.",
            "",
        ]
        lines[h1_index + 1 : h1_index + 1] = status_lines
        changelog_file.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
