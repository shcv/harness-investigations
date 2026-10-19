#!/usr/bin/env python3
"""
Discord Changelog Poster

Posts Claude Code changelogs to Discord via webhook, creating forum threads for each version.
Tracks the last posted version to enable automatic posting of new changelogs.
"""

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
import requests
from packaging import version

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, skip loading .env file
    pass

# ANSI color codes for output
class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"

    @classmethod
    def disable(cls):
        """Disable colors for non-TTY output"""
        cls.RED = cls.GREEN = cls.YELLOW = cls.BLUE = cls.PURPLE = cls.CYAN = (
            cls.BOLD
        ) = cls.END = ""


def colored(text: str, color: str) -> str:
    """Apply color to text"""
    return f"{color}{text}{Colors.END}"


def print_header(title: str):
    """Print a colored section header"""
    print(f"\n{colored('=== ' + title + ' ===', Colors.BOLD + Colors.BLUE)}")


def print_success(message: str):
    """Print a green success message"""
    print(colored(f"✓ {message}", Colors.GREEN))


def print_warning(message: str):
    """Print a yellow warning message"""
    print(colored(f"⚠ Warning: {message}", Colors.YELLOW))


def print_error(message: str):
    """Print a red error message"""
    print(colored(f"✗ Error: {message}", Colors.RED), file=sys.stderr)


def print_info(message: str):
    """Print a blue info message"""
    print(colored(f"ℹ {message}", Colors.CYAN))


# Webhook configuration
@dataclass
class WebhookConfig:
    """Configuration for a Discord webhook"""
    name: str                           # Identifier for this webhook (e.g., "main", "volvox")
    url: str                            # Discord webhook URL
    channels: List[str]                 # Channel names this webhook subscribes to

    @classmethod
    def from_dict(cls, data: dict) -> 'WebhookConfig':
        """Create WebhookConfig from dictionary"""
        return cls(
            name=data['name'],
            url=data['url'],
            channels=data['channels'],
        )


# Channel configuration
@dataclass
class ChannelConfig:
    """Configuration for a content channel"""
    name: str                           # Channel identifier
    type: str                           # Channel type (e.g., "changelog")
    directory: Path                     # Path to content directory
    last_posted_version: Optional[str]  # Last posted version for this channel

    @classmethod
    def from_dict(cls, name: str, data: dict) -> 'ChannelConfig':
        """Create ChannelConfig from dictionary"""
        return cls(
            name=name,
            type=data['type'],
            directory=Path(data['directory']),
            last_posted_version=data.get('last_posted_version'),
        )


def get_config_path() -> Path:
    """Get the path to the config.py file"""
    return Path(__file__).parent / "config.py"


def load_webhook_configs() -> List[WebhookConfig]:
    """
    Load webhook configurations from config.py file.

    Returns:
        List of WebhookConfig objects, or empty list if file doesn't exist
    """
    try:
        # Try to import the config module
        import importlib.util
        config_path = get_config_path()

        if not config_path.exists():
            print_warning(f"Config file not found: {config_path}")
            print_info("Create config.py from config.py.example")
            return []

        # Load the config module
        spec = importlib.util.spec_from_file_location("discord_config", config_path)
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)

        # Get the WEBHOOKS list
        if not hasattr(config_module, 'WEBHOOKS'):
            print_error("config.py must define a WEBHOOKS list")
            return []

        webhooks = config_module.WEBHOOKS
        return [WebhookConfig.from_dict(wh) for wh in webhooks]

    except ImportError as e:
        print_error(f"Failed to import config: {e}")
        return []
    except KeyError as e:
        print_error(f"Missing required field in webhook config: {e}")
        return []
    except Exception as e:
        print_error(f"Failed to load webhook config: {e}")
        return []


def load_channels() -> dict[str, ChannelConfig]:
    """
    Load channel configurations from config.py file.

    Returns:
        Dictionary mapping channel name to ChannelConfig
    """
    try:
        import importlib.util
        config_path = get_config_path()

        if not config_path.exists():
            return {}

        # Load the config module
        spec = importlib.util.spec_from_file_location("discord_config", config_path)
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)

        # Get the CHANNELS dict
        if not hasattr(config_module, 'CHANNELS'):
            print_error("config.py must define a CHANNELS dict")
            return {}

        channels_dict = config_module.CHANNELS
        return {
            name: ChannelConfig.from_dict(name, data)
            for name, data in channels_dict.items()
        }

    except Exception as e:
        print_error(f"Failed to load channels: {e}")
        return {}


