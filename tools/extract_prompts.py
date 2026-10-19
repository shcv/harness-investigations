#!/usr/bin/env python3
"""
Claude Code Prompt Extraction Tool

Extracts all prompt text from Claude Code source files, including:
- System prompts (core Claude behavior instructions)
- Agent definitions (subagent prompts and descriptions)
- Tool descriptions (what each tool does)
- Output styles (different response modes)
- Hook descriptions
- Error messages and user-facing text

Output Structure:
    prompts/v{version}/
    ├── index.md          # Summary with links to all prompts
    ├── index.json        # Machine-readable index
    ├── system/           # System prompts
    │   └── *.md
    ├── agent/            # Agent definitions
    │   └── *.md
    ├── tool/             # Tool descriptions
    │   └── *.md
    └── ...

Each .md file contains YAML frontmatter with extraction metadata,
followed by the raw prompt content.

Usage:
    python extract_prompts.py [--file PATH] [--output DIR] [--version VER]

Arguments:
    --file PATH     Path to Claude Code source file (default: latest pretty version)
    --output DIR    Output directory for extracted prompts (default: archive/claude-code/prompts)
    --version VER   Version string to use in output filenames
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime


@dataclass
class PromptEntry:
    """A single extracted prompt"""
    id: str                          # Unique identifier
    category: str                    # Category: system, agent, tool, style, message
    subcategory: str                 # More specific type
    name: str                        # Human-readable name
    content: str                     # The actual prompt text
    source_line: int                 # Line number in source
    source_var: Optional[str] = None # Variable name if applicable
    metadata: Dict[str, Any] = field(default_factory=dict)


class PromptExtractor:
    """Extracts prompts from Claude Code source files"""

    def __init__(self, source_path: str):
        self.source_path = source_path
        self.source_content = ""
        self.lines: List[str] = []
        self.prompts: List[PromptEntry] = []

    def load_source(self) -> bool:
        """Load the source file"""
        try:
            with open(self.source_path, 'r', encoding='utf-8') as f:
                self.source_content = f.read()
            self.lines = self.source_content.split('\n')
            return True
        except Exception as e:
            print(f"Error loading source file: {e}", file=sys.stderr)
            return False

    def extract_all(self) -> List[PromptEntry]:
        """Extract all prompts from the source"""
        if not self.source_content:
            if not self.load_source():
                return []

        # Run all extraction methods
        self._extract_system_prompts()
        self._extract_agent_definitions()
        self._extract_tool_descriptions()
        self._extract_output_styles()
        self._extract_user_messages()

        return self.prompts

    def _find_line_number(self, pos: int) -> int:
        """Convert character position to line number"""
        return self.source_content[:pos].count('\n') + 1

    def _extract_template_literal(self, start_pos: int) -> tuple[str, int]:
        """Extract a template literal starting at position (after the backtick)"""
        content = []
        pos = start_pos
        depth = 1  # Track nested template literals

        while pos < len(self.source_content) and depth > 0:
            char = self.source_content[pos]

            if char == '\\' and pos + 1 < len(self.source_content):
                # Escaped character
                content.append(char)
                content.append(self.source_content[pos + 1])
                pos += 2
                continue

            if char == '`':
                depth -= 1
                if depth > 0:
                    content.append(char)
                pos += 1
                continue

            if char == '$' and pos + 1 < len(self.source_content) and self.source_content[pos + 1] == '{':
                # Template expression - find matching brace
                brace_depth = 1
                expr_start = pos
                pos += 2
                while pos < len(self.source_content) and brace_depth > 0:
                    if self.source_content[pos] == '{':
                        brace_depth += 1
                    elif self.source_content[pos] == '}':
                        brace_depth -= 1
                    elif self.source_content[pos] == '`':
                        # Nested template literal
                        depth += 1
                    pos += 1
                content.append(self.source_content[expr_start:pos])
                continue

            content.append(char)
            pos += 1

        return ''.join(content), pos

    def _extract_system_prompts(self):
        """Extract main system prompts"""
        # Pattern for system prompt variable assignments
        patterns = [
            # Main system prompt identifiers
            (r'var\s+(\w+)\s*=\s*"(You are Claude Code[^"]*)"', 'system', 'identity'),
            (r'var\s+(\w+)\s*=\s*"(You are a Claude agent[^"]*)"', 'system', 'identity'),

            # Template literal system prompts
            (r'var\s+(\w+)\s*=\s*`(You are (?:Claude Code|a Claude agent|an interactive CLI)[^`]*)`', 'system', 'main'),
        ]

        for pattern, category, subcategory in patterns:
            for match in re.finditer(pattern, self.source_content, re.DOTALL):
                var_name = match.group(1)
                content = match.group(2)
                line_num = self._find_line_number(match.start())

                self.prompts.append(PromptEntry(
                    id=f"system-{var_name}",
                    category=category,
                    subcategory=subcategory,
                    name=f"System Prompt ({var_name})",
                    content=content,
                    source_line=line_num,
                    source_var=var_name
                ))

        # Find the main interactive CLI prompt builder
        main_prompt_pattern = r'You are an interactive CLI tool that helps users'
        for match in re.finditer(main_prompt_pattern, self.source_content):
            # Find the start of this template literal
            start = match.start()
            # Search backwards for the backtick
            backtick_pos = self.source_content.rfind('`', max(0, start - 50), start)
            if backtick_pos >= 0:
                content, end_pos = self._extract_template_literal(backtick_pos + 1)
                line_num = self._find_line_number(backtick_pos)

                # Only add if it's substantial
                if len(content) > 200:
                    prompt_id = f"system-main-{line_num}"
                    # Check if we already have this
                    if not any(p.id == prompt_id for p in self.prompts):
                        self.prompts.append(PromptEntry(
                            id=prompt_id,
                            category='system',
                            subcategory='main',
                            name='Main Interactive CLI Prompt',
                            content=content,
                            source_line=line_num
                        ))

    def _extract_agent_definitions(self):
        """Extract agent definitions (subagents)"""
        # Pattern for agent objects - handles both string literals and variable references
        agent_patterns = [
            # Direct string value: agentType: "name"
            r'\{\s*agentType:\s*"([^"]+)"\s*,\s*whenToUse:\s*["`]([^"`]+)["`]',
            # Variable reference followed by whenToUse
            r'\{\s*agentType:\s*(\w+)\s*,\s*whenToUse:\s*["`]([^"`]+)["`]',
        ]

        seen_agents = set()
        for pattern in agent_patterns:
            for match in re.finditer(pattern, self.source_content):
                agent_type = match.group(1)
                when_to_use = match.group(2)
                line_num = self._find_line_number(match.start())

                # Skip duplicates
                if agent_type in seen_agents:
                    continue
                seen_agents.add(agent_type)

                # Try to find the getSystemPrompt for this agent
                system_prompt = self._find_agent_system_prompt(match.start())

                self.prompts.append(PromptEntry(
                    id=f"agent-{agent_type}",
                    category='agent',
                    subcategory='definition',
                    name=f"Agent: {agent_type}",
                    content=when_to_use,
                    source_line=line_num,
                    metadata={
                        'agentType': agent_type,
                        'whenToUse': when_to_use,
                        'systemPrompt': system_prompt
                    }
                ))

        # Also extract standalone agent system prompts
        # These are often assigned to variables before being used in agent definitions
        agent_prompt_patterns = [
            (r'(\w+)\s*=\s*`(You are a (?:file search|software architect|specialized investigator|status line setup|documentation)[^`]*)`', 'agent', 'system_prompt'),
            (r'(\w+)\s*=\s*`(You are an? \w+ (?:specialist|agent|guide) for Claude Code[^`]*)`', 'agent', 'system_prompt'),
            (r'(\w+)\s*=\s*`(You are Claude Code.*?official (?:documentation|guide|CLI)[^`]*)`', 'agent', 'system_prompt'),
        ]

        for pattern, category, subcategory in agent_prompt_patterns:
            for match in re.finditer(pattern, self.source_content, re.DOTALL):
                var_name = match.group(1)
                content = match.group(2)
                line_num = self._find_line_number(match.start())

                # Skip if already captured
                if any(p.source_var == var_name for p in self.prompts):
                    continue

                self.prompts.append(PromptEntry(
                    id=f"agent-prompt-{var_name}",
                    category=category,
                    subcategory=subcategory,
                    name=f"Agent System Prompt ({var_name})",
                    content=content,
                    source_line=line_num,
                    source_var=var_name
                ))

        # Extract the claude-code-guide agent which has a complex system prompt
        guide_pattern = r'(\w+)\s*=\s*`(You are Claude Code.*?official (?:CLI|documentation|guide)[^`]+documentation-based guidance\.)`'
        for match in re.finditer(guide_pattern, self.source_content, re.DOTALL):
            var_name = match.group(1)
            content = match.group(2)
            line_num = self._find_line_number(match.start())

            if not any(p.source_var == var_name for p in self.prompts):
                self.prompts.append(PromptEntry(
                    id=f"agent-prompt-{var_name}",
                    category='agent',
                    subcategory='system_prompt',
                    name=f"Agent System Prompt ({var_name})",
                    content=content,
                    source_line=line_num,
                    source_var=var_name
                ))

    def _find_agent_system_prompt(self, agent_start: int) -> Optional[str]:
        """Find the getSystemPrompt content for an agent definition"""
        # Look ahead for getSystemPrompt within a reasonable distance
        search_area = self.source_content[agent_start:agent_start + 5000]

        prompt_match = re.search(r'getSystemPrompt:\s*\(\)\s*=>\s*`([^`]+)`', search_area)
        if prompt_match:
            return prompt_match.group(1)

        # Try to find reference to another variable
        ref_match = re.search(r'getSystemPrompt:\s*\(\)\s*=>\s*(\w+)', search_area)
        if ref_match:
            return f"[Reference to: {ref_match.group(1)}]"

        return None

    def _extract_tool_descriptions(self):
        """Extract tool descriptions"""
        # First extract standalone tool description variables
        # These are the main tool descriptions stored in variables like OnQ, snQ, etc.
        tool_desc_var_patterns = [
            # Variable assignment with template literal containing tool-like description
            (r'(\w{2,5})\s*=\s*`(Reads a file from[^`]+)`', 'Read'),
            (r'(\w{2,5})\s*=\s*`(Writes (?:a file|content) to[^`]+)`', 'Write'),
            (r'(\w{2,5})\s*=\s*`(Use this tool to create and manage a structured task list[^`]+)`', 'TodoWrite'),
            (r'(\w{2,5})\s*=\s*`(Performs exact string replacements[^`]+)`', 'Edit'),
            (r'(\w{2,5})\s*=\s*`(Use this tool when you need to ask the user[^`]+)`', 'AskUserQuestion'),
            (r'(\w{2,5})\s*=\s*`(Completely replaces the contents of a specific cell[^`]+)`', 'NotebookEdit'),
            (r'(\w{2,5})\s*=\s*`(Retrieves output from a running or completed task[^`]+)`', 'TaskOutput'),
            (r'(\w{2,5})\s*=\s*`(Kills a running background[^`]+)`', 'KillShell'),
            (r'(\w{2,5})\s*=\s*`(Use this tool proactively when you.*implementation task[^`]+)`', 'EnterPlanMode'),
            (r'(\w{2,5})\s*=\s*`(Use this tool when you are in plan mode[^`]+)`', 'ExitPlanMode'),
            (r'(\w{2,5})\s*=\s*`(Execute a skill[^`]+)`', 'Skill'),
            (r'(\w{2,5})\s*=\s*`(Execute a slash command[^`]+)`', 'SlashCommand'),
            # Different pattern: variable = `- Description...`
            (r'(\w{2,5})\s*=\s*`(- Fast file pattern matching tool[^`]+)`', 'Glob'),
            # Function returns
            (r'function\s+(\w+)\(\)\s*\{\s*return\s*`(A powerful search tool[^`]+)`', 'Grep'),
            (r'function\s+(\w+)\(\)\s*\{\s*return\s*`(Executes a given bash command[^`]+)`', 'Bash'),
            # Web tools
            (r'(\w{2,5})\s*=\s*`(- Fetches content from[^`]+)`', 'WebFetch'),
            (r'(\w{2,5})\s*=\s*`(- Allows Claude to search the web[^`]+)`', 'WebSearch'),
            # Task tool
            (r'(\w{2,5})\s*=\s*`(Launch a new agent[^`]+)`', 'Task'),
        ]

        captured_tools = set()
        for pattern, tool_name in tool_desc_var_patterns:
            for match in re.finditer(pattern, self.source_content, re.DOTALL):
                var_name = match.group(1)
                content = match.group(2)
                line_num = self._find_line_number(match.start())

                if tool_name in captured_tools:
                    continue
                captured_tools.add(tool_name)

                self.prompts.append(PromptEntry(
                    id=f"tool-{tool_name.lower()}",
                    category='tool',
                    subcategory='description',
                    name=f"Tool: {tool_name}",
                    content=content,
                    source_line=line_num,
                    source_var=var_name,
                    metadata={'toolName': tool_name}
                ))

        # Also look for description in object properties
        desc_pattern = r'description:\s*`([^`]{100,})`'
        for match in re.finditer(desc_pattern, self.source_content):
            content = match.group(1)
            line_num = self._find_line_number(match.start())

            # Skip if already captured by content
            if any(p.content == content for p in self.prompts):
                continue

            # Skip model selection descriptions
            if 'Opus' in content and 'Most capable' in content:
                continue

            # Infer tool name from content
            tool_name = self._infer_tool_name(content)

            # For hook-related descriptions, categorize differently
            if 'Exit code' in content or 'hook' in content.lower():
                self.prompts.append(PromptEntry(
                    id=f"hook-desc-{line_num}",
                    category='hook',
                    subcategory='description',
                    name="Hook Description",
                    content=content,
                    source_line=line_num
                ))
            else:
                self.prompts.append(PromptEntry(
                    id=f"tool-desc-{line_num}",
                    category='tool',
                    subcategory='description',
                    name=f"Tool Description ({tool_name or 'Unknown'})",
                    content=content,
                    source_line=line_num
                ))

    def _infer_tool_name(self, content: str) -> Optional[str]:
        """Try to infer tool name from description content"""
        patterns = [
            (r'Reads a file from', 'Read'),
            (r'Writes (?:a file|content) to', 'Write'),
            (r'Executes.*bash command', 'Bash'),
            (r'search tool', 'Grep'),
            (r'glob pattern', 'Glob'),
            (r'Launch.*agent', 'Task'),
            (r'todo list', 'TodoWrite'),
            (r'Fetches content from.*URL', 'WebFetch'),
            (r'search the web', 'WebSearch'),
        ]

        for pattern, name in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return name
        return None

    def _extract_output_styles(self):
        """Extract output style definitions"""
        # Pattern for output style objects
        style_pattern = r'\{\s*name:\s*"([^"]+)"[^}]*description:\s*"([^"]+)"[^}]*prompt:\s*`([^`]+)`'

        for match in re.finditer(style_pattern, self.source_content, re.DOTALL):
            name = match.group(1)
            description = match.group(2)
            prompt = match.group(3)
            line_num = self._find_line_number(match.start())

            self.prompts.append(PromptEntry(
                id=f"style-{name.lower().replace(' ', '-')}",
                category='style',
                subcategory='output_style',
                name=f"Output Style: {name}",
                content=prompt,
                source_line=line_num,
                metadata={
                    'styleName': name,
                    'description': description
                }
            ))

    def _extract_user_messages(self):
        """Extract user-facing messages and error texts"""
        # Patterns for common message types
        message_patterns = [
            # Error messages
            (r'throw\s+new\s+Error\(`([^`]{50,})`\)', 'message', 'error'),
            # Help text
            (r'helpText:\s*`([^`]{50,})`', 'message', 'help'),
            # Warnings
            (r'(?:warn|warning).*`([^`]{50,})`', 'message', 'warning'),
        ]

        for pattern, category, subcategory in message_patterns:
            for match in re.finditer(pattern, self.source_content, re.IGNORECASE):
                content = match.group(1)
                line_num = self._find_line_number(match.start())

                self.prompts.append(PromptEntry(
                    id=f"msg-{subcategory}-{line_num}",
                    category=category,
                    subcategory=subcategory,
                    name=f"{subcategory.title()} Message",
                    content=content,
                    source_line=line_num
                ))


def sanitize_filename(name: str) -> str:
    """Convert a prompt name to a safe filename"""
    # Remove special characters and convert to lowercase
    safe = re.sub(r'[^\w\s-]', '', name.lower())
    # Replace spaces with hyphens
    safe = re.sub(r'\s+', '-', safe)
    # Remove duplicate hyphens
    safe = re.sub(r'-+', '-', safe)
    # Trim hyphens from ends
    safe = safe.strip('-')
    return safe or 'unnamed'


def write_markdown_files(prompts: List[PromptEntry], output_path: Path, version: str):
    """Write prompts as individual markdown files with YAML frontmatter"""
    version_dir = output_path / f"v{version}"
    version_dir.mkdir(parents=True, exist_ok=True)

    # Group by category for organization
    by_category: Dict[str, List[PromptEntry]] = {}
    for prompt in prompts:
        if prompt.category not in by_category:
            by_category[prompt.category] = []
        by_category[prompt.category].append(prompt)

    files_written = 0

    for category, category_prompts in by_category.items():
        # Create category subdirectory
        cat_dir = version_dir / category
        cat_dir.mkdir(exist_ok=True)

        for prompt in category_prompts:
            # Generate filename from prompt ID or name
            filename = sanitize_filename(prompt.id) + '.md'
            filepath = cat_dir / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                # Write YAML frontmatter
                # All metadata here is from our extraction tool
                f.write("---\n")
                f.write(f"id: {prompt.id}\n")
                f.write(f"name: {prompt.name}\n")
                f.write(f"category: {prompt.category}\n")
                f.write(f"subcategory: {prompt.subcategory}\n")
                f.write(f"source_line: {prompt.source_line}\n")
                if prompt.source_var:
                    f.write(f"source_var: {prompt.source_var}\n")

                # Add original metadata under a separate key
                if prompt.metadata:
                    f.write("original_metadata:\n")
                    for key, value in prompt.metadata.items():
                        if isinstance(value, str):
                            # Escape quotes and handle multiline
                            if '\n' in value or '"' in value:
                                f.write(f"  {key}: |\n")
                                for line in value.split('\n'):
                                    f.write(f"    {line}\n")
                            else:
                                f.write(f"  {key}: \"{value}\"\n")
                        else:
                            f.write(f"  {key}: {value}\n")

                f.write("---\n\n")

                # Write the prompt content directly (no code blocks needed for .md)
                f.write(prompt.content)
                if not prompt.content.endswith('\n'):
                    f.write('\n')

            files_written += 1

    # Write an index file for this version
    index_file = version_dir / "index.md"
    with open(index_file, 'w', encoding='utf-8') as f:
        f.write("---\n")
        f.write(f"version: {version}\n")
        f.write(f"extracted_at: {datetime.now().isoformat()}\n")
        f.write(f"total_prompts: {len(prompts)}\n")
        f.write("---\n\n")
        f.write(f"# Claude Code Prompts - v{version}\n\n")
        f.write(f"Extracted: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("## Categories\n\n")

        for category in ['system', 'agent', 'tool', 'hook', 'style', 'message']:
            if category not in by_category:
                continue
            count = len(by_category[category])
            f.write(f"### {category.title()} ({count})\n\n")
            for prompt in by_category[category]:
                filename = sanitize_filename(prompt.id)
                f.write(f"- [{prompt.name}]({category}/{filename}.md)\n")
            f.write("\n")

    print(f"Written {files_written} prompt files to: {version_dir}/")
    return version_dir


def write_json_index(prompts: List[PromptEntry], output_path: Path, version: str):
    """Write a JSON index file for programmatic access"""
    version_dir = output_path / f"v{version}"
    version_dir.mkdir(parents=True, exist_ok=True)
    output_file = version_dir / "index.json"

    data = {
        'version': version,
        'extracted_at': datetime.now().isoformat(),
        'total_prompts': len(prompts),
        'categories': {},
        'prompts': []
    }

    # Group by category
    for prompt in prompts:
        if prompt.category not in data['categories']:
            data['categories'][prompt.category] = 0
        data['categories'][prompt.category] += 1

        prompt_data = asdict(prompt)
        prompt_data['file'] = f"{prompt.category}/{sanitize_filename(prompt.id)}.md"
        data['prompts'].append(prompt_data)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Written JSON index to: {output_file}")
    return output_file


def find_latest_version(archive_dir: Path) -> tuple[Optional[Path], Optional[str]]:
    """Find the latest prettified version in the archive"""
    pretty_dir = archive_dir / "claude-code" / "pretty"
    if not pretty_dir.exists():
        # Try old structure
        pretty_dir = archive_dir / "pretty"

    if not pretty_dir.exists():
        return None, None

    # Find all pretty-*.js files
    files = list(pretty_dir.glob("pretty-v*.js"))
    if not files:
        return None, None

    # Sort by version
    def get_version(p: Path) -> tuple:
        match = re.search(r'v(\d+)\.(\d+)\.(\d+)', p.name)
        if match:
            return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        return (0, 0, 0)

    files.sort(key=get_version, reverse=True)
    latest = files[0]

    # Extract version string
    version_match = re.search(r'v(\d+\.\d+\.\d+)', latest.name)
    version_str = version_match.group(1) if version_match else "unknown"

    return latest, version_str


def main():
    parser = argparse.ArgumentParser(
        description='Extract prompts from Claude Code source files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--file', '-f', type=str, help='Path to Claude Code source file')
    parser.add_argument('--output', '-o', type=str, help='Output directory')
    parser.add_argument('--format', type=str, choices=['json', 'org', 'both'],
                        default='both', help='Output format (default: both)')
    parser.add_argument('--version', '-v', type=str, help='Version string for output files')

    args = parser.parse_args()

    # Determine project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    archive_dir = project_root / "archive"

    # Determine source file
    if args.file:
        source_path = Path(args.file)
        if not source_path.exists():
            print(f"Error: Source file not found: {source_path}", file=sys.stderr)
            sys.exit(1)
        version_str = args.version or "custom"
    else:
        source_path, version_str = find_latest_version(archive_dir)
        if not source_path:
            print("Error: Could not find any prettified Claude Code files", file=sys.stderr)
            sys.exit(1)
        if args.version:
            version_str = args.version
        print(f"Using latest version: {source_path}")

    # Determine output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = archive_dir / "claude-code" / "prompts"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract prompts
    print(f"Extracting prompts from: {source_path}")
    extractor = PromptExtractor(str(source_path))
    prompts = extractor.extract_all()

    print(f"Found {len(prompts)} prompts")

    # Group by category for summary
    by_cat = {}
    for p in prompts:
        by_cat[p.category] = by_cat.get(p.category, 0) + 1
    for cat, count in sorted(by_cat.items()):
        print(f"  - {cat}: {count}")

    # Write output - individual markdown files organized by version/category
    write_markdown_files(prompts, output_dir, version_str)
    write_json_index(prompts, output_dir, version_str)

    print(f"\nDone! Output written to: {output_dir}/v{version_str}/")


if __name__ == '__main__':
    main()
