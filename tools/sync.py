#!/usr/bin/env python3
"""
Claude Code Archive Sync Tool (Python Implementation)

This script automates the process of downloading, organizing, and optionally
processing all available versions of the @anthropic-ai/claude-code package
from the npm registry.

Architecture:
- Phase 1: Download missing versions from npm registry
- Phase 2: Prettify downloaded files using prettier (optional)
- Phase 3: Generate diffs between consecutive versions (optional)
- Phase 4: Generate changelogs using the configured agent provider (optional)
  * If --cleanup is enabled: immediately clean each changelog after generation
  * If --post is enabled: immediately post each changelog after cleanup
- Phase 5: Filter detailed changes for changelog input (optional)
- Phase 6: Clean up changelog headers (optional, skipped if --changelog is enabled)
- Phase 7: Post changelogs to Discord (optional, skipped if --changelog is enabled)

Note: When --changelog is used with --cleanup and/or --post, each changelog is
processed completely (generate → clean → post) before moving to the next one.
This reduces the risk of losing work if the process is interrupted.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import sys
import tarfile
import time
from dataclasses import dataclass
from pathlib import Path
from subprocess import run
from typing import Any, Dict, List, Set, Optional, Tuple
import requests
from packaging import version

import bun_extract
from astdiff_filter import filter_astdiff, looks_like_astdiff
from github_releases import GitHubReleaseMixin
from changelog_prompt import (
    PRIMARY_DIFF_LABELS,
    ChangelogInputs,
    build_prompt as build_changelog_prompt,
    format_trailer,
    retry_addendum,
)
from annotation_summary import (
    POSITIVE_CLAIM_TYPES,
    format_annotation_summary,
    primary_evidence_term,
)
from agent_runner import (
    AgentRunRequest,
    AgentRunnerError,
    SUPPORTED_AGENT_PROVIDERS,
    DEFAULT_AGENT_PROVIDER,
    load_project_env,
    default_model_for,
    make_agent_runner,
)

# Share local configuration with the standalone annotation/prose commands.
load_project_env()


def _env_bool(name: str, default: bool) -> bool:
    """Parse a boolean CHANGELOG_* env var, defaulting when unset."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")

class ProjectConfig:
    """Configuration for a specific project/package"""

    def __init__(
        self,
        name: str,
        npm_package: Optional[str] = None,
        github_repo: Optional[str] = None,
        github_tag_prefix: Optional[str] = None,
        release_notes_repo: Optional[str] = None,
        release_notes_tag_prefix: Optional[str] = None,
        use_astdiff: bool = False,
        changelog_prompt: Optional[str] = None,
        changes_prompt: Optional[str] = None,
        webhook_env_var: Optional[str] = None,
        source_subdir: Optional[str] = None,
        extract_files: Optional[List[Tuple[str, str]]] = None,
        min_version: Optional[str] = None,
    ):
        self.name = name
        self.npm_package = npm_package
        self.github_repo = github_repo  # e.g., "openai/codex"
        self.github_tag_prefix = github_tag_prefix  # e.g., "rust-v" for rust-v0.46.0
        # Release notes may live on GitHub even when artifacts come from npm.
        self.release_notes_repo = release_notes_repo or github_repo
        self.release_notes_tag_prefix = (
            release_notes_tag_prefix
            if release_notes_tag_prefix is not None
            else github_tag_prefix
        )
        self.use_astdiff = use_astdiff
        self.changelog_prompt = changelog_prompt
        self.changes_prompt = changes_prompt
        self.webhook_env_var = webhook_env_var
        self.source_subdir = source_subdir  # Subdirectory containing main source (e.g., "codex-rs")
        # Floor for backfilling; acts as an implicit --since when none is given.
        self.min_version = min_version
        # Files to extract: list of (archive_path, output_prefix) tuples
        # e.g., [("cli.js", "cli"), ("sdk.mjs", "sdk")] -> cli-v1.0.0.js, sdk-v1.0.0.mjs
        # If None, defaults to [("cli.js", "cli"), ("cli.mjs", "cli")] for backwards compat
        self.extract_files = extract_files
        # Primary file prefix for diff/changelog generation (first one if not specified)
        # Validate that at least one source is specified
        if not npm_package and not github_repo:
            raise ValueError(f"Project {name} must specify either npm_package or github_repo")

        self._primary_prefix = None
        if extract_files:
            self._primary_prefix = extract_files[0][1]  # Use first file's prefix as primary

    @property
    def primary_file_prefix(self) -> str:
        """Get the primary file prefix for diffs/changelogs"""
        return self._primary_prefix or "cli"

    @property
    def is_npm_based(self) -> bool:
        """Check if this project uses npm as its source"""
        return self.npm_package is not None

    @property
    def is_github_based(self) -> bool:
        """Check if this project uses GitHub releases as its source"""
        return self.github_repo is not None


# Predefined project configurations
PROJECTS = {
    "claude-code": ProjectConfig(
        name="claude-code",
        npm_package="@anthropic-ai/claude-code",
        release_notes_repo="anthropics/claude-code",
        release_notes_tag_prefix="v",
        use_astdiff=True,  # Use astdiff for minified Claude Code
        webhook_env_var="DISCORD_WEBHOOK_URL",  # Uses existing env var
    ),
    "claude-agent-sdk": ProjectConfig(
        name="claude-agent-sdk",
        npm_package="@anthropic-ai/claude-agent-sdk",
        use_astdiff=True,  # Use astdiff for bundled SDK code
        webhook_env_var="DISCORD_WEBHOOK_URL_AGENT_SDK",
        # Extract both CLI and SDK module files
        extract_files=[
            ("cli.js", "cli"),      # cli-v0.2.23.js
            ("sdk.mjs", "sdk"),     # sdk-v0.2.23.mjs
        ],
    ),
    "codex": ProjectConfig(
        name="codex",
        github_repo="openai/codex",
        github_tag_prefix="rust-v",  # Tags are like rust-v0.46.0
        source_subdir="codex-rs",  # Main Rust source is in codex-rs/
        use_astdiff=False,  # Regular diff for Rust source
        webhook_env_var="DISCORD_WEBHOOK_URL_CODEX",  # Separate webhook for Codex
        min_version="0.116.0",  # Don't backfill older versions
    ),
}


from colors import Colors, colored, print_header, print_success, print_warning, print_error, print_info

# Common regex patterns
RE_DIFF_VERSION = re.compile(r"v([0-9.]+)(?:-\d+)?\.diff$")
RE_FILE_PREFIX_VERSION = re.compile(r"([a-z]+)-v([0-9.]+)\.[a-z]+$")


@dataclass
class SyncStats:
    """Track sync operation statistics"""
    total_versions: int = 0
    downloaded_count: int = 0
    prettified_count: int = 0
    diff_generated_count: int = 0
    changelog_generated_count: int = 0
    download_failures: int = 0
    prettier_failures: int = 0
    diff_generation_failures: int = 0
    changelog_generation_failures: int = 0
    changes_generated_count: int = 0
    changes_generation_failures: int = 0
    changelogs_cleaned_count: int = 0
    changelog_cleanup_failures: int = 0
    changelogs_posted_count: int = 0
    changelog_post_failures: int = 0
    changelogs_committed_count: int = 0
    changelog_commit_failures: int = 0