def save_channel_version(channel_name: str, version_str: str):
    """
    Save the last posted version for a channel back to config.py file.

    Args:
        channel_name: Name of the channel
        version_str: Version string to save
    """
    try:
        config_path = get_config_path()

        if not config_path.exists():
            print_error("Config file not found, cannot save state")
            return

        # Read the current config file
        content = config_path.read_text()

        # Use regex to find and update the specific channel's last_posted_version
        import re

        # Pattern to match the channel block and its last_posted_version line
        pattern = rf'("{channel_name}":\s*\{{[^}}]*"last_posted_version":\s*)([^,\n]*)'

        def replacement(match):
            prefix = match.group(1)
            # Replace with the new version string
            return f'{prefix}"{version_str}"'

        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

        # Write back to file
        config_path.write_text(new_content)

    except Exception as e:
        print_error(f"Failed to save channel version: {e}")

# Constants
MAX_MESSAGE_LENGTH = 2000
LAST_POSTED_FILE = ".last_posted_version"
UPLOAD_STATE_FILE = ".upload_state.json"
POST_HISTORY_FILE = ".post_history.json"

# Deduplication: minimum seconds between posting the same version to same webhook
# This prevents duplicate posts when the script runs twice in quick succession
DEDUP_WINDOW_SECONDS = 300  # 5 minutes

# Discord webhook rate limit: 5 requests per 2 seconds
# We'll be conservative and use 4 requests per 2 seconds to be safe
RATE_LIMIT_REQUESTS = 4
RATE_LIMIT_PERIOD = 2.0  # seconds


class RateLimiter:
    """Simple rate limiter for Discord webhook requests"""

    def __init__(self, max_requests: int, time_period: float):
        """
        Args:
            max_requests: Maximum number of requests allowed in time_period
            time_period: Time period in seconds
        """
        self.max_requests = max_requests
        self.time_period = time_period
        self.request_times: List[float] = []

    def wait_if_needed(self):
        """Wait if necessary to comply with rate limits"""
        now = time.time()

        # Remove requests older than the time period
        self.request_times = [t for t in self.request_times if now - t < self.time_period]

        # If we've hit the limit, wait until the oldest request expires
        if len(self.request_times) >= self.max_requests:
            oldest = self.request_times[0]
            sleep_time = self.time_period - (now - oldest)
            if sleep_time > 0:
                print_info(f"Rate limit: waiting {sleep_time:.1f}s before next request...")
                time.sleep(sleep_time)
                # Clean up again after sleeping
                now = time.time()
                self.request_times = [t for t in self.request_times if now - t < self.time_period]

        # Record this request
        self.request_times.append(time.time())


def get_project_root() -> Path:
    """Find the project root directory"""
    current = Path.cwd()
    while current != current.parent:
        # Check for various archive structures
        if (current / "archive" / "changelog").exists():
            return current
        if (current / "archive" / "claude-code" / "changelog").exists():
            return current
        if (current / "tools" / "post.py").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find project root")


def load_upload_state(project_root: Path, project_name: Optional[str] = None) -> dict:
    """Load the upload state from JSON file"""
    if project_name:
        state_file = project_root / f".upload_state_{project_name}.json"
    else:
        state_file = project_root / UPLOAD_STATE_FILE
    if not state_file.exists():
        return {}

    try:
        return json.loads(state_file.read_text())
    except Exception as e:
        print_warning(f"Could not load upload state: {e}")
        return {}


def save_upload_state(project_root: Path, state: dict, project_name: Optional[str] = None):
    """Save the upload state to JSON file"""
    if project_name:
        state_file = project_root / f".upload_state_{project_name}.json"
    else:
        state_file = project_root / UPLOAD_STATE_FILE
    try:
        temporary = state_file.with_suffix('.tmp')
        temporary.write_text(json.dumps(state, indent=2) + "\n")
        temporary.replace(state_file)
    except Exception as e:
        print_error(f"Could not save upload state: {e}")
        raise


def get_version_state(state: dict, version_str: str) -> Optional[dict]:
    """Get the upload state for a specific version"""
    return state.get(version_str)


def mark_version_complete(state: dict, version_str: str):
    """Mark a version as completely uploaded and remove from state"""
    if version_str in state:
        del state[version_str]


def update_version_state(state: dict, version_str: str, thread_id: str, chunks_posted: int, total_chunks: int):
    """Update the upload state for a version"""
    state[version_str] = {
        "thread_id": thread_id,
        "chunks_posted": chunks_posted,
        "total_chunks": total_chunks
    }


# Post history tracking for deduplication
def load_post_history(project_root: Path) -> dict:
    """
    Load the post history from JSON file.
    Structure: {webhook_name: {version_str: timestamp}}
    """
    history_file = project_root / POST_HISTORY_FILE
    if not history_file.exists():
        return {}
    try:
        return json.loads(history_file.read_text())
    except Exception as e:
        print_warning(f"Could not load post history: {e}")
        return {}


def save_post_history(project_root: Path, history: dict):
    """Save the post history to JSON file"""
    history_file = project_root / POST_HISTORY_FILE
    try:
        history_file.write_text(json.dumps(history, indent=2) + "\n")
    except Exception as e:
        print_error(f"Could not save post history: {e}")


def was_recently_posted(history: dict, webhook_name: str, version_str: str) -> bool:
    """
    Check if a version was recently posted to a webhook (within DEDUP_WINDOW_SECONDS).
    Returns True if the version should be skipped to avoid duplicates.
    """
    if webhook_name not in history:
        return False
    if version_str not in history[webhook_name]:
        return False

    posted_time = history[webhook_name][version_str]
    elapsed = time.time() - posted_time
    return elapsed < DEDUP_WINDOW_SECONDS


def record_post(history: dict, webhook_name: str, version_str: str):
    """Record that a version was posted to a webhook"""
    if webhook_name not in history:
        history[webhook_name] = {}
    history[webhook_name][version_str] = time.time()


def cleanup_old_history(history: dict, max_age_seconds: int = 86400):
    """Remove entries older than max_age_seconds (default: 24 hours)"""
    now = time.time()
    for webhook_name in list(history.keys()):
        webhook_history = history[webhook_name]
        for version_str in list(webhook_history.keys()):
            if now - webhook_history[version_str] > max_age_seconds:
                del webhook_history[version_str]
        if not webhook_history:
            del history[webhook_name]


def extract_version_from_filename(filename: str) -> Optional[str]:
    """Extract version string from changelog filename"""
    match = re.match(r"changelog-v?(.+)\.md$", filename)
    return match.group(1) if match else None


def extract_version_from_path(path: Path) -> Optional[str]:
    """Extract version string from changelog file path"""
    return extract_version_from_filename(path.name)


def get_all_changelogs(changelog_dir: Path) -> List[Tuple[version.Version, Path]]:
    """Get all changelog files sorted by version"""
    changelogs = []
    for file_path in changelog_dir.glob("changelog-*.md"):
        ver_str = extract_version_from_path(file_path)
        if ver_str:
            try:
                ver = version.parse(ver_str)
                changelogs.append((ver, file_path))
            except Exception as e:
                print_warning(f"Could not parse version from {file_path.name}: {e}")

    changelogs.sort(key=lambda x: x[0])
    return changelogs


def get_last_posted_version(project_root: Path, project_name: Optional[str] = None) -> Optional[version.Version]:
    """
    Read the last posted version from tracking file.

    NOTE: This is used by sync.py for single-project automation.
    For multi-channel posting via post.py, use channel.last_posted_version from config.py instead.
    """
    if project_name:
        last_posted_file = project_root / f".last_posted_version_{project_name}"
    else:
        last_posted_file = project_root / LAST_POSTED_FILE
    if not last_posted_file.exists():
        return None

    try:
        ver_str = last_posted_file.read_text().strip()
        return version.parse(ver_str)
    except Exception as e:
        print_warning(f"Could not read last posted version: {e}")
        return None


def save_last_posted_version(project_root: Path, ver: version.Version, project_name: Optional[str] = None):
    """
    Save the last posted version to tracking file.

    NOTE: This is used by sync.py for single-project automation.
    For multi-channel posting via post.py, use save_channel_version() instead.
    """
    if project_name:
        last_posted_file = project_root / f".last_posted_version_{project_name}"
    else:
        last_posted_file = project_root / LAST_POSTED_FILE
    last_posted_file.write_text(str(ver) + "\n")


TRAILER_START_RE = re.compile(r'^Generated (?:by `harness-investigations@|with:$)')


def subtext_trailer(content: str) -> str:
    """Render the generation trailer as Discord subtext (``-# `` lines).

    The trailer is metadata, so it should not compete with the changelog
    body. The archived Markdown keeps plain lines; only the posted copy
    changes.
    """
    lines = content.rstrip('\n').split('\n')
    start = next((i for i in range(len(lines) - 1, -1, -1)
                  if TRAILER_START_RE.match(lines[i])), None)
    if start is None:
        return content
    for i in range(start, len(lines)):
        if lines[i].strip():
            lines[i] = '-# ' + lines[i]
    return '\n'.join(lines) + '\n'