class ClaudeCodeSync(GitHubReleaseMixin):
    """Main sync tool implementation"""

    # Default changelog system prompt
    DEFAULT_CHANGELOG_PROMPT = """Give me a changelog based on the diff provided in the prompt. Return only the changelog contents. Be detailed and clear in your explanations. Investigate the newer file as needed. Focus on and prioritize user-facing (interactive and cli argument) features. Lead with new user-facing features ordered by impact, then features still in development, then a compact one-line-per-item list of other changes. If official release notes are provided, make sure every published item appears. If there is a new command, argument, flag, or other user-facing feature, give explanations and examples for how a user could use it. Note that this is an interactive CLI application, not a library; user's won't interact with the code directly, so present usage from the perspective of an interaction or command-line arguments, not function calls. If you want to explain the code, reproduce the relevant snippet with semantic names."""

    def __init__(
        self,
        base_dir: Path,
        project: ProjectConfig,
        prettier: bool = False,
        diff: bool = False,
        changelog: bool = False,
        changes: bool = False,
        cleanup: bool = False,
        post: bool = False,
        git_commit: bool = False,
        git_remote: Optional[str] = None,
        git_https_fallback: bool = False,
        latest: bool = False,
        since: Optional[str] = None,
        new_first: bool = False,
        redo: Optional[str] = None,
        dry_run: bool = False,
        annotate: bool = False,
        astdiff_threads: Optional[int] = None,
        agent_provider: str = DEFAULT_AGENT_PROVIDER,
        changelog_model: Optional[str] = None,
        annotation_model: Optional[str] = None,
        codex_reasoning_effort: Optional[str] = None,
        codex_annotation_reasoning_effort: Optional[str] = None,
        codex_executable: str = "codex",
        qwen_base_url: Optional[str] = None,
        astdiff_executable: Optional[str] = None,
        allow_degraded_diff: bool = False,
    ):
        self.base_dir = base_dir
        self.project = project
        self.prettier = prettier
        self.diff = diff
        self.changelog = changelog
        self.changes = changes
        self.do_cleanup = cleanup
        self.post = post
        self.git_commit = git_commit
        self.git_remote = git_remote
        self.git_https_fallback = git_https_fallback
        self.latest = latest
        # Fall back to the project's min_version floor if no explicit --since.
        # An explicit --since (even one older than the floor) wins, so ad-hoc
        # work can still reach below the floor without editing config.
        self.since = since if since is not None else project.min_version
        self.new_first = new_first
        self.redo = redo
        self.dry_run = dry_run
        self.annotate = annotate
        self.astdiff_threads = astdiff_threads
        self.astdiff_executable = astdiff_executable or os.getenv("CHANGELOG_ASTDIFF_BIN") or "astdiff"
        self.allow_degraded_diff = allow_degraded_diff
        self.agent_provider = agent_provider.lower()
        self.changelog_model = changelog_model or default_model_for(
            self.agent_provider, "changelog"
        )
        self.annotation_model = annotation_model or default_model_for(
            self.agent_provider, "annotation"
        )
        self.codex_reasoning_effort = codex_reasoning_effort
        self.codex_annotation_reasoning_effort = codex_annotation_reasoning_effort
        self.codex_executable = codex_executable
        self.qwen_base_url = qwen_base_url

        # Directory structure - now project-specific
        self.archive_dir = base_dir / "archive" / project.name

        # Source directory depends on project type
        if project.is_github_based:
            # GitHub projects: just a git clone
            self.source_dir = self.archive_dir / "source"
            self.original_dir = None  # Not used for GitHub projects
            self.pretty_dir = None  # Not used for GitHub projects
        else:
            # npm projects: original + prettified
            self.source_dir = None  # Not used for npm projects
            self.original_dir = self.archive_dir / "original"
            self.pretty_dir = self.archive_dir / "pretty"

        self.diff_dir = self.archive_dir / "diff"
        self.changelog_dir = self.archive_dir / "changelog"
        self.changes_dir = self.archive_dir / "changes"
        self.temp_dir = base_dir / f".sync-temp-{project.name}"
        # Dedicated working directory for SDK agent runs. claude buckets
        # sessions by cwd, so running agents here keeps their JSONL sessions out
        # of the user's personal session bucket for this repo (cwd=base_dir).
        # Input/output files are passed to the agent as absolute paths, so the
        # agent never needs to resolve anything relative to this dir.
        self.agent_cwd = base_dir / ".agent-cwd"

        self.stats = SyncStats()
        self._cleanup_module = None
        self._changelog_agent = None
        self._annotation_agent = None
        self._tool_version = None
        # Version discovery starts with the local Git tag set after the
        # repository is synchronized.  Release metadata is fetched lazily only
        # when a changelog needs optional published-note enrichment.
        self._github_release_cache: Dict[str, Optional[Dict[str, Any]]] = {}
        self._github_release_lookup_failures: Set[str] = set()
        self._github_intermediate_candidates: Set[str] = set()
        self._github_unreleased_versions: Set[str] = set()
        self._blocked_diff_versions: Dict[str, List[Path]] = {}
        self._notify_send_path = shutil.which("notify-send")

    def setup_directories(self):
        """Create required directories"""
        directories = [self.archive_dir]

        # Add source directories based on project type
        if self.project.is_github_based:
            # GitHub: just source directory (will be git repo)
            directories.append(self.source_dir)
        else:
            # npm: original and pretty directories
            directories.append(self.original_dir)
            if self.prettier:
                directories.append(self.pretty_dir)

        if self.diff:
            directories.append(self.diff_dir)

        if self.changelog:
            directories.append(self.changelog_dir)

        if self.changes:
            directories.append(self.changes_dir)

        for directory in directories:
            if directory:  # Skip None directories
                directory.mkdir(parents=True, exist_ok=True)

        # Create temp directory
        self.temp_dir.mkdir(exist_ok=True)

    def check_dependencies(self):
        """Check for required system dependencies"""
        # Check prettier if needed
        if self.prettier and self.project.is_npm_based:
            print_info("Checking prettier command...")
            result = run(["which", "prettier"], capture_output=True)
            if result.returncode != 0:
                print_error("'prettier' command not found in PATH")
                print_error(
                    "Please ensure the prettier tool is installed and available"
                )
                sys.exit(1)

    def _is_before_since(self, version_str: str) -> bool:
        """Return True if version_str is before the --since cutoff."""
        if not self.since:
            return False
        try:
            return version.parse(version_str.lstrip("v")) < version.parse(self.since.lstrip("v"))
        except Exception:
            return False

    def _notify_failure(self, title: str, message: str) -> None:
        """Best-effort desktop notification for hard failures."""
        # The scheduled wrapper owns notification after its persistent grace
        # period. Direct sync.py invocations keep immediate notifications.
        if _env_bool("CHANGELOG_DEFER_FAILURE_NOTIFICATIONS", False):
            return
        if not self._notify_send_path:
            return

        body = " ".join(message.strip().split())
        if len(body) > 500:
            body = body[:497] + "..."

        try:
            run(
                [
                    self._notify_send_path,
                    "--urgency=critical",
                    f"{self.project.name}: {title}",
                    body,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception:
            pass

    def get_npm_versions(self) -> List[str]:
        """Get all available versions from npm registry, sorted oldest first by default"""
        print_info(f"Fetching all available versions of {self.project.npm_package}...")

        try:
            result = run(
                ["npm", "view", self.project.npm_package, "versions", "--json"],
                capture_output=True,
                text=True,
                check=True,
            )

            versions = json.loads(result.stdout)
            if isinstance(versions, str):
                versions = [versions]  # Handle single version case

            # Sort versions (oldest first by default, newest first if --new-first)
            sorted_versions = sorted(
                versions, key=version.parse, reverse=self.new_first
            )
            self.stats.total_versions = len(sorted_versions)

            if self.since:
                sorted_versions = [v for v in sorted_versions if not self._is_before_since(v)]
                print_info(f"Filtered to {len(sorted_versions)} versions since {self.since}")

            return sorted_versions

        except Exception as e:
            print_error(f"Failed to fetch versions from npm: {e}")
            sys.exit(1)

    def get_existing_originals(self) -> Set[str]:
        """Get set of versions that already exist in original directory.

        For projects with multiple extract_files, a version is only considered
        'existing' if ALL required files are present.
        """
        # Determine which file prefixes we need
        extract_files = self.project.extract_files
        if extract_files is None:
            # Default: just need cli file
            required_prefixes = ["cli"]
        else:
            required_prefixes = [prefix for _, prefix in extract_files]

        # Count how many files exist for each version
        version_files: dict = {}  # version -> set of prefixes found

        for file_path in self.original_dir.glob("*-v*.*"):
            # Extract prefix and version from filename: cli-v1.0.63.js -> ("cli", "1.0.63")
            match = RE_FILE_PREFIX_VERSION.match(file_path.name)
            if match:
                prefix, ver = match.groups()
                if prefix in required_prefixes:
                    if ver not in version_files:
                        version_files[ver] = set()
                    version_files[ver].add(prefix)

        # Return versions that have ALL required files
        required_set = set(required_prefixes)
        return {ver for ver, found in version_files.items() if found >= required_set}

    def _extract_from_platform_binary(self, version_str: str) -> bytes:
        """Download the linux-x64 sibling package and extract cli.js from its Bun binary.

        The embedded JS is platform-agnostic (same bundle in every platform
        package), so we always pull linux-x64 regardless of the host. Raises on
        any failure; caller decides how to report.
        """
        platform_pkg = f"{self.project.npm_package}-linux-x64"
        print_info(f"Fetching platform binary tarball for {platform_pkg}@{version_str}...")

        url_result = run(
            ["npm", "view", f"{platform_pkg}@{version_str}", "dist.tarball"],
            capture_output=True,
            text=True,
            check=True,
        )
        tarball_url = url_result.stdout.strip()
        if not tarball_url:
            raise RuntimeError(f"no dist.tarball for {platform_pkg}@{version_str}")

        platform_tgz = self.temp_dir / f"{platform_pkg.replace('/', '__')}-{version_str}.tgz"
        print_info(f"Downloading {tarball_url} (~74 MB)...")
        response = requests.get(tarball_url, stream=True, timeout=60)
        response.raise_for_status()
        with open(platform_tgz, "wb") as fh:
            for chunk in response.iter_content(chunk_size=64 * 1024):
                fh.write(chunk)

        platform_extract_dir = self.temp_dir / f"platform-{version_str}"
        try:
            with tarfile.open(platform_tgz, "r:gz") as tar:
                # Binaries may be named "claude" (unix) or "claude.exe" (win).
                bin_member = None
                for candidate in ("package/claude", "package/claude.exe"):
                    try:
                        bin_member = tar.getmember(candidate)
                        break
                    except KeyError:
                        continue
                if bin_member is None:
                    raise RuntimeError(
                        f"no claude binary in {platform_pkg}@{version_str} tarball"
                    )
                tar.extract(bin_member, platform_extract_dir)
                binary_path = platform_extract_dir / bin_member.name

            print_info("Extracting embedded JS bundle from Bun binary...")
            project_root = Path(__file__).resolve().parents[1]
            return bun_extract.extract_cli_js(
                binary_path, project_root,
                self.original_dir / f'cli-v{version_str}.modules.json',
            )
        finally:
            platform_tgz.unlink(missing_ok=True)
            shutil.rmtree(platform_extract_dir, ignore_errors=True)

    def download_version(self, version_str: str) -> bool:
        """Download a specific version from npm. Returns True on success."""
        print(f"\n--- Downloading version {version_str} ---")

        try:
            # Get tarball URL
            print_info(f"Fetching tarball URL for version {version_str}...")
            result = run(
                ["npm", "view", f"{self.project.npm_package}@{version_str}", "dist.tarball"],
                capture_output=True,
                text=True,
                check=True,
            )

            tarball_url = result.stdout.strip()
            if not tarball_url:
                print_warning(f"Could not get tarball URL for version {version_str}")
                return False

            # Download tarball
            print_info(f"Downloading {tarball_url}...")
            response = requests.get(tarball_url, stream=True, timeout=60)
            response.raise_for_status()

            tgz_file = self.temp_dir / f"{self.project.name}-{version_str}.tgz"
            with open(tgz_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Determine files to extract
            extract_files = self.project.extract_files
            if extract_files is None:
                # Default behavior: extract cli.js or cli.mjs
                extract_files = [("cli.js", "cli"), ("cli.mjs", "cli")]

            # Extract and save files
            print_info("Extracting files...")
            files_extracted = 0

            with tarfile.open(tgz_file, "r:gz") as tar:
                for archive_name, output_prefix in extract_files:
                    archive_path = f"package/{archive_name}"
                    try:
                        member = tar.getmember(archive_path)
                        tar.extract(member, self.temp_dir)
                        extracted_file = self.temp_dir / archive_path

                        # Determine output extension from archive name
                        ext = Path(archive_name).suffix or ".js"
                        original_file = self.original_dir / f"{output_prefix}-v{version_str}{ext}"
                        print_info(f"Saving: {original_file.name}")
                        shutil.copy2(extracted_file, original_file)
                        files_extracted += 1
                    except KeyError:
                        # File not in archive, skip (only warn if no files extracted at end)
                        continue

            # v2.1.113+ of claude-code ships the main npm package as a thin
            # wrapper and puts the real CLI inside a Bun-compiled binary in a
            # sibling platform package. When we see an empty extraction, try
            # pulling the linux-x64 sibling and extracting the embedded JS.
            if (
                files_extracted == 0
                and self.project.npm_package == "@anthropic-ai/claude-code"
            ):
                try:
                    js_bytes = self._extract_from_platform_binary(version_str)
                    original_file = self.original_dir / f"cli-v{version_str}.js"
                    print_info(f"Saving: {original_file.name}")
                    original_file.write_bytes(js_bytes)
                    files_extracted = 1
                except Exception as platform_err:
                    print_warning(
                        f"Platform-binary fallback failed for {version_str}: {platform_err}"
                    )

            if files_extracted == 0:
                print_warning(f"No files found in tarball for version {version_str}")
                tgz_file.unlink(missing_ok=True)
                shutil.rmtree(self.temp_dir / "package", ignore_errors=True)
                return False

            # Clean up temp files
            tgz_file.unlink(missing_ok=True)
            shutil.rmtree(self.temp_dir / "package", ignore_errors=True)

            print_success(f"Downloaded version {version_str} ({files_extracted} file(s))")
            return True

        except Exception as e:
            print_warning(f"Failed to download version {version_str}: {e}")
            return False

    def sync_github_repo(self):
        """Sync the GitHub repository and its tags."""
        print_header("Phase 1: Syncing GitHub Repository")

        repo_url = f"https://github.com/{self.project.github_repo}.git"

        # Check if repo already cloned
        if not (self.source_dir / ".git").exists():
            print_info(f"Cloning {self.project.github_repo}...")
            result = run(
                ["git", "clone", repo_url, str(self.source_dir)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print_error(f"Failed to clone repository: {result.stderr}")
                sys.exit(1)
            print_success(f"Cloned {self.project.github_repo}")
        else:
            print_info("Repository already cloned, fetching updates...")
            result = run(
                [
                    "git",
                    "-C",
                    str(self.source_dir),
                    "fetch",
                    "origin",
                    "--force",
                    "+refs/tags/*:refs/tags/*",
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                message = result.stderr.strip() or result.stdout.strip() or "unknown git fetch error"
                print_error(f"Failed to fetch tags: {message}")
                self._notify_failure("tag fetch failed", message)
                sys.exit(1)
            print_success("Fetched latest tags")

        print_info("Repository synced, ready for version discovery")

    def checkout_latest_github(self, all_versions: List[str]):
        """Checkout the selected latest Git tag for --latest runs."""
        if not all_versions:
            print_warning("No stable Git tags available for --latest")
            return

        latest_version = all_versions[-1] if not self.new_first else all_versions[0]
        print_info(f"Checking out latest version: {latest_version}")
        tag_name = f"{self.project.github_tag_prefix or ''}{latest_version}"
        result = run(
            ["git", "-C", str(self.source_dir), "checkout", tag_name],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print_error(f"Failed to checkout {tag_name}: {result.stderr}")
        else:
            print_success(f"Checked out {tag_name}")

    def phase_1_download_originals(self, all_versions: List[str]):
        """Phase 1: Download missing original files"""
        print_header("Phase 1: Downloading Original Files")

        if self.latest:
            # For --latest, only process the most recent version
            if not all_versions:
                print_warning("No versions available to download.")
                return

            latest_version = all_versions[-1] if not self.new_first else all_versions[0]  # Get appropriate latest version
            print_info(f"Processing latest version only: {latest_version}")

            # Also download the previous version for diff generation
            if self.diff and len(all_versions) > 1:
                # Get the second-latest version (versions are sorted oldest first)
                previous_version = all_versions[-2] if not self.new_first else all_versions[1]
                versions_to_check = [latest_version, previous_version]
                print_info(
                    f"Also checking previous version for diff: {previous_version}"
                )
            else:
                versions_to_check = [latest_version]

            existing_originals = self.get_existing_originals()
            missing_versions = [
                v for v in versions_to_check if v not in existing_originals
            ]
        else:
            # Normal behavior: check all versions
            print_info("Checking for missing original files...")
            existing_originals = self.get_existing_originals()
            missing_versions = [v for v in all_versions if v not in existing_originals]

        if not missing_versions:
            print_info("All required original files are present.")
            return

        print_info(f"Missing original versions: {', '.join(missing_versions)}")
        print_info("Downloading missing versions...")

        for version_str in missing_versions:
            if self.download_version(version_str):
                self.stats.downloaded_count += 1
            else:
                self.stats.download_failures += 1

        print_info(f"\nDownloaded {self.stats.downloaded_count} new files.")
        if self.stats.download_failures > 0:
            print_warning(f"{self.stats.download_failures} downloads failed.")

    def get_files_to_prettify(self) -> List[Path]:
        """Get list of original files that need prettification"""
        files_to_prettify = []

        # Determine file patterns based on extract_files config
        extract_files = self.project.extract_files
        if extract_files is None:
            # Legacy mode: use old naming convention (pretty-v*.js without prefix)
            patterns = [("cli-v*.js", r"cli-v([0-9.]+)\.js$", None)]  # None prefix = old naming
        else:
            # New mode: use prefix-based naming (pretty-{prefix}-v*.js)
            patterns = []
            for archive_name, prefix in extract_files:
                ext = Path(archive_name).suffix or ".js"
                pattern = f"{prefix}-v*{ext}"
                regex = rf"{prefix}-v([0-9.]+){re.escape(ext)}$"
                patterns.append((pattern, regex, prefix))

        for glob_pattern, regex_pattern, prefix in patterns:
            # Get all original files sorted by version
            original_files = list(self.original_dir.glob(glob_pattern))
            original_files.sort(
                key=lambda p, r=regex_pattern: version.parse(
                    re.match(r, p.name).group(1) if re.match(r, p.name) else "0"
                ),
                reverse=self.new_first,
            )

            if self.latest and original_files:
                # For --latest, only check the most recent version
                newest_files = sorted(original_files, key=lambda p: version.parse(
                    re.match(regex_pattern, p.name).group(1)), reverse=True)
                files_to_check = newest_files[:2 if self.diff else 1]
            else:
                files_to_check = original_files

            for original_file in files_to_check:
                # Extract version from filename
                match = re.match(regex_pattern, original_file.name)
                if not match:
                    continue

                version_str = match.group(1)

                # Filter by --since if specified
                if self._is_before_since(version_str):
                    continue

                # Determine pretty file name based on prefix mode
                if prefix is None:
                    # Legacy mode: pretty-v{version}.js
                    pretty_file = self.pretty_dir / f"pretty-v{version_str}.js"
                else:
                    # New mode: pretty-{prefix}-v{version}.js
                    pretty_file = self.pretty_dir / f"pretty-{prefix}-v{version_str}.js"

                # Check if pretty version already exists
                if not pretty_file.exists():
                    files_to_prettify.append(original_file)

        return files_to_prettify

    def prettify_file(self, original_file: Path) -> bool:
        """Prepare a single JavaScript analysis input. Returns True on success."""
        # Extract prefix and version from filename: cli-v1.0.63.js -> ("cli", "1.0.63")
        match = RE_FILE_PREFIX_VERSION.match(original_file.name)
        if not match:
            return False

        prefix, version_str = match.groups()

        # Determine naming mode: legacy (no extract_files) vs new (with extract_files)
        if self.project.extract_files is None:
            # Legacy mode: pretty-v{version}.js
            pretty_file = self.pretty_dir / f"pretty-v{version_str}.js"
            print(f"\n--- Preparing version {version_str} ---")
        else:
            # New mode: pretty-{prefix}-v{version}.js
            pretty_file = self.pretty_dir / f"pretty-{prefix}-v{version_str}.js"
            print(f"\n--- Preparing {prefix} version {version_str} ---")

        try:
            # Split-module Bun releases have already been parsed and normalized
            # by the pinned esbuild rebundling step. astdiff consumes syntax
            # trees, so a second whole-file parse through Prettier adds no
            # structural information and eventually exhausts Node's heap as
            # the module graph grows. Keep the established pretty/ path as a
            # hard link so downstream readers do not need a second 40+ MB copy.
            modules_file = original_file.with_suffix(".modules.json")
            if modules_file.exists():
                os.link(original_file, pretty_file)
                print_success(
                    f"Prepared esbuild analysis snapshot for version {version_str}"
                )
                self.update_claude_md(version_str)
                return True

            # Run prettier with babel parser and custom ignore-path to handle gitignored files.
            # Legacy single-bundle releases exceed Node's default ~1.8 GB heap,
            # so retain the larger heap for those inputs.
            prettier_env = {**os.environ, "NODE_OPTIONS": "--max-old-space-size=4096"}
            result = run(
                [
                    "prettier",
                    "--ignore-path",
                    ".prettierignore",
                    "--parser",
                    "babel",
                    str(original_file),
                ],
                capture_output=True,
                text=True,
                check=True,
                env=prettier_env,
            )

            # Write output to pretty file
            with open(pretty_file, "w", encoding="utf-8") as f:
                f.write(result.stdout)

            # Check if prettier succeeded (non-empty output)
            if pretty_file.stat().st_size == 0:
                print_warning(
                    f"prettier produced empty output for version {version_str}"
                )
                pretty_file.unlink(missing_ok=True)
                return False

            print_success(f"Prettified version {version_str}")

            # Update CLAUDE.md with the current version
            self.update_claude_md(version_str)

            return True

        except Exception as e:
            print_warning(f"prettier failed for version {version_str}: {e}")
            pretty_file.unlink(missing_ok=True)
            return False

    def phase_2_prettify_files(self):
        """Phase 2: Prettify files if requested"""
        if not self.prettier:
            return

        print_header("Phase 2: Preparing Analysis Inputs")
        print_info("Checking for files to prepare...")

        files_to_prettify = self.get_files_to_prettify()

        if not files_to_prettify:
            print_info("All analysis inputs are already prepared.")
            return

        order_desc = "newest first" if self.new_first else "oldest first"
        print_info(
            f"Found {len(files_to_prettify)} analysis inputs to prepare "
            f"(processing {order_desc})"
        )

        for original_file in files_to_prettify:
            if self.prettify_file(original_file):
                self.stats.prettified_count += 1
            else:
                self.stats.prettier_failures += 1

        print_info(f"\nPrepared {self.stats.prettified_count} new analysis inputs.")
        if self.stats.prettier_failures > 0:
            print_warning(
                f"{self.stats.prettier_failures} analysis input preparations failed."
            )

    def get_versions_to_diff_github(self, all_versions: List[str]) -> List[Tuple[str, str]]:
        """Get list of consecutive version pairs that need diffs generated (GitHub mode)"""
        versions_to_diff = []

        if self.latest:
            # For --latest, only diff the most recent pair
            if len(all_versions) >= 2:
                older_version = all_versions[-2] if not self.new_first else all_versions[1]
                newer_version = all_versions[-1] if not self.new_first else all_versions[0]

                diff_file = self.diff_dir / f"v{newer_version}.diff"
                if not diff_file.exists():
                    versions_to_diff.append((older_version, newer_version))
        else:
            # Create pairs of consecutive versions
            sorted_versions = sorted(all_versions, key=version.parse)
            for i in range(len(sorted_versions) - 1):
                older_version = sorted_versions[i]
                newer_version = sorted_versions[i + 1]

                # Filter by --since if specified (check newer version)
                if self._is_before_since(newer_version):
                    continue

                diff_file = self.diff_dir / f"v{newer_version}.diff"
                if not diff_file.exists():
                    versions_to_diff.append((older_version, newer_version))

            # Reverse to process newest first (when --new-first is specified)
            if self.new_first:
                versions_to_diff.reverse()

        return versions_to_diff

    def _analysis_file_for_version(self, version_str: str) -> Path:
        if self.project.extract_files is None:
            return self.pretty_dir / f"pretty-v{version_str}.js"
        prefix = self.project.primary_file_prefix
        return self.pretty_dir / f"pretty-{prefix}-v{version_str}.js"

    def _diff_input_for_version(self, version_str: str) -> Path:
        """Return the consistently normalized source used by astdiff."""
        if self.project.extract_files is None:
            original = self.original_dir / f"cli-v{version_str}.js"
            if original.with_suffix(".modules.json").exists():
                return original
        return self._analysis_file_for_version(version_str)

    def get_files_to_diff(
        self, all_versions: Optional[List[str]] = None
    ) -> List[Tuple[Path, Path]]:
        """Get list of consecutive version pairs that need diffs generated"""
        files_to_diff = []

        # Determine naming mode based on extract_files config
        if self.project.extract_files is None:
            # Legacy mode: use pretty-v*.js
            pretty_files = list(self.pretty_dir.glob("pretty-v*.js"))
            regex_pattern = r"pretty-v([0-9.]+)\.js$"
        else:
            # New mode: use pretty-{prefix}-v*.js with primary prefix
            prefix = self.project.primary_file_prefix
            pretty_files = list(self.pretty_dir.glob(f"pretty-{prefix}-v*.js"))
            regex_pattern = rf"pretty-{prefix}-v([0-9.]+)\.js$"

        available = {}
        for path in pretty_files:
            match = re.match(regex_pattern, path.name)
            if match:
                available[match.group(1)] = path

        # A split-module esbuild snapshot is itself the preferred diff input.
        # Include it even when callers intentionally run --diff without first
        # materializing the compatibility link under pretty/.
        if self.project.extract_files is None:
            for modules_path in self.original_dir.glob("cli-v*.modules.json"):
                match = re.match(r"cli-v([0-9.]+)\.modules\.json$", modules_path.name)
                if not match:
                    continue
                version_str = match.group(1)
                original = self.original_dir / f"cli-v{version_str}.js"
                if original.exists():
                    available[version_str] = original

        if all_versions is None:
            ordered_versions = sorted(available, key=version.parse)
        else:
            # Version discovery may already be filtered by --since. Include
            # existing analysis inputs so the first selected version retains
            # its immediate comparison baseline.
            ordered_versions = sorted(
                set(all_versions) | set(available), key=version.parse
            )

        version_pairs = list(zip(ordered_versions, ordered_versions[1:]))
        if self.latest:
            version_pairs = version_pairs[-1:]

        self._blocked_diff_versions = {}
        for older_version, newer_version in version_pairs:
            if self._is_before_since(newer_version):
                continue

            diff_file = self.diff_dir / f"v{newer_version}.diff"
            if diff_file.exists():
                continue

            older_file = self._diff_input_for_version(older_version)
            newer_file = self._diff_input_for_version(newer_version)
            missing = [path for path in (older_file, newer_file) if not path.exists()]
            if missing:
                self._blocked_diff_versions[newer_version] = missing
                continue
            files_to_diff.append((older_file, newer_file))

        if self.new_first:
            files_to_diff.reverse()

        return files_to_diff

    def generate_diff_github(
        self, older_version: str, newer_version: str, iteration: int = 1
    ) -> bool:
        """Generate diff between two tags using git. Returns True on success."""
        # Add iteration suffix if > 1
        if iteration > 1:
            diff_file = self.diff_dir / f"v{newer_version}-{iteration}.diff"
        else:
            diff_file = self.diff_dir / f"v{newer_version}.diff"

        print(f"\n--- Generating diff: v{older_version} -> v{newer_version} ---")

        try:
            # Use git diff between tags
            older_tag = f"{self.project.github_tag_prefix}{older_version}"
            newer_tag = f"{self.project.github_tag_prefix}{newer_version}"
            self._ensure_local_git_tag(older_tag)
            self._ensure_local_git_tag(newer_tag)

            # If source_subdir is specified, only diff that subdirectory
            path_spec = []
            if self.project.source_subdir:
                path_spec = ["--", self.project.source_subdir]

            result = run(
                ["git", "-C", str(self.source_dir), "diff", older_tag, newer_tag] + path_spec,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                stderr = result.stderr.strip() or result.stdout.strip() or "git diff returned a non-zero exit status"
                raise RuntimeError(
                    f"git diff failed for {older_tag}..{newer_tag}: {stderr}"
                )

            # Write diff output (even if empty - that means no changes)
            with open(diff_file, "w", encoding="utf-8") as f:
                if result.stdout:
                    f.write(result.stdout)
                else:
                    f.write(
                        f"No changes between v{older_version} and v{newer_version}\n"
                    )

            print_success(f"Generated diff for v{newer_version}")
            return True

        except Exception as e:
            print_warning(f"Diff generation failed for v{newer_version}: {e}")
            self._notify_failure(
                "diff generation failed",
                f"v{newer_version}: {e}",
            )
            diff_file.unlink(missing_ok=True)
            return False

    def generate_diff(
        self, older_file: Path, newer_file: Path, iteration: int = 1
    ) -> bool:
        """Generate diff between two consecutive versions. Returns True on success."""
        # Prepared legacy inputs are named pretty-vVERSION.js. Split-module
        # inputs retain their original cli-vVERSION.js names so both sides use
        # the same esbuild normalization.
        if self.project.extract_files is None:
            regex_pattern = r"(?:pretty|cli)-v([0-9.]+)\.js$"
        else:
            prefix = self.project.primary_file_prefix
            regex_pattern = rf"(?:pretty-)?{prefix}-v([0-9.]+)\.[a-z]+$"

        # Extract version from newer file
        match = re.match(regex_pattern, newer_file.name)
        if not match:
            return False

        newer_version = match.group(1)

        # Extract version from older file
        older_match = re.match(regex_pattern, older_file.name)
        if not older_match:
            return False

        older_version = older_match.group(1)

        # Add iteration suffix if > 1
        if iteration > 1:
            diff_file = self.diff_dir / f"v{newer_version}-{iteration}.diff"
        else:
            diff_file = self.diff_dir / f"v{newer_version}.diff"

        print(f"\n--- Generating diff: v{older_version} -> v{newer_version} ---")

        try:
            # Use astdiff only if project configuration enables it
            use_astdiff = False
            if self.project.use_astdiff:
                astdiff_path = shutil.which(self.astdiff_executable)
                use_astdiff = astdiff_path is not None
                if not use_astdiff:
                    raise RuntimeError(
                        f"Required astdiff executable {self.astdiff_executable!r} was not found. "
                        "Set --astdiff-bin or CHANGELOG_ASTDIFF_BIN to a working build."
                    )

            if use_astdiff:
                astdiff_path = str(Path(astdiff_path).resolve())
                print_info(f"Using astdiff: {astdiff_path}")
                def artifact(path):
                    with Path(path).open("rb") as source:
                        digest = hashlib.file_digest(source, "sha256").hexdigest()
                    return {"path": str(Path(path).resolve()), "sha256": digest}

                provenance = {
                    "astdiff": artifact(astdiff_path),
                    "older": artifact(older_file),
                    "newer": artifact(newer_file),
                    "threads": self.astdiff_threads,
                }
                result = self._run_astdiff(
                    astdiff_path, older_file, newer_file
                )
            else:
                # Use regular diff for projects configured for textual diffs.
                # diff returns 1 when files differ, which is normal
                result = run(
                    ["diff", "-u", str(older_file), str(newer_file)],
                    capture_output=True,
                    text=True,
                )
                if result.returncode not in (0, 1):
                    print_warning(
                        f"diff failed for v{newer_version} "
                        f"(exit {result.returncode}): {result.stderr.strip()}"
                    )
                    return False

            if result is None:
                # astdiff failed after retries
                return False

            # Write diff output (even if empty - that means no changes)
            with open(diff_file, "w", encoding="utf-8") as f:
                if result.stdout:
                    f.write(result.stdout)
                else:
                    f.write(
                        f"No changes between v{older_version} and v{newer_version}\n"
                    )

            print_success(f"Generated diff for v{newer_version}")
            if use_astdiff:
                provenance["output"] = artifact(diff_file)
                diff_file.with_suffix(".meta.json").write_text(
                    json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
                )
            return True

        except Exception as e:
            print_warning(f"Diff generation failed for v{newer_version}: {e}")
            diff_file.unlink(missing_ok=True)
            diff_file.with_suffix(".meta.json").unlink(missing_ok=True)
            return False

    def _run_astdiff(self, astdiff_path, older_file, newer_file, retries=1):
        """Run astdiff with retry on OOM/crash. Returns CompletedProcess or None."""
        env = None
        if self.astdiff_threads is not None:
            env = {**os.environ, "RAYON_NUM_THREADS": str(self.astdiff_threads)}
        for attempt in range(1 + retries):
            result = run(
                [astdiff_path, str(older_file), str(newer_file)],
                capture_output=True,
                text=True,
                env=env,
            )
            if result.returncode == 0:
                return result

            # Identify the failure type from return code
            sig = -result.returncode if result.returncode < 0 else None
            if sig in (signal.SIGABRT, signal.SIGKILL):
                cause = "out of memory"
            else:
                cause = f"exit {result.returncode}"
            stderr_tail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else ""

            if attempt < retries:
                print_warning(
                    f"astdiff failed ({cause}: {stderr_tail}), "
                    f"retrying in 30s..."
                )
                time.sleep(30)
            else:
                print_warning(
                    f"astdiff failed ({cause}: {stderr_tail}), "
                    f"no retries left"
                )
        return None

    def generate_string_diff(self, version_str: str) -> Optional[str]:
        """
        Generate a string diff for a version using the AST-based string_diff.js tool.
        Returns the diff output as a string, or None if it fails.
        """
        # string_diff.js parses minified JavaScript via Acorn.  Projects without
        # a pretty/ directory (i.e. GitHub-based source projects like codex) have
        # nothing for it to chew on; the fallback path below would dereference
        # self.pretty_dir which is None for those, raising a TypeError.
        if self.pretty_dir is None:
            return None

        # Find the string_diff.js tool - it's in the same directory as this script
        tools_dir = Path(__file__).parent
        string_diff_tool = tools_dir / "string_diff.js"

        if not string_diff_tool.exists():
            print_warning("string_diff.js not found, skipping string diff")
            return None

        # The string_diff.js tool has a built-in 'compare' command that handles version lookup
        try:
            result = run(
                ["node", str(string_diff_tool), "compare", version_str.lstrip("v"), "--filter"],
                capture_output=True,
                text=True,
                cwd=str(tools_dir.parent),  # Run from project root so paths resolve correctly
            )

            if result.returncode == 0:
                return result.stdout
            else:
                # If compare fails, try using the pretty_dir directly
                current_file = self.pretty_dir / f"pretty-v{version_str}.js"
                if not current_file.exists():
                    return None

                # Find previous version
                all_pretty_files = sorted(
                    self.pretty_dir.glob("pretty-v*.js"),
                    key=lambda p: version.parse(
                        re.match(r"pretty-v([0-9.]+)\.js$", p.name).group(1)
                    ),
                )
                prev_file = None
                for i, f in enumerate(all_pretty_files):
                    if f == current_file and i > 0:
                        prev_file = all_pretty_files[i - 1]
                        break

                if not prev_file:
                    return None

                result = run(
                    ["node", str(string_diff_tool), "diff", str(prev_file), str(current_file), "--filter"],
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    return result.stdout
                else:
                    print_warning(f"String diff failed: {result.stderr}")
                    return None

        except Exception as e:
            print_warning(f"String diff generation failed: {e}")
            return None

    def phase_3_generate_diffs(self, all_versions: Optional[List[str]] = None):
        """Phase 3: Generate diffs between consecutive versions"""
        if not self.diff:
            return

        print_header("Phase 3: Generating Diffs")
        print_info("Checking for diffs to generate...")

        if self.project.is_github_based:
            # GitHub mode: use git diff between tags
            if not all_versions:
                print_error("No versions provided for diff generation")
                return

            versions_to_diff = self.get_versions_to_diff_github(all_versions)

            if not versions_to_diff:
                print_info("All diffs already generated.")
                return

            order_desc = "newest first" if self.new_first else "oldest first"
            print_info(
                f"Found {len(versions_to_diff)} diffs to generate (processing {order_desc})"
            )

            for older_version, newer_version in versions_to_diff:
                if self.generate_diff_github(older_version, newer_version):
                    self.stats.diff_generated_count += 1
                else:
                    self.stats.diff_generation_failures += 1
        else:
            # npm mode: compare files
            files_to_diff = self.get_files_to_diff(all_versions)

            if self._blocked_diff_versions:
                self.stats.diff_generation_failures += len(
                    self._blocked_diff_versions
                )
                for version_str, missing in self._blocked_diff_versions.items():
                    names = ", ".join(path.name for path in missing)
                    print_warning(
                        f"Diff for v{version_str} is blocked by missing analysis "
                        f"input: {names}"
                    )

            if not files_to_diff:
                if not self._blocked_diff_versions:
                    print_info("All diffs already generated.")
                return

            order_desc = "newest first" if self.new_first else "oldest first"
            print_info(
                f"Found {len(files_to_diff)} diffs to generate (processing {order_desc})"
            )

            for older_file, newer_file in files_to_diff:
                if self.generate_diff(older_file, newer_file):
                    self.stats.diff_generated_count += 1
                else:
                    self.stats.diff_generation_failures += 1

        print_info(f"\nGenerated {self.stats.diff_generated_count} new diffs.")
        if self.stats.diff_generation_failures > 0:
            print_warning(
                f"{self.stats.diff_generation_failures} diff generations failed."
            )

    def _get_versions_needing_output(self, output_dir: Path, filename_template: str) -> List[str]:
        """Get list of versions that have diffs but no corresponding output file.

        Args:
            output_dir: Directory to check for existing output files
            filename_template: Template with {version} placeholder, e.g. "changelog-v{version}.md"
        """
        versions_needed = []

        # Get all diff files
        diff_files = list(self.diff_dir.glob("v*.diff"))

        if self.latest and diff_files:
            # For --latest, only check the most recent diff
            valid_diff_files = [
                f for f in diff_files
                if RE_DIFF_VERSION.match(f.name)
            ]

            if valid_diff_files:
                valid_diff_files.sort(
                    key=lambda p: version.parse(
                        RE_DIFF_VERSION.match(p.name).group(1)
                    ),
                    reverse=True,
                )
                diff_files = [valid_diff_files[0]]
            else:
                diff_files = []

        for diff_file in diff_files:
            match = RE_DIFF_VERSION.match(diff_file.name)
            if not match:
                continue

            version_str = match.group(1)

            if self._is_before_since(version_str):
                continue

            output_file = output_dir / filename_template.format(version=version_str)

            if not output_file.exists():
                versions_needed.append(version_str)

        return sorted(set(versions_needed), key=version.parse, reverse=self.new_first)

    def get_versions_to_changelog(self) -> List[str]:
        """Get list of versions that need changelogs generated"""
        return self._get_versions_needing_output(
            self.changelog_dir, "changelog-v{version}.md"
        )

    def cleanup_single_changelog(self, changelog_file: Path, version_str: str) -> bool:
        """Clean up a single changelog file. Returns True on success."""
        try:
            cleanup_module = self._get_cleanup_module()
            if cleanup_module is None:
                print_warning("cleanup_changelogs.py not found, skipping cleanup")
                self.stats.changelog_cleanup_failures += 1
                return False

            content = changelog_file.read_text()
            cleaned_content, was_modified = cleanup_module.cleanup_changelog(content, version_str)

            if was_modified:
                changelog_file.write_text(cleaned_content)
                orig_lines = len(content.split('\n'))
                new_lines = len(cleaned_content.split('\n'))
                print_success(f"Cleaned {changelog_file.name} ({orig_lines - new_lines} lines removed)")
                self.stats.changelogs_cleaned_count += 1
            else:
                print_info(f"No cleanup needed for {changelog_file.name}")

            return True

        except Exception as e:
            print_warning(f"Failed to clean {changelog_file.name}: {e}")
            self.stats.changelog_cleanup_failures += 1
            return False

    def post_single_changelog(self, changelog_file: Path, version_str: str) -> bool:
        """
        Post a single changelog to Discord using multi-webhook config.
        Returns True on success.

        NOTE: This posts immediately after generating each changelog (inline mode).
        The version is posted to all webhooks subscribed to this project's channel.
        """
        try:
            post_script = self.base_dir / "tools" / "post.py"

            if not post_script.exists():
                print_warning("post.py not found, skipping post")
                self.stats.changelog_post_failures += 1
                return False

            # Post this specific version to all configured webhooks for this project
            cmd = [
                str(post_script),
                str(changelog_file.resolve()),
                "--project", self.project.name,
            ]

            if self.dry_run:
                cmd.append("--dry-run")

            result = run(
                cmd,
                cwd=str(self.base_dir),
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode == 0:
                self.stats.changelogs_posted_count += 1
                print_success(f"Posted {changelog_file.name} to Discord")
                return True
            else:
                self.stats.changelog_post_failures += 1
                if result.stderr:
                    print_warning(f"post.py error: {result.stderr.strip()}")
                return False

        except Exception as e:
            print_warning(f"Failed to post {changelog_file.name}: {e}")
            self.stats.changelog_post_failures += 1
            return False

    def git_commit_changelog(self, changelog_file: Path, version_str: str) -> bool:
        """Commit and push a single changelog file, touching nothing else.

        Uses a pathspec-scoped `git commit -- <path>` so unrelated dirty
        state elsewhere in the working tree (in-progress edits, scratch
        dirs) is never swept in. Returns True on success.
        """
        rel_path = self._relative_display_path(changelog_file)
        try:
            status = run(
                ["git", "-C", str(self.base_dir), "status", "--porcelain", "--", rel_path],
                capture_output=True,
                text=True,
                check=False,
            )
            if status.returncode != 0:
                raise RuntimeError(status.stderr.strip() or 'git status failed')
            if not status.stdout.strip():
                # A previous run may have committed successfully but failed
                # to push. The delivery queue still needs to retry that push.
                return self.git_push_changelog(rel_path, version_str)

            if self.dry_run:
                print_info(f"[dry-run] Would commit and push {rel_path}")
                return True

            add = run(
                ["git", "-C", str(self.base_dir), "add", "--", rel_path],
                capture_output=True,
                text=True,
                check=False,
            )
            if add.returncode != 0:
                print_warning(f"git add failed for {rel_path}: {add.stderr.strip()}")
                self.stats.changelog_commit_failures += 1
                return False

            resolved_model = (
                getattr(self._changelog_agent, "last_resolved_model", None)
                or self.changelog_model
            )
            agent_name = {
                "claude": "Claude",
                "codex": "Codex",
                "qwen": "Qwen",
            }[self.agent_provider]
            commit_message = (
                f"archive: add {self.project.name} changelog for v{version_str}\n\n"
                f"Assisted-by: {agent_name} {resolved_model}\n"
            )
            message_path = self.base_dir / 'commit-msg'
            # Never overwrite a message left by an interrupted manual commit.
            if message_path.exists():
                if message_path.read_text() != commit_message:
                    raise RuntimeError('commit-msg belongs to another pending commit')
            else:
                with message_path.open('x', encoding='utf-8') as message_file:
                    message_file.write(commit_message)
            commit = run(
                ["git", "-C", str(self.base_dir), "commit", "-F", str(message_path), "--", rel_path],
                capture_output=True,
                text=True,
                check=False,
            )
            if commit.returncode != 0:
                print_warning(f"git commit failed for {rel_path}: {commit.stderr.strip()}")
                self.stats.changelog_commit_failures += 1
                return False
            message_path.unlink()

            return self.git_push_changelog(rel_path, version_str)

        except Exception as e:
            print_warning(f"git commit/push failed for {rel_path}: {e}")
            self.stats.changelog_commit_failures += 1
            return False

    def git_push_changelog(self, rel_path: str, version_str: str) -> bool:
        """Push pending archive commits, including after an earlier failure."""
        if self.dry_run:
            print_info(f"[dry-run] Would push {rel_path}")
            return True
        try:

            push_cmd = ["git", "-C", str(self.base_dir), "push"]
            if self.git_remote:
                push_cmd.append(self.git_remote)
            push = run(push_cmd, capture_output=True, text=True, check=False)
            if push.returncode != 0 and self.git_https_fallback:
                # The default push likely goes over SSH with a
                # Yubikey-touch-gated key, which nothing can satisfy from an
                # unattended run. Retry over HTTPS using gh's stored token
                # (already configured as git's credential helper for
                # github.com) instead of weakening the SSH/signing setup.
                # Opt-in via --git-https-fallback / CHANGELOG_GIT_HTTPS_FALLBACK
                # since it depends on gh being installed and authenticated.
                fallback = self._push_via_gh_https()
                if fallback is not None:
                    print_warning(
                        f"git push (ssh) failed for {rel_path}, retrying via gh over HTTPS"
                    )
                    push = fallback

            if push.returncode != 0:
                print_warning(f"git push failed after committing {rel_path}: {push.stderr.strip()}")
                self._notify_failure(
                    "changelog auto-push failed",
                    f"v{version_str}: {push.stderr.strip()[:300]}",
                )
                self.stats.changelog_commit_failures += 1
                return False

            self.stats.changelogs_committed_count += 1
            print_success(f"Committed and pushed {rel_path}")
            return True

        except Exception as e:
            print_warning(f"git commit/push failed for {rel_path}: {e}")
            self.stats.changelog_commit_failures += 1
            return False

    def _push_via_gh_https(self):
        """Retry the current branch's push over HTTPS using gh's stored
        OAuth token instead of the SSH remote. Returns the CompletedProcess,
        or None if there's no github.com upstream to translate (e.g. a
        non-GitHub remote), in which case the caller keeps the original
        SSH failure.
        """
        branch = run(
            ["git", "-C", str(self.base_dir), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()

        if self.git_remote:
            remote_name = self.git_remote
        else:
            upstream = run(
                ["git", "-C", str(self.base_dir), "rev-parse",
                 "--abbrev-ref", "--symbolic-full-name", "@{u}"],
                capture_output=True,
                text=True,
                check=False,
            ).stdout.strip()
            remote_name, sep, upstream_branch = upstream.partition("/")
            if not sep:
                return None
            branch = upstream_branch or branch

        remote_url = run(
            ["git", "-C", str(self.base_dir), "remote", "get-url", remote_name],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        https_url = re.sub(r"^git@github\.com:", "https://github.com/", remote_url)
        if https_url == remote_url and not remote_url.startswith("https://github.com"):
            return None  # not a github.com remote; gh's helper won't apply

        return run(
            ["git", "-C", str(self.base_dir), "push", https_url, f"HEAD:{branch}"],
            capture_output=True,
            text=True,
            check=False,
        )

    def _get_cleanup_module(self):
        """Load and cache the cleanup_changelogs module."""
        if self._cleanup_module is not None:
            return self._cleanup_module

        import importlib.util
        cleanup_script = self.base_dir / "tools" / "cleanup_changelogs.py"

        if not cleanup_script.exists():
            return None

        spec = importlib.util.spec_from_file_location("cleanup_changelogs", cleanup_script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self._cleanup_module = module
        return module

    def _get_agent_runner(self, role: str):
        """Build and cache the configured agent runner for a role."""
        base_url = self.qwen_base_url if self.agent_provider == "qwen" else None
        if role == "annotation":
            if self._annotation_agent is None:
                self._annotation_agent = make_agent_runner(
                    self.agent_provider,
                    model=self.annotation_model,
                    reasoning_effort=(
                        self.codex_annotation_reasoning_effort
                        if self.agent_provider == "codex"
                        else None
                    ),
                    executable=self.codex_executable,
                    base_url=base_url,
                )
            return self._annotation_agent

        if self._changelog_agent is None:
            self._changelog_agent = make_agent_runner(
                self.agent_provider,
                model=self.changelog_model,
                reasoning_effort=(
                    self.codex_reasoning_effort
                    if self.agent_provider == "codex"
                    else None
                ),
                executable=self.codex_executable,
                base_url=base_url,
            )
        return self._changelog_agent

    def _check_agent_available(self, feature_name: str, role: str = "changelog") -> bool:
        """Check if the configured agent provider is available."""
        try:
            self._get_agent_runner(role).check_available()
            return True
        except AgentRunnerError as e:
            print_warning(
                f"{self.agent_provider} agent is unavailable. Skipping {feature_name}: {e}"
            )
            return False

    def _get_tool_version(self) -> str:
        """Return a repo version string for changelog provenance."""
        if self._tool_version is not None:
            return self._tool_version

        try:
            result = run(
                ["git", "-C", str(self.base_dir), "describe", "--always", "--dirty"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                self._tool_version = result.stdout.strip()
            else:
                self._tool_version = "unknown"
        except Exception:
            self._tool_version = "unknown"

        return self._tool_version

    def _relative_display_path(self, path: Path) -> str:
        """Render a repository-relative path when possible."""
        try:
            return str(path.relative_to(self.base_dir))
        except ValueError:
            return str(path)

    def _append_generation_metadata(
        self, changelog_file: Path, inputs: ChangelogInputs
    ) -> None:
        """Append the generation trailer to an accepted changelog."""
        # Report the concrete model that actually served the request, not
        # just the (possibly alias) string we requested — e.g. "sonnet" may
        # resolve to a different snapshot over time.
        resolved_model = (
            getattr(self._changelog_agent, "last_resolved_model", None)
            or self.changelog_model
        )
        trailer = format_trailer(
            inputs,
            tool_version=self._get_tool_version(),
            provider=self.agent_provider,
            model=resolved_model,
            effort=self.codex_reasoning_effort if self.agent_provider == "codex" else None,
            annotation_model=self.annotation_model,
            expects_astdiff=self.project.use_astdiff,
        )
        body = changelog_file.read_text(encoding="utf-8").rstrip()
        changelog_file.write_text(f"{body}\n\n\n{trailer}\n", encoding="utf-8")

    def _ensure_prompt_file(self, directory: Path, filename: str, default_content: str, label: str):
        """Ensure a prompt file exists, creating it with defaults if missing."""
        prompt_file = directory / filename
        if not prompt_file.exists():
            print_info(f"Creating default {label} system prompt file...")
            with open(prompt_file, "w", encoding="utf-8") as f:
                f.write(default_content)
            print_success(f"Created {prompt_file}")
            print_info(f"You can edit this file to customize {label} generation")

    def _run_agent_query(
        self,
        prompt: str,
        system_prompt: str = "",
        allowed_tools: Optional[List[str]] = None,
        cwd: Optional[Path] = None,
        env: Optional[dict] = None,
        timeout: Optional[int] = None,
        role: str = "changelog",
    ) -> str:
        """Run the configured agent provider synchronously."""
        request = AgentRunRequest(
            prompt=prompt,
            system_prompt=system_prompt,
            cwd=cwd or self._ensure_agent_cwd(),
            allowed_tools=allowed_tools,
            env=env,
            timeout=timeout,
            read_roots=[self.archive_dir, self.temp_dir, self.agent_cwd],
        )
        return self._get_agent_runner(role).run(request)

    def _ensure_agent_cwd(self) -> Path:
        """Create and return the dedicated cwd for SDK agent runs.

        Keeps agent sessions in their own cwd bucket (see self.agent_cwd) so
        they don't clutter the user's personal session list for this repo.
        """
        self.agent_cwd.mkdir(parents=True, exist_ok=True)
        return self.agent_cwd

    # ── Annotation pipeline (hybrid changelog mode) ───────────────────────────

    def _run_annotation_pipeline(
        self, version_str: str, changes_file: Optional[Path] = None,
    ) -> Optional[str]:
        """Annotate the current diff; never reuse batches from a different input."""
        import asyncio
        from pipeline_io import write_json
        from slice_changes import make_batches, parse_slices, write_batches

        version = f"v{version_str}"
        changes_dir = self.changes_dir / version
        batches_dir = changes_dir / "batches"
        summary_path = changes_dir / f"annotations-{version}.json"
        summary_path.unlink(missing_ok=True)
        if changes_file is None:
            changes_file = next((path for ext in (".md", ".diff")
                                 if (path := self.changes_dir / f"changes-{version}{ext}").exists()),
                                self.diff_dir / f"{version}.diff")
        batches = make_batches(parse_slices(changes_file))
        write_batches(batches, batches_dir)
        if not batches:
            print_info("No annotatable changes; using the diff directly")
            return None

        annotations = asyncio.run(self._annotate_all_batches(batches_dir))
        if self.pretty_dir:
            pretty_file = self.pretty_dir / f"pretty-{version}.js"
            if pretty_file.exists():
                annotations = self._verify_annotation_claims(annotations, pretty_file)
        write_json(summary_path, annotations)
        print_info(f"Annotation summary: {len(annotations)} entries → {summary_path.name}")
        return format_annotation_summary(annotations, version) if annotations else None

    async def _annotate_all_batches(self, batches_dir: Path) -> list:
        """Use the same validated provider/cache path as annotate_changes.py."""
        from annotate_changes import annotate_batches
        return await annotate_batches(
            batches_dir, agent_provider=self.agent_provider, model=self.annotation_model,
            codex_reasoning_effort=self.codex_annotation_reasoning_effort,
            codex_bin=self.codex_executable, qwen_base_url=self.qwen_base_url,
            cwd=self._ensure_agent_cwd(),
        )

    def _verify_annotation_claims(self, annotations: list, pretty_file: Path) -> list:
        """Verify all annotation claims against the new-version source.

        Removals: downgrade to 'refactor' if primary evidence term is still
        present in the new source (feature wasn't actually removed).

        Positive claims (new_feature / enhancement / bug_fix): flag as
        low-confidence if primary evidence term is NOT in the new source
        (annotator may have cited non-existent evidence).
        """
        mb = pretty_file.stat().st_size // 1024 // 1024
        print_info(f"Verifying annotation claims against {pretty_file.name} ({mb}MB)...")
        source = pretty_file.read_text(encoding="utf-8", errors="replace")

        removal_fp = 0
        positive_unverified = 0
        updated = []

        for ann in annotations:
            ann_copy = dict(ann)
            ct = ann.get("change_type", "")
            imp = ann.get("importance", 0)

            if ct == "removal" and imp >= 2:
                term = primary_evidence_term(ann)
                if term and term in source:
                    ann_copy["change_type"] = "refactor"
                    ann_copy["_removal_verified"] = False
                    ann_copy["_removal_note"] = f"Feature still present: '{term}' found in source"
                    removal_fp += 1
                else:
                    ann_copy["_removal_verified"] = True

            elif ct in POSITIVE_CLAIM_TYPES and imp >= 3:
                term = primary_evidence_term(ann)
                if term is not None:
                    if term in source:
                        ann_copy["_evidence_verified"] = True
                    else:
                        ann_copy["_evidence_verified"] = False
                        ann_copy["_evidence_note"] = f"Primary term '{term}' not found in source"
                        positive_unverified += 1

            updated.append(ann_copy)

        removal_count = sum(1 for a in annotations if a.get("change_type") == "removal")
        print_info(
            f"Removals: {removal_count} claimed, {removal_fp} downgraded. "
            f"Positive claims: {positive_unverified} flagged as unverified."
        )
        return updated

    # ─────────────────────────────────────────────────────────────────────────

    def _changelog_looks_broken(self, file_body: str, changes_lines: int) -> Optional[str]:
        """Heuristic validator for generated changelogs.

        Returns None if the body looks OK, or a short reason string if it
        appears to be a summary/outline rather than a real changelog body.
        """
        body = (file_body or "").strip()
        if not body:
            return "empty file"
        if len(body) < 200:
            return f"body too short ({len(body)} chars)"
        section_headings = sum(1 for line in body.splitlines() if line.startswith("## "))
        if section_headings < 1:
            return "no '## ' section headings"
        return None

    def _select_primary_diff(
        self, version_str: str, iteration: int, diff_file: Path
    ) -> Tuple[Path, str]:
        """Pick the code diff to hand the changelog agent, and classify it.

        Prefers phase-5 output; falls back to the phase-3 diff so the agent
        always sees code changes, not just the string diff. Returns the path
        (never read into memory here — large diffs exceed ARG_MAX when passed
        inline) and a key of ``PRIMARY_DIFF_LABELS``.
        """
        if self.project.use_astdiff:
            self._refresh_filtered_diff(version_str, iteration, diff_file)
        suffix = f"-{iteration}" if iteration > 1 else ""
        stems = [f"changes-v{version_str}{suffix}"] if suffix else []
        stems.append(f"changes-v{version_str}")
        for stem in stems:
            # Phase 5 writes .md for filtered astdiff, .diff for passthrough.
            for ext, kind in ((".md", "astdiff"), (".diff", "raw")):
                candidate = self.changes_dir / f"{stem}{ext}"
                if candidate.exists():
                    return candidate, kind

        with open(diff_file, encoding="utf-8", errors="replace") as f:
            head = f.read(65536)
        kind = "astdiff-unfiltered" if looks_like_astdiff(head) else "raw"
        return diff_file, kind

    def _refresh_filtered_diff(
        self, version_str: str, iteration: int, diff_file: Path
    ) -> None:
        """Re-run phase 5 when its output is missing or older than the diff.

        Filtering is cheap and deterministic, so rerunning it is safer than
        handing the agent a stale filtered file from an earlier diff.
        """
        suffix = f"-{iteration}" if iteration > 1 else ""
        filtered = self.changes_dir / f"changes-v{version_str}{suffix}.md"
        if filtered.exists() and filtered.stat().st_mtime >= diff_file.stat().st_mtime:
            return
        reason = "older than its diff" if filtered.exists() else "missing"
        print_info(f"Filtered diff for v{version_str} is {reason}; refiltering")
        self.filter_diff(version_str, iteration)

    def generate_changelog(self, version_str: str, iteration: int = 1) -> bool:
        """Generate changelog for a specific version. Returns True on success."""
        # Use the appropriate diff file based on iteration
        if iteration > 1:
            diff_file = self.diff_dir / f"v{version_str}-{iteration}.diff"
            # If the iteration-specific diff doesn't exist, fall back to the original
            if not diff_file.exists():
                diff_file = self.diff_dir / f"v{version_str}.diff"
        else:
            diff_file = self.diff_dir / f"v{version_str}.diff"

        # Add iteration suffix to changelog if > 1
        if iteration > 1:
            changelog_file = (
                self.changelog_dir / f"changelog-v{version_str}-{iteration}.md"
            )
        else:
            changelog_file = self.changelog_dir / f"changelog-v{version_str}.md"

        # Only accepted, cleaned output may occupy the canonical filename.
        # Rejected/interrupted drafts stay out of discovery and posting globs.
        final_file = changelog_file
        changelog_file = self.changelog_dir / '.drafts' / final_file.name
        changelog_file.parent.mkdir(parents=True, exist_ok=True)

        print(f"\n--- Generating changelog for version {version_str} ---")

        if not diff_file.exists():
            print_warning(
                f"Diff file not found for version {version_str}. Run with --diff to generate diffs first."
            )
            return False

        try:
            primary_diff_path, primary_diff_kind = self._select_primary_diff(
                version_str, iteration, diff_file
            )
            if self.project.use_astdiff and primary_diff_kind != "astdiff":
                # Without astdiff the agent works from noisy input and misses
                # features; a late changelog beats a weak one.
                label = PRIMARY_DIFF_LABELS[primary_diff_kind]
                if not self.allow_degraded_diff:
                    print_warning(
                        f"v{version_str}: no filtered astdiff output (only {label}); "
                        "skipping. Pass --allow-degraded-diff to generate anyway."
                    )
                    self._notify_failure(
                        "changelog skipped: no astdiff",
                        f"v{version_str}: only {label} available",
                    )
                    return False
                print_warning(f"v{version_str}: generating from {label} input")

            # Generate string diff and persist it so the agent can Read it by path
            string_diff_path = None
            string_diff_output = self.generate_string_diff(version_str)
            if string_diff_output:
                print_info("Generated string diff for additional context")
                string_diff_path = self.changes_dir / f"string-diff-v{version_str}.txt"
                with open(string_diff_path, "w", encoding="utf-8") as f:
                    f.write(string_diff_output)

            official_release_notes_path = self._write_official_release_notes(version_str)

            # Run annotation pre-pass if requested (hybrid mode)
            annotation_summary = None
            if self.annotate:
                print_info("Running annotation pipeline (hybrid mode)...")
                annotation_summary = self._run_annotation_pipeline(
                    version_str, primary_diff_path,
                )
                if annotation_summary:
                    print_info("Annotation summary ready; using hybrid changelog mode")
                else:
                    print_warning("Annotation pipeline produced no output; falling back to diff-only mode")

            # Ensure system prompt file exists and read it
            self.ensure_changelog_prompt()
            system_prompt_file = self.changelog_dir / "system-prompt.md"
            with open(system_prompt_file, "r", encoding="utf-8") as f:
                system_prompt = f.read()

            modules_path = None
            if self.original_dir is not None:
                candidate = self.original_dir / f'cli-v{version_str}.modules.json'
                if candidate.exists():
                    modules_path = candidate
            unreleased_tag = None
            if self._is_unreleased_github_version(version_str):
                unreleased_tag = f"{self.project.github_tag_prefix or ''}{version_str}"
            inputs = ChangelogInputs(
                version=version_str,
                primary_diff_path=primary_diff_path,
                primary_diff_kind=primary_diff_kind,
                string_diff_path=string_diff_path,
                modules_path=modules_path,
                release_notes_path=official_release_notes_path,
                unreleased_tag=unreleased_tag,
                annotation_summary=annotation_summary,
            )

            changelog_agent = self._get_agent_runner("changelog")
            agent_writes_file = changelog_agent.supports_file_write_tool
            write_path = changelog_file.resolve() if agent_writes_file else None
            base_cli_prompt = build_changelog_prompt(inputs, write_path)

            # How many lines of input did the agent get? Used by the validator
            # to scale the minimum-output-size heuristic.
            try:
                with open(primary_diff_path, encoding='utf-8') as source:
                    changes_lines = sum(1 for _ in source)
            except Exception:
                changes_lines = 0

            try:
                cli_prompt = base_cli_prompt
                last_reason = None
                changelog_content = ""
                file_body = ""
                allowed_tools = ["Read", "Glob", "Grep"]
                if agent_writes_file:
                    allowed_tools.append("Write")
                for attempt in (1, 2):
                    # Pre-clear the target file so we can detect whether the
                    # agent actually wrote to it on this attempt.
                    changelog_file.unlink(missing_ok=True)

                    changelog_content = self._run_agent_query(
                        cli_prompt,
                        system_prompt=system_prompt,
                        allowed_tools=allowed_tools,
                        cwd=self._ensure_agent_cwd(),
                        role="changelog",
                    )

                    if agent_writes_file and changelog_file.exists():
                        try:
                            file_body = changelog_file.read_text(encoding="utf-8")
                        except Exception:
                            file_body = ""
                    else:
                        file_body = ""

                    if not file_body.strip() and changelog_content.strip():
                        # Claude fallback: agent ignored Write. Codex normal path:
                        # script writes the final read-only response.
                        with open(changelog_file, "w", encoding="utf-8") as f:
                            if not changelog_content.lstrip().startswith("# "):
                                f.write(f"# Changelog for version {version_str}\n\n")
                            f.write(changelog_content)
                        file_body = changelog_file.read_text(encoding="utf-8")

                    last_reason = self._changelog_looks_broken(file_body, changes_lines)
                    if not last_reason:
                        break

                    print_warning(
                        f"Changelog v{version_str} attempt {attempt} failed validation: {last_reason}"
                    )
                    if attempt == 2:
                        break

                    # Strengthen the prompt for the retry attempt.
                    cli_prompt = base_cli_prompt + retry_addendum(last_reason, write_path)
            except Exception as e:
                print_warning(f"{self.agent_provider} agent execution failed: {e}")
                return False

            if last_reason:
                print_warning(
                    f"Changelog v{version_str} still broken after retry ({last_reason}); "
                    "retaining draft but skipping cleanup/post"
                )
                self._notify_failure(
                    "changelog validation failed",
                    f"v{version_str}: {last_reason}",
                )
                return False

            self._append_generation_metadata(changelog_file, inputs)
            self._mark_unreleased_github_changelog(changelog_file, version_str)
            print_success(f"Generated changelog for v{version_str}")

            # Immediately clean up if cleanup is enabled
            if self.do_cleanup:
                if not self.cleanup_single_changelog(changelog_file, version_str):
                    return False

            # Queue before the atomic rename. If interrupted here, the draft
            # remains eligible for regeneration; delivery requires final_file.
            if (self.git_commit or self.post) and not self.dry_run:
                self._queue_delivery(final_file, version_str)
            changelog_file.replace(final_file)

            # Immediately commit and push (just this file) if enabled. Runs
            # after cleanup so the committed content is the final version.
            self._deliver_changelog(final_file, version_str)

            return True

        except Exception as e:
            print_warning(f"Changelog generation failed for v{version_str}: {e}")
            self._notify_failure(
                "changelog generation failed",
                f"v{version_str}: {e}",
            )
            changelog_file.unlink(missing_ok=True)
            return False

    def _delivery_path(self, changelog_file: Path) -> Path:
        return self.archive_dir / '.delivery' / (changelog_file.name + '.json')

    def _queue_delivery(self, changelog_file: Path, version_str: str) -> None:
        path = self._delivery_path(changelog_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        state = {'version': version_str, 'commit': self.git_commit, 'post': self.post}
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(state) + '\n')
        temporary.replace(path)

    def _deliver_changelog(self, changelog_file: Path, version_str: str) -> None:
        path = self._delivery_path(changelog_file)
        if self.dry_run:
            if self.git_commit:
                self.git_commit_changelog(changelog_file, version_str)
            if self.post:
                self.post_single_changelog(changelog_file, version_str)
            return
        if not path.exists():
            return
        state = json.loads(path.read_text())
        for action, enabled, deliver in (
            ('commit', self.git_commit, self.git_commit_changelog),
            ('post', self.post, self.post_single_changelog),
        ):
            if state.get(action) and enabled:
                if not deliver(changelog_file, version_str):
                    return
                state[action] = False
                temporary = path.with_suffix('.tmp')
                temporary.write_text(json.dumps(state) + '\n')
                temporary.replace(path)
        if not state.get('commit') and not state.get('post'):
            path.unlink()

    def retry_pending_deliveries(self) -> None:
        """Resume incomplete delivery on a later scheduled run, without regeneration."""
        for path in sorted((self.archive_dir / '.delivery').glob('*.json')):
            changelog_file = self.changelog_dir / path.name.removesuffix('.json')
            if changelog_file.exists():
                state = json.loads(path.read_text())
                self._deliver_changelog(changelog_file, state['version'])

    def phase_4_generate_changelogs(self):
        """Phase 4: Generate changelogs using claude CLI"""
        if not self.changelog:
            return

        print_header("Phase 4: Generating Changelogs")

        # Ensure the system prompt file exists
        self.ensure_changelog_prompt()

        if not self._check_agent_available("changelog generation", role="changelog"):
            self.stats.changelog_generation_failures += 1
            return

        print_info("Checking for changelogs to generate...")

        versions_to_changelog = self.get_versions_to_changelog()

        if not versions_to_changelog:
            if self._blocked_diff_versions:
                blocked = ", ".join(
                    f"v{value}" for value in self._blocked_diff_versions
                )
                print_warning(
                    f"Changelog generation is blocked by missing diffs for: {blocked}"
                )
            else:
                print_info("All changelogs already generated.")
            return

        order_desc = "newest first" if self.new_first else "oldest first"
        print_info(
            f"Found {len(versions_to_changelog)} changelogs to generate (processing {order_desc})"
        )

        for version_str in versions_to_changelog:
            if self.generate_changelog(version_str):
                self.stats.changelog_generated_count += 1
            else:
                self.stats.changelog_generation_failures += 1

        print_info(
            f"\nGenerated {self.stats.changelog_generated_count} new changelogs."
        )
        if self.stats.changelog_generation_failures > 0:
            print_warning(
                f"{self.stats.changelog_generation_failures} changelog generations failed."
            )

    def get_versions_to_filter(self) -> List[str]:
        """Get list of versions that need filtered diff files"""
        versions_needed = []
        diff_files = list(self.diff_dir.glob("v*.diff"))

        if self.latest and diff_files:
            valid_diff_files = [
                f for f in diff_files
                if RE_DIFF_VERSION.match(f.name)
            ]
            if valid_diff_files:
                valid_diff_files.sort(
                    key=lambda p: version.parse(
                        RE_DIFF_VERSION.match(p.name).group(1)
                    ),
                    reverse=True,
                )
                diff_files = [valid_diff_files[0]]
            else:
                diff_files = []

        for diff_file in diff_files:
            match = RE_DIFF_VERSION.match(diff_file.name)
            if not match:
                continue

            version_str = match.group(1)
            if self._is_before_since(version_str):
                continue

            md_output = self.changes_dir / f"changes-v{version_str}.md"
            raw_output = self.changes_dir / f"changes-v{version_str}.diff"
            if not md_output.exists() and not raw_output.exists():
                versions_needed.append(version_str)

        return sorted(set(versions_needed), key=version.parse, reverse=self.new_first)

    def filter_diff(self, version_str: str, iteration: int = 1) -> bool:
        """Filter astdiff output to remove noise. Pure Python, no SDK needed.
        Returns True on success."""
        if iteration > 1:
            diff_file = self.diff_dir / f"v{version_str}-{iteration}.diff"
            if not diff_file.exists():
                diff_file = self.diff_dir / f"v{version_str}.diff"
        else:
            diff_file = self.diff_dir / f"v{version_str}.diff"

        if iteration > 1:
            changes_file = self.changes_dir / f"changes-v{version_str}-{iteration}.md"
        else:
            changes_file = self.changes_dir / f"changes-v{version_str}.md"

        print(f"\n--- Filtering diff for version {version_str} ---")

        if not diff_file.exists():
            print_warning(
                f"Diff file not found for version {version_str}. "
                "Run with --diff to generate diffs first."
            )
            return False

        try:
            with open(diff_file, "r", encoding="utf-8") as f:
                content = f.read()

            if not looks_like_astdiff(content):
                if iteration > 1:
                    raw_changes_file = (
                        self.changes_dir / f"changes-v{version_str}-{iteration}.diff"
                    )
                else:
                    raw_changes_file = self.changes_dir / f"changes-v{version_str}.diff"
                raw_changes_file.write_text(content)
                print_info(
                    f"Diff for v{version_str} is not astdiff format; "
                    "saved raw diff for changelog input"
                )
                return True

            filtered = filter_astdiff(content)

            with open(changes_file, "w", encoding="utf-8") as f:
                f.write(filtered)

            print_success(f"Filtered diff for v{version_str}")
            return True

        except Exception as e:
            print_warning(f"Diff filtering failed for v{version_str}: {e}")
            changes_file.unlink(missing_ok=True)
            return False

    # ── phase 5 ────────────────────────────────────────────────────────

    def phase_5_filter_diffs(self):
        """Phase 5: Filter astdiff output to remove noise (no SDK needed)"""
        if not self.changes:
            return

        print_header("Phase 5: Filtering Diffs")

        if not self.project.use_astdiff:
            print_info(
                "Skipping diff filtering for this project; changelog generation "
                "will use raw unified diffs."
            )
            return

        print_info("Checking for diffs to filter...")

        versions = self.get_versions_to_filter()

        if not versions:
            if self._blocked_diff_versions:
                blocked = ", ".join(
                    f"v{value}" for value in self._blocked_diff_versions
                )
                print_warning(
                    f"Diff filtering is blocked by missing diffs for: {blocked}"
                )
            else:
                print_info("All diffs already filtered.")
            return

        order_desc = "newest first" if self.new_first else "oldest first"
        print_info(
            f"Found {len(versions)} diffs to filter (processing {order_desc})"
        )

        for version_str in versions:
            if self.filter_diff(version_str):
                self.stats.changes_generated_count += 1
            else:
                self.stats.changes_generation_failures += 1

        print_info(
            f"\nFiltered {self.stats.changes_generated_count} diffs."
        )
        if self.stats.changes_generation_failures > 0:
            print_warning(
                f"{self.stats.changes_generation_failures} filter operations failed."
            )

    def ensure_changelog_prompt(self):
        """Ensure the changelog system prompt file exists"""
        self._ensure_prompt_file(
            self.changelog_dir, "system-prompt.md",
            self.DEFAULT_CHANGELOG_PROMPT, "changelog"
        )

    def update_claude_md(self, version_str: str):
        """Update CLAUDE.md file to indicate the current version for analysis"""
        # Create CLAUDE.md in the project's archive directory
        claude_md_path = self.archive_dir / "CLAUDE.md"

        # Determine naming mode based on extract_files config
        if self.project.extract_files is None:
            # Legacy mode: pretty-v*.js
            pretty_files = list(self.pretty_dir.glob("pretty-v*.js"))
            regex_pattern = r"pretty-v([0-9.]+)\.js$"
            file_prefix = "pretty-v"
        else:
            # New mode: pretty-{prefix}-v*.js
            prefix = self.project.primary_file_prefix
            pretty_files = list(self.pretty_dir.glob(f"pretty-{prefix}-v*.js"))
            regex_pattern = rf"pretty-{prefix}-v([0-9.]+)\.js$"
            file_prefix = f"pretty-{prefix}-v"

        if pretty_files:
            # Sort by version to find the actual latest
            pretty_files.sort(
                key=lambda p: version.parse(
                    re.match(regex_pattern, p.name).group(1)
                    if re.match(regex_pattern, p.name) else "0"
                ),
                reverse=True,
            )
            latest_file = pretty_files[0]
            latest_match = re.match(regex_pattern, latest_file.name)
            if latest_match:
                latest_version = latest_match.group(1)
            else:
                latest_version = version_str
        else:
            latest_version = version_str

        # Project display name
        project_display = self.project.name.replace("-", " ").title()

        # Content for CLAUDE.md (using relative paths from archive subdirectory)
        claude_md_content = f"""# CLAUDE.md

This file provides guidance to Claude Code when working with the {self.project.name} archive.

## Current {project_display} Version

The latest prepared version available for analysis is **v{latest_version}**.

File location: `pretty/{file_prefix}{latest_version}.js`

## Archive Structure

- `original/` - Original CLI files from npm
- `pretty/` - Analysis inputs: Prettier output for legacy bundles and esbuild snapshots for split-module releases
- `diff/` - Diffs between consecutive versions
- `changelog/` - Generated changelogs for each version
- `changes/` - Detailed changes with semantic names

## Latest Version Information

When analyzing {project_display}'s source, please use the prepared version at:
`pretty/{file_prefix}{latest_version}.js`

Package: `{self.project.npm_package}`
"""

        # Write or update CLAUDE.md
        try:
            with open(claude_md_path, "w", encoding="utf-8") as f:
                f.write(claude_md_content)
            print_info(f"Updated {claude_md_path.relative_to(self.base_dir)} to reference v{latest_version}")
        except Exception as e:
            print_warning(f"Failed to update CLAUDE.md: {e}")

    def phase_6_cleanup_changelogs(self):
        """Phase 6: Clean up changelog headers"""
        if not self.do_cleanup:
            return

        # Skip if changelogs were already cleaned during phase 4
        if self.changelog:
            print_info("Changelogs already cleaned during generation phase")
            return

        print_header("Phase 6: Cleaning Up Changelogs")

        changelog_files = sorted(self.changelog_dir.glob("changelog-*.md"))

        if not changelog_files:
            print_info("No changelogs to clean up")
            return

        print_info(f"Processing {len(changelog_files)} changelog(s)...")

        for changelog_file in changelog_files:
            ver_match = re.match(r'changelog-v?(.+)\.md$', changelog_file.name)
            version_str = ver_match.group(1) if ver_match else "unknown"
            self.cleanup_single_changelog(changelog_file, version_str)

        if self.stats.changelogs_cleaned_count > 0:
            print_success(f"Cleaned {self.stats.changelogs_cleaned_count} changelog(s)")

    def phase_7_post_changelogs(self):
        """Phase 7: Post changelogs to Discord using multi-webhook config"""
        if not self.post:
            return

        # Skip if changelogs were already posted during phase 4
        if self.changelog:
            print_info("Changelogs already posted during generation phase")
            return

        print_header("Phase 7: Posting Changelogs to Discord")

        post_script = self.base_dir / "tools" / "post.py"

        if not post_script.exists():
            print_error("post.py not found")
            self.stats.changelog_post_failures += 1
            return

        # Use post.py with --new flag to post to all configured webhooks
        # that subscribe to this project's channel
        try:
            cmd = [
                str(post_script),
                "--new",
                "--project", self.project.name,
            ]

            if self.dry_run:
                cmd.append("--dry-run")

            print_info(f"Running: {' '.join(cmd)}")

            result = run(
                cmd,
                cwd=str(self.base_dir),
                capture_output=False,  # Let output go directly to terminal
                check=False
            )

            if result.returncode == 0:
                print_success("Successfully posted changelogs via post.py")
                # Note: post.py handles its own statistics and version tracking
            else:
                print_error(f"post.py exited with code {result.returncode}")
                self.stats.changelog_post_failures += 1

        except Exception as e:
            print_error(f"Failed to run post.py: {e}")
            self.stats.changelog_post_failures += 1

    def cleanup(self):
        """Clean up temporary files"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def print_summary(self):
        """Print final summary statistics"""
        print_header("Sync Complete")

        print(f"Total versions available: {self.stats.total_versions}")

        if self.project.is_github_based:
            # GitHub-based project summary
            print(f"Archive directory: {self.archive_dir}")
            print(f"Source repository: {self.source_dir}")
        else:
            # npm-based project summary
            archived_versions = len(list(self.original_dir.glob("cli-v*.js")))
            print(f"Total versions archived: {archived_versions}")
            print(f"Archive directory: {self.original_dir}")

            if self.stats.downloaded_count > 0:
                print_success(f"Downloaded {self.stats.downloaded_count} new versions")

            if self.prettier:
                prettified_count = len(list(self.pretty_dir.glob("pretty-v*.js")))
                print(f"Prepared analysis inputs: {prettified_count}")
                if self.stats.prettified_count > 0:
                    print_success(
                        f"Prepared {self.stats.prettified_count} new analysis inputs"
                    )

        if self.diff:
            diff_count = len(list(self.diff_dir.glob("v*.diff")))
            print(f"Version diffs: {diff_count}")
            if self.stats.diff_generated_count > 0:
                print_success(f"Generated {self.stats.diff_generated_count} new diffs")

        if self.changelog:
            changelog_count = len(list(self.changelog_dir.glob("changelog-v*.md")))
            print(f"Version changelogs: {changelog_count}")
            if self.stats.changelog_generated_count > 0:
                print_success(
                    f"Generated {self.stats.changelog_generated_count} new changelogs"
                )

        if self.changes:
            changes_count = len(
                list(self.changes_dir.glob("changes-v*.md"))
                + list(self.changes_dir.glob("changes-v*.diff"))
            )
            print(f"Filtered diffs: {changes_count}")
            if self.stats.changes_generated_count > 0:
                print_success(
                    f"Filtered {self.stats.changes_generated_count} diffs"
                )

        if self.do_cleanup:
            if self.stats.changelogs_cleaned_count > 0:
                print_success(
                    f"Cleaned {self.stats.changelogs_cleaned_count} changelog(s)"
                )

        if self.post:
            if self.stats.changelogs_posted_count > 0:
                print_success(
                    f"Posted {self.stats.changelogs_posted_count} changelog(s) to Discord"
                )

        if self.git_commit:
            if self.stats.changelogs_committed_count > 0:
                print_success(
                    f"Committed and pushed {self.stats.changelogs_committed_count} changelog(s)"
                )

        # Print any failures
        total_failures = self.failure_count()
        if total_failures > 0:
            print_warning(f"Total failures: {total_failures}")

    def failure_count(self) -> int:
        """Return the number of failed operations across all pipeline phases."""
        return (
            self.stats.download_failures
            + self.stats.prettier_failures
            + self.stats.diff_generation_failures
            + self.stats.changelog_generation_failures
            + self.stats.changes_generation_failures
            + self.stats.changelog_cleanup_failures
            + self.stats.changelog_post_failures
            + self.stats.changelog_commit_failures
        )

    def run(self):
        """Execute the sync process"""
        try:
            project_display = self.project.name.replace("-", " ").title()
            title = f"{project_display} Archive Sync Tool"
            print(colored(title, Colors.BOLD + Colors.PURPLE))
            print(colored("=" * len(title), Colors.PURPLE))
            if self.changelog or self.annotate:
                print_info(
                    f"Agent provider: {self.agent_provider} "
                    f"(changelog={self.changelog_model}, annotation={self.annotation_model})"
                )

            # Setup
            self.setup_directories()
            self.check_dependencies()
            if self.git_commit or self.post:
                self.retry_pending_deliveries()

            # npm versions come from the registry before the download phases.
            # GitHub versions are read from local tags after the repository has
            # been synchronized below.
            if not self.project.is_github_based:
                all_versions = self.get_npm_versions()

            # Execute phases
            if self.project.is_github_based:
                # GitHub-based projects
                self.sync_github_repo()
                all_versions = self.get_github_releases()
                if self.latest:
                    self.checkout_latest_github(all_versions)
                # Skip prettify phase for GitHub projects (source is already readable)
                self.phase_3_generate_diffs(all_versions)
            else:
                # npm-based projects
                self.phase_1_download_originals(all_versions)
                self.phase_2_prettify_files()
                self.phase_3_generate_diffs(all_versions)

            # Common phases for both project types
            self.phase_5_filter_diffs()
            self.phase_4_generate_changelogs()
            self.phase_6_cleanup_changelogs()
            self.phase_7_post_changelogs()

            # Summary
            self.print_summary()
            failures = self.failure_count()
            if failures:
                self._notify_failure(
                    "sync completed with failures",
                    f"{failures} operation(s) failed; see ai-cli-changelog-sync.log",
                )
            return failures

        except KeyboardInterrupt:
            print_warning("\nSync interrupted by user")
            sys.exit(1)
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            sys.exit(1)
        finally:
            self.cleanup()

    def parse_version_range(self, version_spec: str) -> List[str]:
        """Parse version range specification and return list of versions.

        Supports:
        - Single version: "1.0.69" or "v1.0.69"
        - Range: "1.0.69-1.0.71" or "v1.0.69-v1.0.71"
        - Open range: "1.0.69-" (from 1.0.69 to latest)
        - Shorthand: "69" -> "1.0.69", "69-71" -> "1.0.69-1.0.71"
        """
        versions = []

        # Get all available versions from diff files (works for both npm and GitHub projects)
        diff_files = list(self.diff_dir.glob("v*.diff"))
        available_versions = []
        for f in diff_files:
            # Extract version from diff filename (handle both v1.0.69.diff and v1.0.69-2.diff)
            match = RE_DIFF_VERSION.match(f.name)
            if match:
                ver = match.group(1)
                if ver not in available_versions:
                    available_versions.append(ver)

        # Sort versions
        available_versions.sort(key=version.parse)

        # Remove 'v' prefix if present
        version_spec = version_spec.lstrip("v")

        # Handle shorthand notation — resolve to the most recent version
        # series that matches (e.g. "69" matches 2.1.69 before 1.0.69)
        def resolve_shorthand(patch_num: str) -> Optional[str]:
            """Find the highest version ending in .{patch_num}."""
            candidates = [v for v in available_versions if v.endswith(f".{patch_num}")]
            if candidates:
                return max(candidates, key=version.parse)
            return None

        if re.match(r"^\d+$", version_spec):
            # Single shorthand version like "69"
            target = resolve_shorthand(version_spec)
            if target:
                return [target]
        elif re.match(r"^\d+-\d+$", version_spec):
            # Range shorthand like "69-71"
            start_num, end_num = version_spec.split("-")
            start_version = resolve_shorthand(start_num)
            end_version = resolve_shorthand(end_num)
            if not start_version or not end_version:
                return []
            for v in available_versions:
                if (
                    version.parse(start_version)
                    <= version.parse(v)
                    <= version.parse(end_version)
                ):
                    versions.append(v)
            return versions
        elif re.match(r"^\d+-$", version_spec):
            # Open range shorthand like "69-"
            start_num = version_spec.rstrip("-")
            start_version = resolve_shorthand(start_num)
            if not start_version:
                return []
            for v in available_versions:
                if version.parse(v) >= version.parse(start_version):
                    versions.append(v)
            return versions

        # Handle full version notation
        if "-" in version_spec:
            # Range notation
            parts = version_spec.split("-")
            if len(parts) == 2:
                start_version = parts[0]
                end_version = parts[1] if parts[1] else None

                for v in available_versions:
                    if version.parse(v) >= version.parse(start_version):
                        if end_version and version.parse(v) > version.parse(
                            end_version
                        ):
                            break
                        versions.append(v)
        else:
            # Single version
            if version_spec in available_versions:
                versions.append(version_spec)

        return versions

    def redo_versions(self):
        """Redo diff and changelog generation for specified versions."""
        if not self.redo:
            return

        print_header("Redoing Diffs and Changelogs")

        # Parse version range
        versions_to_redo = self.parse_version_range(self.redo)

        if not versions_to_redo:
            print_warning(f"No matching versions found for: {self.redo}")
            return

        print_info(
            f"Redoing {len(versions_to_redo)} version(s): {', '.join(versions_to_redo)}"
        )

        for version_str in versions_to_redo:
            # Find the next iteration number for this version
            diff_iteration = 1
            changelog_iteration = 1

            # Check existing diff files
            existing_diffs = list(self.diff_dir.glob(f"v{version_str}*.diff"))
            for diff_file in existing_diffs:
                match = re.match(
                    rf"v{re.escape(version_str)}(?:-(\d+))?\.diff$", diff_file.name
                )
                if match:
                    iter_num = int(match.group(1)) if match.group(1) else 1
                    diff_iteration = max(diff_iteration, iter_num + 1)

            # Check existing changelog files
            existing_changelogs = list(
                self.changelog_dir.glob(f"changelog-v{version_str}*.md")
            )
            for changelog_file in existing_changelogs:
                match = re.match(
                    rf"changelog-v{re.escape(version_str)}(?:-(\d+))?\.md$",
                    changelog_file.name,
                )
                if match:
                    iter_num = int(match.group(1)) if match.group(1) else 1
                    changelog_iteration = max(changelog_iteration, iter_num + 1)

            # Generate diff if requested
            if self.diff:
                if self.project.is_github_based:
                    # GitHub mode: use git tags
                    # Find all versions to determine the previous one
                    diff_versions = []
                    for f in self.diff_dir.glob("v*.diff"):
                        match = RE_DIFF_VERSION.match(f.name)
                        if match and match.group(1) not in diff_versions:
                            diff_versions.append(match.group(1))
                    all_versions_sorted = sorted(diff_versions, key=version.parse)
                    try:
                        version_index = all_versions_sorted.index(version_str)
                        if version_index > 0:
                            prev_version = all_versions_sorted[version_index - 1]
                            print_info(
                                f"Generating diff iteration {diff_iteration} for v{version_str}"
                            )
                            if self.generate_diff_github(prev_version, version_str, diff_iteration):
                                self.stats.diff_generated_count += 1
                            else:
                                self.stats.diff_generation_failures += 1
                        else:
                            print_warning(f"No previous version found for v{version_str}")
                    except ValueError:
                        print_warning(f"Version {version_str} not found in available versions")
                else:
                    # npm mode: use pretty files
                    pretty_file = self.pretty_dir / f"pretty-v{version_str}.js"
                    if not pretty_file.exists():
                        print_warning(f"Pretty file not found for v{version_str}")
                        continue

                    # Find previous version
                    all_pretty_files = sorted(
                        self.pretty_dir.glob("pretty-v*.js"),
                        key=lambda p: version.parse(
                            re.match(r"pretty-v([0-9.]+)\.js$", p.name).group(1)
                        ),
                    )
                    prev_file = None
                    for i, f in enumerate(all_pretty_files):
                        if f == pretty_file and i > 0:
                            prev_file = all_pretty_files[i - 1]
                            break

                    if prev_file:
                        print_info(
                            f"Generating diff iteration {diff_iteration} for v{version_str}"
                        )
                        if self.generate_diff(prev_file, pretty_file, diff_iteration):
                            self.stats.diff_generated_count += 1
                        else:
                            self.stats.diff_generation_failures += 1
                    else:
                        print_warning(f"No previous version found for v{version_str}")

            # Filter diff first (provides input for changelog)
            if self.changes:
                changes_iteration = changelog_iteration
                print_info(
                    f"Filtering diff iteration {changes_iteration} for v{version_str}"
                )
                if self.filter_diff(version_str, changes_iteration):
                    self.stats.changes_generated_count += 1
                else:
                    self.stats.changes_generation_failures += 1

            # Generate changelog (uses filtered diff if available)
            if self.changelog:
                print_info(
                    f"Generating changelog iteration {changelog_iteration} for v{version_str}"
                )
                if self.generate_changelog(version_str, changelog_iteration):
                    self.stats.changelog_generated_count += 1
                else:
                    self.stats.changelog_generation_failures += 1

        print_info(
            f"\nRedo complete: {self.stats.diff_generated_count} diffs, {self.stats.changelog_generated_count} changelogs"
        )
        if (
            self.stats.diff_generation_failures > 0
            or self.stats.changelog_generation_failures > 0
        ):
            print_warning(
                f"Failures: {self.stats.diff_generation_failures} diffs, {self.stats.changelog_generation_failures} changelogs"
            )


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Multi-Project Archive Sync Tool - Download and process CLI versions from npm",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --project claude-code                    # Download Claude Code files (default)
  %(prog)s --project codex --prettier               # Download and prettify Codex files
  %(prog)s --project claude-code --prettier --diff  # Generate diffs for Claude Code
  %(prog)s --all                                    # Run all processing steps (includes cleanup and post)
  %(prog)s --all --latest                           # Process only the most recent version
  %(prog)s --changelog --cleanup                    # Generate and clean up changelogs
  %(prog)s --cleanup --post                         # Clean up existing changelogs and post to Discord
  %(prog)s --changelog --since v1.0.50              # Generate changelogs for v1.0.50 and newer
  %(prog)s --all --since 1.0.50                     # Process all steps for versions 1.0.50+
  %(prog)s --changelog --new-first                  # Generate changelogs (newest first)
  %(prog)s --prettier --diff --changelog            # Generate diffs and changelogs
  %(prog)s --diff --changes                         # Generate diffs and filter to meaningful changes
  %(prog)s --project codex --changelog --agent-provider codex
  %(prog)s --redo 69 --changelog                    # Redo changelog for v1.0.69
  %(prog)s --project codex --all                    # Process all Codex versions
        """,
    )

    parser.add_argument(
        "--project",
        type=str,
        choices=list(PROJECTS.keys()),
        default="claude-code",
        help=f"Project to sync (default: claude-code). Available: {', '.join(PROJECTS.keys())}",
    )

    parser.add_argument(
        "--prettier",
        action="store_true",
        help="Create prettified versions of CLI files",
    )

    parser.add_argument(
        "--diff",
        action="store_true",
        help="Generate diffs between consecutive versions",
    )

    parser.add_argument(
        "--changelog",
        action="store_true",
        help="Generate changelogs using the configured agent provider (processes available diffs)",
    )

    parser.add_argument(
        "--changes",
        action="store_true",
        help="Filter astdiff output to remove version/build metadata changes and pair import changes",
    )

    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean up changelog headers (remove duplicate headers and meta-commentary)",
    )

    parser.add_argument(
        "--post",
        action="store_true",
        help="Post new changelogs to Discord via webhook",
    )

    parser.add_argument(
        "--git-commit",
        action="store_true",
        help="Commit and push each generated changelog file individually after cleanup",
    )

    parser.add_argument(
        "--git-remote",
        default=os.getenv("CHANGELOG_GIT_REMOTE"),
        help=(
            "Git remote to push generated changelogs to (used with --git-commit). "
            "Defaults to the current branch's tracked upstream if unset. "
            "Can also be set with CHANGELOG_GIT_REMOTE — keep this out of "
            "version control if it names a private remote."
        ),
    )

    parser.add_argument(
        "--git-https-fallback",
        action=argparse.BooleanOptionalAction,
        default=_env_bool("CHANGELOG_GIT_HTTPS_FALLBACK", False),
        help=(
            "If the --git-commit push fails (e.g. an SSH key gated behind a "
            "hardware-key touch that an unattended run can't provide), retry "
            "over HTTPS using `gh`'s stored credentials. Off by default since "
            "it requires gh installed and authenticated for the target host. "
            "Can also be set with CHANGELOG_GIT_HTTPS_FALLBACK=true."
        ),
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all processing steps (prettier, diff, filter, changelog, cleanup, post)",
    )

    parser.add_argument(
        "--latest", action="store_true", help="Process only the most recent version"
    )

    parser.add_argument(
        "--since",
        type=str,
        help="Only process versions at or after this version (e.g., --since v1.0.50)",
    )

    parser.add_argument(
        "--new-first",
        action="store_true",
        help="Process versions in reverse chronological order (newest first) instead of chronological order",
    )

    parser.add_argument(
        "--no-color", action="store_true", help="Disable colored output"
    )

    parser.add_argument(
        "--redo",
        type=str,
        help='Redo diff/changelog for specific version(s). Examples: "1.0.69", "69-71", "1.0.69-1.0.71", "69-"',
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Suppress commits, pushes, and Discord sends; local generation and model calls still run",
    )

    parser.add_argument(
        "--annotate",
        action=argparse.BooleanOptionalAction,
        default=_env_bool("CHANGELOG_ANNOTATE", False),
        help="Run a fast-model pre-annotation pass before changelog generation (hybrid mode: annotations + diffs). Default: CHANGELOG_ANNOTATE or disabled (many calls per version).",
    )

    parser.add_argument(
        "--astdiff-bin",
        default=os.getenv("CHANGELOG_ASTDIFF_BIN") or "astdiff",
        help="astdiff executable (or CHANGELOG_ASTDIFF_BIN). Default: astdiff on PATH",
    )

    parser.add_argument(
        "--allow-degraded-diff",
        action="store_true",
        help="Generate changelogs for astdiff projects even when only a raw or "
             "unfiltered diff is available (default: skip and retry later)",
    )

    parser.add_argument(
        "--astdiff-threads",
        type=int,
        default=None,
        help="Limit astdiff parallelism (RAYON_NUM_THREADS). Default: half of available cores",
    )

    parser.add_argument(
        "--agent-provider",
        choices=SUPPORTED_AGENT_PROVIDERS,
        default=os.getenv("CHANGELOG_AGENT_PROVIDER")
        or os.getenv("CHANGELOG_AGENT")
        or DEFAULT_AGENT_PROVIDER,
        help=(
            "Agent provider for changelog generation. Can also be set with "
            "CHANGELOG_AGENT_PROVIDER or CHANGELOG_AGENT. Default: codex"
        ),
    )

    parser.add_argument(
        "--changelog-model",
        default=os.getenv("CHANGELOG_AGENT_MODEL")
        or os.getenv("CHANGELOG_CHANGELOG_MODEL"),
        help=(
            "Model for final changelog generation. Defaults by provider "
            "(claude: sonnet, codex: gpt-6.1-sol)."
        ),
    )

    parser.add_argument(
        "--annotation-model",
        default=os.getenv("CHANGELOG_ANNOTATION_MODEL"),
        help=(
            "Model for --annotate batches. Defaults by provider "
            "(claude: claude-haiku-4-5-20251001, codex: gpt-6-luna)."
        ),
    )

    parser.add_argument(
        "--codex-reasoning-effort",
        default=os.getenv("CHANGELOG_CODEX_REASONING_EFFORT") or "medium",
        choices=["low", "medium", "high", "xhigh"],
        help="Codex reasoning effort for final changelog generation. Default: medium",
    )

    parser.add_argument(
        "--codex-annotation-reasoning-effort",
        default=os.getenv("CHANGELOG_CODEX_ANNOTATION_REASONING_EFFORT") or "low",
        choices=["low", "medium", "high", "xhigh"],
        help="Codex reasoning effort for --annotate batches. Default: low",
    )

    parser.add_argument(
        "--codex-bin",
        default=os.getenv("CHANGELOG_CODEX_BIN") or "codex",
        help="Codex executable to use when --agent-provider=codex. Default: codex",
    )

    parser.add_argument(
        "--qwen-base-url",
        default=os.getenv("CHANGELOG_OPENAI_BASE_URL"),
        help=(
            "OpenAI-compatible base URL for --agent-provider=qwen (e.g. "
            "http://sandbox.home:11434/v1). Can also be set with "
            "CHANGELOG_OPENAI_BASE_URL."
        ),
    )

    args = parser.parse_args()

    if args.agent_provider not in SUPPORTED_AGENT_PROVIDERS:
        parser.error(
            "--agent-provider must be one of: "
            + ", ".join(SUPPORTED_AGENT_PROVIDERS)
        )

    if args.changelog_model is None:
        args.changelog_model = default_model_for(args.agent_provider, "changelog")
    if args.annotation_model is None:
        args.annotation_model = default_model_for(args.agent_provider, "annotation")

    # Handle --all flag
    if args.all:
        args.prettier = True
        args.diff = True
        args.changes = True
        args.changelog = True
        args.cleanup = True
        args.post = True

    # --changelog implies --changes (filter step provides input for changelog)
    if args.changelog:
        args.changes = True

    # Disable colors if requested or if not a TTY
    if args.no_color or not sys.stdout.isatty():
        Colors.disable()

    # Find base directory (project root)
    script_path = Path(__file__).resolve()
    base_dir = script_path.parent.parent  # Go up from tools/ to project root

    # Get project configuration
    project = PROJECTS[args.project]

    # Create and run sync tool
    sync_tool = ClaudeCodeSync(
        base_dir=base_dir,
        project=project,
        prettier=args.prettier,
        diff=args.diff,
        changelog=args.changelog,
        changes=args.changes,
        cleanup=args.cleanup,
        post=args.post,
        git_commit=args.git_commit,
        git_remote=args.git_remote,
        git_https_fallback=args.git_https_fallback,
        latest=args.latest,
        since=args.since,
        new_first=args.new_first,
        redo=args.redo,
        dry_run=args.dry_run,
        annotate=args.annotate,
        astdiff_threads=args.astdiff_threads if args.astdiff_threads else os.cpu_count() // 2,
        astdiff_executable=args.astdiff_bin,
        allow_degraded_diff=args.allow_degraded_diff,
        agent_provider=args.agent_provider,
        changelog_model=args.changelog_model,
        annotation_model=args.annotation_model,
        codex_reasoning_effort=args.codex_reasoning_effort,
        codex_annotation_reasoning_effort=args.codex_annotation_reasoning_effort,
        codex_executable=args.codex_bin,
        qwen_base_url=args.qwen_base_url,
    )

    # If --redo is specified, run the redo process instead
    if args.redo:
        # For redo, we need at least one of diff, changelog, or changes
        if not args.diff and not args.changelog and not args.changes:
            print_error(
                "--redo requires at least one of --diff, --changelog, or --changes"
            )
            sys.exit(1)
        sync_tool.setup_directories()
        sync_tool.check_dependencies()
        try:
            sync_tool.redo_versions()
            sys.exit(min(sync_tool.failure_count(), 1))
        finally:
            sync_tool.cleanup()
    else:
        sys.exit(min(sync_tool.run(), 1))


if __name__ == "__main__":
    main()