def parse_changelog_sections(content: str) -> List[Tuple[str, str]]:
    """
    Parse a changelog into semantic sections.

    Returns a list of (section_type, content) tuples where section_type is:
    - 'title': The # heading
    - 'summary': ## Summary section
    - 'section': ## New Features, ## Improvements, etc.
    - 'feature': ### Feature Name subsection
    - 'content': Non-header content belonging to previous section
    """
    sections = []
    lines = content.split('\n')
    current_section = []
    current_type = 'content'

    for line in lines:
        # Check what type of line this is
        if line.startswith('# ') and not line.startswith('## '):
            # Title (# Changelog for version X.X.X)
            if current_section:
                sections.append((current_type, '\n'.join(current_section)))
            current_section = [line]
            current_type = 'title'
        elif line.startswith('## '):
            # Major section header
            if current_section:
                sections.append((current_type, '\n'.join(current_section)))
            current_section = [line]
            if 'Summary' in line:
                current_type = 'summary'
            else:
                current_type = 'section'
        elif line.startswith('### '):
            # Feature/subsection header
            if current_section:
                sections.append((current_type, '\n'.join(current_section)))
            current_section = [line]
            current_type = 'feature'
        elif line.strip() == '---':
            # Horizontal rule - end of feature, include with current section
            current_section.append(line)
            sections.append((current_type, '\n'.join(current_section)))
            current_section = []
            current_type = 'content'
        else:
            # Regular content line
            current_section.append(line)

    # Don't forget the last section
    if current_section:
        sections.append((current_type, '\n'.join(current_section)))

    return sections


def smart_chunk_changelog(content: str, max_length: int = MAX_MESSAGE_LENGTH) -> List[str]:
    """
    Split a changelog into chunks at logical boundaries.

    Strategy:
    1. Parse into semantic sections (title, summary, features, etc.)
    2. Keep title + summary together in first chunk
    3. Start new chunks at major section headers (## headers)
    4. Split features to keep chunks focused but not too small
    5. Combine small trailing sections (Bug Fixes, Notes)
    """
    sections = parse_changelog_sections(content)

    if not sections:
        return [content] if content else []

    # Filter out empty content sections
    sections = [(t, c) for t, c in sections if c.strip()]

    chunks = []
    current_chunk_parts = []
    current_length = 0

    def flush_chunk():
        nonlocal current_chunk_parts, current_length
        if current_chunk_parts:
            chunk_text = '\n'.join(current_chunk_parts).strip()
            if chunk_text:
                chunks.append(chunk_text)
        current_chunk_parts = []
        current_length = 0

    for i, (section_type, section_content) in enumerate(sections):
        section_length = len(section_content) + 1  # +1 for newline

        # If this single section is too long, we need to split it
        if section_length > max_length:
            flush_chunk()

            # Fall back to line-by-line splitting for this oversized section
            lines = section_content.split('\n')
            for line in lines:
                line_length = len(line) + 1
                if current_length + line_length > max_length:
                    flush_chunk()
                current_chunk_parts.append(line)
                current_length += line_length
            continue

        # Decide whether to start a new chunk based on section type and size
        should_break = False

        # Title always starts the first chunk (don't break before it)
        # Summary should stay with title if they fit together
        if section_type == 'title':
            should_break = False
        elif section_type == 'summary':
            # Keep summary with title if possible
            should_break = False
        elif section_type == 'section':
            # Major section headers (## New Features, ## Bug Fixes, etc.)
            # Break before them UNLESS the current chunk is small
            # This allows combining small trailing sections
            if current_chunk_parts and current_length > max_length * 0.25:
                should_break = True
        elif section_type == 'feature':
            # Features (### Feature Name)
            # Break if current chunk is getting large (>50% full)
            if current_length > max_length * 0.5:
                should_break = True

        # Always break if adding this would exceed the limit
        if current_length + section_length > max_length:
            should_break = True

        if should_break:
            flush_chunk()

        current_chunk_parts.append(section_content)
        current_length += section_length

    # Flush any remaining content
    flush_chunk()

    # Post-process: merge very small trailing chunks
    if len(chunks) > 1:
        merged_chunks = []
        i = 0
        while i < len(chunks):
            chunk = chunks[i]

            # If this is a small chunk and we can merge with next
            while (i + 1 < len(chunks) and
                   len(chunk) < max_length * 0.3 and
                   len(chunk) + len(chunks[i + 1]) + 2 <= max_length):
                chunk = chunk + '\n\n' + chunks[i + 1]
                i += 1

            merged_chunks.append(chunk)
            i += 1

        chunks = merged_chunks

    return chunks


def chunk_message(content: str, max_length: int = MAX_MESSAGE_LENGTH) -> List[str]:
    """
    Split message into chunks that fit within Discord's character limit.

    For changelogs (detected by '# Changelog' header), uses smart semantic splitting.
    For other content, falls back to simple line-based splitting.
    """
    if len(content) <= max_length:
        return [content]

    # Use smart chunking for changelogs
    if content.strip().startswith('# Changelog'):
        return smart_chunk_changelog(content, max_length)

    # Fall back to simple line-based splitting for non-changelogs
    chunks = []
    current_chunk = ""

    lines = content.split("\n")

    for line in lines:
        # If a single line is too long, we need to split it
        if len(line) > max_length:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""

            for i in range(0, len(line), max_length):
                chunks.append(line[i:i + max_length])
        else:
            if len(current_chunk) + len(line) + 1 > max_length:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                if current_chunk:
                    current_chunk += "\n" + line
                else:
                    current_chunk = line

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def post_to_discord(
    thread_name: str,
    content: str,
    rate_limiter: RateLimiter,
    version_str: str,
    upload_state: dict,
    project_root: Path,
    webhook_url: str,
    dry_run: bool = False,
    resume_thread_id: Optional[str] = None,
    resume_from_chunk: int = 0,
    project_name: Optional[str] = None
) -> Tuple[bool, Optional[str], int]:
    """
    Post a message to Discord webhook, creating a forum thread or resuming an existing one.

    Args:
        thread_name: The name of the forum thread to create
        content: The message content
        rate_limiter: Rate limiter to prevent hitting Discord's limits
        version_str: Version string for tracking
        upload_state: Current upload state dictionary
        project_root: Project root path
        webhook_url: Discord webhook URL to post to
        dry_run: If True, don't actually post (just simulate)
        resume_thread_id: Thread ID to resume posting to (if resuming)
        resume_from_chunk: Chunk index to resume from (0-based)
        project_name: Optional project/webhook name for state tracking

    Returns:
        Tuple of (success, thread_id, chunks_posted)
    """
    chunks = chunk_message(content)
    total_chunks = len(chunks)

    if dry_run:
        if resume_from_chunk > 0:
            print_info(f"DRY RUN: Would resume thread '{thread_name}' from chunk {resume_from_chunk + 1}/{total_chunks}")
        else:
            print_info(f"DRY RUN: Would create thread '{thread_name}' with {total_chunks} message(s)")
        for i, chunk in enumerate(chunks, 1):
            print_info(f"  Message {i}: {len(chunk)} characters")
        return (True, "dry_run_thread_id", total_chunks)

    thread_id = resume_thread_id
    start_chunk = resume_from_chunk

    try:
        # If not resuming, create the thread with the first chunk
        if start_chunk == 0:
            rate_limiter.wait_if_needed()

            first_payload = {
                "content": chunks[0],
                "thread_name": thread_name
            }

            response = requests.post(
                f"{webhook_url}?wait=true",
                json=first_payload,
                headers={"Content-Type": "application/json"}, timeout=30,
            )
            response.raise_for_status()

            # Extract thread_id from response
            response_data = response.json()
            thread_id = response_data.get("channel_id")

            if not thread_id:
                print_error("Could not get thread_id from webhook response")
                return (False, None, 0)

            # Save state after first chunk
            update_version_state(upload_state, version_str, thread_id, 1, total_chunks)
            save_upload_state(project_root, upload_state, project_name)

            start_chunk = 1

        # Post remaining chunks
        for i in range(start_chunk, total_chunks):
            rate_limiter.wait_if_needed()

            chunk_payload = {"content": chunks[i]}
            chunk_response = requests.post(
                f"{webhook_url}?thread_id={thread_id}",
                json=chunk_payload,
                headers={"Content-Type": "application/json"}, timeout=30,
            )
            chunk_response.raise_for_status()

            # Update state after each chunk
            chunks_posted = i + 1
            update_version_state(upload_state, version_str, thread_id, chunks_posted, total_chunks)
            save_upload_state(project_root, upload_state, project_name)

        return (True, thread_id, total_chunks)

    except requests.exceptions.RequestException as e:
        print_error(f"Failed to post to Discord: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print_error(f"Response: {e.response.text}")
        # State has already been saved up to the last successful chunk
        chunks_posted = start_chunk if start_chunk > 0 else 0
        return (False, thread_id, chunks_posted)


def post_changelog(
    file_path: Path,
    rate_limiter: RateLimiter,
    upload_state: dict,
    project_root: Path,
    webhook_url: str,
    dry_run: bool = False,
    project_name: Optional[str] = None,
    post_history: Optional[dict] = None,
    channel_name: Optional[str] = None,
) -> bool:
    """
    Post a single changelog file to Discord, resuming if partially uploaded.

    Args:
        post_history: Optional dict for deduplication tracking. If provided,
                      will skip versions posted recently to the same webhook.
    """
    ver_str = extract_version_from_path(file_path)
    if not ver_str:
        print_error(f"Could not extract version from {file_path.name}")
        return False

    thread_name = f"v{ver_str}"
    state_key = f'{channel_name}:{ver_str}' if channel_name else ver_str
    if upload_state.get(state_key, {}).get('complete'):
        print_info(f"Already delivered {thread_name} to {project_name}")
        return True

    # Deduplication check: skip if recently posted to this webhook
    if post_history is not None and project_name and not dry_run:
        if was_recently_posted(post_history, project_name, state_key):
            print_warning(f"Skipping {thread_name} - already posted to {project_name} within {DEDUP_WINDOW_SECONDS}s")
            return True  # Return True to not break the posting loop

    try:
        content = subtext_trailer(file_path.read_text())
    except Exception as e:
        print_error(f"Could not read {file_path}: {e}")
        return False

    # Check if we're resuming a partial upload
    version_state = get_version_state(upload_state, state_key)
    resume_thread_id = None
    resume_from_chunk = 0

    if version_state:
        chunks_posted = version_state.get("chunks_posted", 0)
        total_chunks = version_state.get("total_chunks", 0)
        resume_thread_id = version_state.get("thread_id")

        if chunks_posted < total_chunks and resume_thread_id:
            print_info(f"Resuming {file_path.name} from chunk {chunks_posted + 1}/{total_chunks}...")
            resume_from_chunk = chunks_posted
        else:
            print_info(f"Posting {file_path.name} as '{thread_name}'...")
    else:
        print_info(f"Posting {file_path.name} as '{thread_name}'...")

    success, thread_id, chunks_posted = post_to_discord(
        thread_name,
        content,
        rate_limiter,
        state_key,
        upload_state,
        project_root,
        webhook_url,
        dry_run,
        resume_thread_id,
        resume_from_chunk,
        project_name
    )

    if success and not dry_run:
        # Retain a durable receipt so a later scheduler retry does not create
        # duplicate threads after the short deduplication window expires.
        upload_state[state_key] = {'complete': True, 'thread_id': thread_id}
        save_upload_state(project_root, upload_state, project_name)
        print_success(f"Posted {thread_name} ({chunks_posted} chunks)")

        # Record in post history for deduplication
        if post_history is not None and project_name and not dry_run:
            record_post(post_history, project_name, state_key)
            save_post_history(project_root, post_history)
    elif not success:
        print_error(f"Failed to complete {thread_name} (posted {chunks_posted} chunks)")

    return success


def parse_version_arg(arg: str, changelog_dir: Path) -> Optional[Path]:
    """Parse a version argument (either a file path or version string)"""
    # Check if it's a file path
    path = Path(arg)
    if path.exists() and path.is_file():
        return path

    # Try to interpret as version string
    # Remove 'v' prefix if present
    ver_str = arg[1:] if arg.startswith('v') else arg

    # Try to find the corresponding changelog file
    changelog_file = changelog_dir / f"changelog-v{ver_str}.md"
    if changelog_file.exists():
        return changelog_file

    return None


def get_webhook_configs(all_configs: List[WebhookConfig], discord_names: Optional[List[str]] = None) -> List[WebhookConfig]:
    """
    Get webhook configurations to use.

    Args:
        all_configs: All available webhook configurations
        discord_names: If provided, only return webhooks with these names

    Returns:
        List of WebhookConfig objects
    """
    if discord_names:
        configs = [wh for wh in all_configs if wh.name in discord_names]
        # Check for invalid names
        found_names = {wh.name for wh in configs}
        invalid_names = set(discord_names) - found_names
        if invalid_names:
            print_error(f"Unknown Discord server(s): {', '.join(invalid_names)}")
            available = ', '.join(wh.name for wh in all_configs)
            print_info(f"Available Discord servers: {available}")
        return configs
    return all_configs


def filter_changelogs_by_version_range(
    changelogs: List[Tuple[version.Version, Path]],
    from_version: Optional[str] = None,
    to_version: Optional[str] = None
) -> List[Tuple[version.Version, Path]]:
    """
    Filter changelogs based on CLI version range.

    Args:
        changelogs: List of (version, path) tuples
        from_version: Optional minimum version (CLI)
        to_version: Optional maximum version (CLI)

    Returns:
        Filtered list of changelogs
    """
    if not from_version and not to_version:
        return changelogs

    filtered = []

    # Parse CLI version constraints
    min_ver = version.parse(from_version) if from_version else None
    max_ver = version.parse(to_version) if to_version else None

    for ver, path in changelogs:
        # Check minimum version
        if min_ver and ver < min_ver:
            continue

        # Check maximum version
        if max_ver and ver > max_ver:
            continue

        filtered.append((ver, path))

    return filtered


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Post Claude Code changelogs to Discord forum channel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Configuration:
  Configure Discord servers in tools/config.py (see config.py.example)
  URLs are stored directly in config.py (gitignored)

Examples:
  # Post all new changelogs to all configured Discord servers (all channels)
  %(prog)s --new

  # Post all new changelogs for a specific channel only
  %(prog)s --new --project claude-code

  # Post to specific Discord server only (all its subscribed channels)
  %(prog)s --new --discord context-lobotomy

  # Post to multiple specific Discord servers
  %(prog)s --new --discord context-lobotomy --discord volvox

  # Post a version range to specific Discord server (e.g., catch up a new server)
  %(prog)s --all --discord volvox --from-version 2.1.0 --to-version 2.1.15

  # Post specific versions to all Discord servers (all channels)
  %(prog)s v1.0.67 v1.0.68

  # Post only codex changelogs to servers subscribed to codex
  %(prog)s --new --project codex

  # Dry run (don't actually post)
  %(prog)s --dry-run --new
"""
    )

    parser.add_argument(
        "versions",
        nargs="*",
        help="Changelog files or version numbers to post (e.g., 'v1.0.67' or 'archive/changelog/changelog-v1.0.67.md')"
    )

    parser.add_argument(
        "--new",
        action="store_true",
        help="Post all changelogs newer than the last posted version"
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Post all changelogs (use with caution!)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate posting without actually sending to Discord"
    )

    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output"
    )

    parser.add_argument(
        "--discord",
        action="append",
        dest="discord",
        metavar="NAME",
        help="Post to specific Discord server(s) by name (can be used multiple times). If not specified, posts to all configured Discord servers."
    )

    parser.add_argument(
        "--from-version",
        metavar="VERSION",
        help="Post versions from this version onwards (inclusive)"
    )

    parser.add_argument(
        "--to-version",
        metavar="VERSION",
        help="Post versions up to this version (inclusive)"
    )

    parser.add_argument(
        "--project",
        metavar="CHANNEL",
        help="Filter to specific channel (e.g., claude-code, codex). Only posts for this channel across all subscribed servers."
    )

    args = parser.parse_args()

    if args.no_color or not sys.stdout.isatty():
        Colors.disable()

    # Find project root
    try:
        project_root = get_project_root()
    except RuntimeError as e:
        print_error(str(e))
        return 1

    # Load Discord server configurations from file
    all_webhook_configs = load_webhook_configs()
    if not all_webhook_configs:
        print_error("No Discord server configurations found")
        return 1

    # Get webhook configurations to use
    webhook_configs = get_webhook_configs(all_webhook_configs, args.discord)
    if not webhook_configs:
        print_error("No valid Discord servers specified")
        return 1

    # Filter by project/channel if specified
    if args.project:
        # Filter webhooks to only include those subscribed to this project
        webhook_configs = [wh for wh in webhook_configs if args.project in wh.channels]
        if not webhook_configs:
            print_error(f"No Discord servers configured for channel: {args.project}")
            # Collect all unique channels
            all_channels = set()
            for wh in all_webhook_configs:
                all_channels.update(wh.channels)
            print_info(f"Available channels: {', '.join(sorted(all_channels))}")
            return 1

    # Load channel configurations
    channels = load_channels()
    if not channels:
        print_error("No channels configured")
        return 1

    # Seed per-webhook cursors together before any delivery advances the legacy
    # shared channel cursor. A failure on one subscriber must not skip its work
    # because another subscriber already received a newer version.
    if not args.dry_run and (args.all or args.new or args.versions):
        for webhook in all_webhook_configs:
            state = load_upload_state(project_root, webhook.name)
            cursors = state.setdefault('_channel_cursors', {})
            for channel_name in webhook.channels:
                if channel_name in channels:
                    cursors.setdefault(channel_name, channels[channel_name].last_posted_version)
            save_upload_state(project_root, state, webhook.name)

    # Validate Discord webhook URLs are set
    missing_webhooks = []
    for wh in webhook_configs:
        if not wh.url:
            missing_webhooks.append(wh.name)

    if missing_webhooks:
        print_error("Missing Discord webhook URL(s) for:")
        for wh_name in missing_webhooks:
            print_error(f"  {wh_name}")
        return 1

    # Check that a posting mode was specified
    if not (args.all or args.new or args.versions):
        parser.print_help()
        return 0

    # Track overall success and statistics
    all_success = True
    total_posted = 0
    total_webhooks_processed = 0

    # Load and clean up post history for deduplication
    post_history = load_post_history(project_root)
    cleanup_old_history(post_history)

    # Process each Discord server
    for webhook_idx, webhook in enumerate(webhook_configs, 1):
        print_header(f"Discord Server {webhook_idx}/{len(webhook_configs)}: {webhook.name}")
        total_webhooks_processed += 1

        webhook_url = webhook.url

        # Load webhook-specific upload state for resume capability
        upload_state = load_upload_state(project_root, webhook.name)

        # Filter channels if --project specified
        channels_to_process = webhook.channels
        if args.project:
            channels_to_process = [ch for ch in webhook.channels if ch == args.project]

        if not channels_to_process:
            print_info(f"No matching channels for {webhook.name}")
            continue

        print_info(f"Channels: {', '.join(channels_to_process)}")

        # Create rate limiter for this webhook (shared across all channels)
        rate_limiter = RateLimiter(RATE_LIMIT_REQUESTS, RATE_LIMIT_PERIOD)

        # Process each channel this webhook subscribes to
        for channel_name in channels_to_process:
            print_header(f"  Channel: {channel_name}")

            # Get channel configuration
            if channel_name not in channels:
                print_error(f"Unknown channel: {channel_name}")
                print_info(f"Available channels: {', '.join(channels.keys())}")
                all_success = False
                continue

            channel = channels[channel_name]
            changelog_dir = project_root / channel.directory

            if not changelog_dir.exists():
                print_warning(f"Changelog directory not found: {changelog_dir}")
                continue

            # Determine which changelogs to consider (before webhook-specific filtering)
            base_changelogs: List[Tuple[version.Version, Path]] = []

            if args.all:
                # Post all changelogs
                base_changelogs = get_all_changelogs(changelog_dir)

            elif args.new:
                # Post changelogs newer than last posted (will be filtered per webhook)
                base_changelogs = get_all_changelogs(changelog_dir)

            elif args.versions:
                # Post specific versions
                for ver_arg in args.versions:
                    file_path = parse_version_arg(ver_arg, changelog_dir)
                    if file_path:
                        ver_str = extract_version_from_path(file_path)
                        if ver_str:
                            try:
                                ver = version.parse(ver_str)
                                base_changelogs.append((ver, file_path))
                            except Exception as e:
                                print_error(f"Could not parse version from {file_path}: {e}")
                    else:
                        print_error(f"Could not find changelog for: {ver_arg}")

            else:
                # Should not reach here due to earlier checks
                continue

            if not base_changelogs:
                print_info(f"No changelogs found for {channel_name}")
                continue

            # Sort by version
            base_changelogs.sort(key=lambda x: x[0])

            # Determine changelogs for this channel
            if args.new:
                # Filter based on last posted version for this channel
                last_posted_str = upload_state.get('_channel_cursors', {}).get(
                    channel_name, channel.last_posted_version)
                if last_posted_str is None:
                    print_info(f"No last posted version for {channel_name}, will post all (within range)")
                    channel_changelogs = base_changelogs
                else:
                    try:
                        last_posted = version.parse(last_posted_str)
                        print_info(f"Last posted version for {channel_name}: v{last_posted}")
                        channel_changelogs = [(v, p) for v, p in base_changelogs if v > last_posted]
                    except Exception as e:
                        print_warning(f"Could not parse last posted version '{last_posted_str}': {e}")
                        channel_changelogs = base_changelogs
            else:
                channel_changelogs = base_changelogs

            # Apply version range filters
            channel_changelogs = filter_changelogs_by_version_range(
                channel_changelogs,
                args.from_version,
                args.to_version
            )

            if not channel_changelogs:
                print_info(f"No changelogs to post for {channel_name}")
                continue

            print_info(f"Will post {len(channel_changelogs)} {channel_name} changelog(s)")

            # Post each changelog
            posted_count = 0
            last_posted_ver = None

            for ver, file_path in channel_changelogs:
                if post_changelog(
                    file_path,
                    rate_limiter,
                    upload_state,
                    project_root,
                    webhook_url,
                    dry_run=args.dry_run,
                    project_name=webhook.name,
                    post_history=post_history,
                    channel_name=channel_name,
                ):
                    posted_count += 1
                    total_posted += 1
                    last_posted_ver = ver
                else:
                    print_error(f"Failed to post {file_path.name} to {webhook.name}, stopping this channel")
                    all_success = False
                    break

            # Update last posted version for this channel
            if last_posted_ver and not args.dry_run:
                cursors = upload_state.setdefault('_channel_cursors', {})
                prior = cursors.get(channel_name)
                if prior:
                    last_posted_ver = max(last_posted_ver, version.parse(prior))
                cursors[channel_name] = str(last_posted_ver)
                save_upload_state(project_root, upload_state, webhook.name)
                legacy = channel.last_posted_version
                save_channel_version(channel_name, str(max(
                    last_posted_ver, version.parse(legacy)) if legacy else last_posted_ver))
                print_success(f"Updated last posted version for {channel_name} to v{last_posted_ver}")

            if posted_count > 0:
                print_success(f"Posted {posted_count} {channel_name} changelog(s) to {webhook.name}")

    print_header("Summary")
    print_success(f"Posted {total_posted} total changelog(s) across {total_webhooks_processed} Discord server(s)")

    return 0 if all_success else 1


if __name__ == "__main__":
    sys.exit(main())
