#!/usr/bin/env python3
"""Extract the CLI JS bundle from a Bun-compiled claude binary.

Starting with @anthropic-ai/claude-code v2.1.113, the npm package is a thin
wrapper and the real CLI ships as a Bun-compiled executable in platform
sibling packages (@anthropic-ai/claude-code-linux-x64 etc.). The binary is
an ELF with a dedicated `.bun` section. Older releases hold a single
pre-bundled CJS module wrapped in:

    (function(exports, require, module, __filename, __dirname) { ... })

Split-module releases use a compiled module table instead. Their original
sources are retained and combined with esbuild for analysis, without execution.

This module reads the ELF section directly (no objcopy dependency) and, for
older single-wrapper releases, shells out to `node -e` with acorn's tokenizer to find the matched closing
paren of the top-level expression. Acorn is required because minified
bundles contain regex literals that fool a naive brace counter.

Usage as CLI:
    python bun_extract.py <claude-binary> <output.js>
"""
from __future__ import annotations

import json
import struct
import subprocess
import sys
from pathlib import Path

BUN_SECTION = ".bun"
WRAPPER_MARKER = b"(function(exports, require, module, __filename, __dirname)"

# Acorn tokenizer: reads JS from stdin, prints the byte offset where the
# outermost `(` closes. Project's node_modules/acorn is found via cwd.
_NODE_TOKENIZER = r"""
const acorn = require('acorn');
const src = require('fs').readFileSync(0, 'utf8');
const toks = acorn.tokenizer(src, { ecmaVersion: 'latest', sourceType: 'script' });
let depth = 0, end = 0;
for (const t of toks) {
  if (t.type.label === '(') depth++;
  else if (t.type.label === ')') {
    if (--depth === 0) { end = t.end; break; }
  }
}
process.stdout.write(String(Buffer.byteLength(src.slice(0, end), 'utf8')));
"""


def find_bun_section(binary: bytes) -> bytes:
    """Return the contents of the ELF64 `.bun` section."""
    if len(binary) < 64 or binary[:4] != b"\x7fELF":
        raise ValueError("not an ELF binary")
    if binary[4] != 2:
        raise ValueError("only ELF64 is supported (claude binaries are 64-bit)")
    if binary[5] != 1:
        raise ValueError("only little-endian ELF is supported")
    e_shoff = struct.unpack_from("<Q", binary, 0x28)[0]
    e_shentsize = struct.unpack_from("<H", binary, 0x3A)[0]
    e_shnum = struct.unpack_from("<H", binary, 0x3C)[0]
    e_shstrndx = struct.unpack_from("<H", binary, 0x3E)[0]

    strtab_sh = e_shoff + e_shstrndx * e_shentsize
    strtab_off = struct.unpack_from("<Q", binary, strtab_sh + 0x18)[0]
    strtab_sz = struct.unpack_from("<Q", binary, strtab_sh + 0x20)[0]
    strtab = binary[strtab_off : strtab_off + strtab_sz]

    for i in range(e_shnum):
        sh = e_shoff + i * e_shentsize
        name_off = struct.unpack_from("<I", binary, sh)[0]
        name_end = strtab.index(b"\0", name_off)
        if strtab[name_off:name_end].decode("latin-1") == BUN_SECTION:
            off = struct.unpack_from("<Q", binary, sh + 0x18)[0]
            sz = struct.unpack_from("<Q", binary, sh + 0x20)[0]
            return binary[off : off + sz]
    raise RuntimeError(f"no {BUN_SECTION!r} section found in ELF")


def read_module_graph(section: bytes) -> dict[str, str]:
    """Read source ranges from Bun's compiled module table, never bytecode.

    Layout: an eight-byte section length, payload, 32-byte Offsets, trailer.
    CompiledModuleGraphFile has six StringPointers and four enum bytes in the
    split-module binaries (52 bytes). See Bun's StandaloneModuleGraph source:
    https://github.com/oven-sh/bun/blob/main/src/standalone_graph/StandaloneModuleGraph.rs
    Unknown layouts fail closed instead of archiving a partial JS snippet.
    """
    trailer = b"\n---- Bun! ----\n"
    if len(section) < 56 or not section.endswith(trailer):
        raise RuntimeError("missing Bun module graph trailer")
    size = struct.unpack_from('<Q', section)[0]
    if size != len(section) - 8:
        raise RuntimeError("invalid Bun section length")
    payload = section[8:]
    footer = len(payload) - len(trailer) - 32
    byte_count, table, table_size, entry, _, _, _ = struct.unpack_from('<QIIIIII', payload, footer)
    if byte_count != footer or table_size % 52 or table + table_size > footer:
        raise RuntimeError("unsupported or invalid Bun module table")
    if entry >= table_size // 52:
        raise RuntimeError("invalid Bun entry point")

    def read_range(offset: int, length: int) -> bytes:
        if offset + length > table:
            raise RuntimeError("Bun source range is outside the payload")
        return payload[offset:offset + length]

    modules = {}
    for row in range(table, table + table_size, 52):
        name_at, name_len, source_at, source_len = struct.unpack_from('<IIII', payload, row)
        encoding, _, module_format, _ = struct.unpack_from('<BBBB', payload, row + 48)
        name = read_range(name_at, name_len).decode('utf-8').rstrip('\0')
        if not name.startswith('/$bunfs/root/') or '\0' in name:
            raise RuntimeError("unsupported Bun module path")
        if module_format not in (1, 2):
            continue
        if encoding not in (1, 2):
            raise RuntimeError(f"unsupported JavaScript encoding for {name}")
        source = read_range(source_at, source_len)
        if not source or b'\0' in source or name in modules:
            raise RuntimeError(f"missing or invalid source for {name}")
        # Bun's latin1 enum labels raw source bytes; these bundles carry UTF-8.
        modules[name] = source.decode('utf-8')
    if not modules:
        raise RuntimeError("Bun module table contains no JavaScript sources")
    return modules


def rebundle_modules(modules: dict[str, str], project_root: Path) -> bytes:
    result = subprocess.run(
        ['node', str(project_root / 'tools' / 'rebundle_bun.js')],
        input=json.dumps(modules).encode('utf-8'), capture_output=True,
        cwd=project_root, timeout=180, check=False,
    )
    if result.returncode:
        raise RuntimeError(f"Bun source rebundling failed: {result.stderr.decode(errors='replace')[-2000:]}")
    return result.stdout


def find_js_end(js_chunk: bytes, project_root: Path) -> int:
    """Return the byte length of the outermost (function(...)) in `js_chunk`."""
    result = subprocess.run(
        ["node", "-e", _NODE_TOKENIZER],
        input=js_chunk,
        capture_output=True,
        cwd=str(project_root),
        check=True,
    )
    end = int(result.stdout.decode().strip() or "0")
    if end <= 0:
        raise RuntimeError("acorn tokenizer did not find a balanced top-level (...)")
    return end


def extract_cli_js(binary_path: Path, project_root: Path, modules_path: Path | None = None) -> bytes:
    """Extract the CLI body from a Bun-compiled claude binary.

    The embedded JS is wrapped in (function(exports, require, module, __filename,
    __dirname) { ... }). We strip that wrapper so the returned bytes match the
    flat top-level structure of pre-v2.1.113 bundles — necessary because astdiff
    walks top-level declarations and would otherwise see a single
    FunctionExpression containing everything.
    """
    binary = binary_path.read_bytes()
    section = find_bun_section(binary)
    start = section.find(WRAPPER_MARKER)
    if start < 0:
        modules = read_module_graph(section)
        snapshot = rebundle_modules(modules, project_root)
        if modules_path is not None:
            modules_path.write_text(json.dumps(modules, ensure_ascii=False) + '\n')
        return snapshot
    # 30 MB window — current CLI is ~13 MB, leaving generous headroom.
    window = section[start : start + 30 * 1024 * 1024]
    end = find_js_end(window, project_root)
    wrapper = window[:end]

    # Strip the CJS envelope. Prefix is the WRAPPER_MARKER plus its opening `{`;
    # suffix is `})`. Be tolerant of whitespace the bundler might insert.
    body_start = wrapper.find(WRAPPER_MARKER) + len(WRAPPER_MARKER)
    while body_start < len(wrapper) and wrapper[body_start:body_start + 1] in (b" ", b"\t", b"\r", b"\n"):
        body_start += 1
    if wrapper[body_start:body_start + 1] != b"{":
        raise RuntimeError("expected `{` after wrapper marker")
    body_start += 1

    body_end = end - 1  # skip trailing `)`
    while body_end > body_start and wrapper[body_end - 1:body_end] in (b" ", b"\t", b"\r", b"\n"):
        body_end -= 1
    if wrapper[body_end - 1:body_end] != b"}":
        raise RuntimeError("expected `}` before closing `)`")
    body_end -= 1

    body = wrapper[body_start:body_end]
    return body.lstrip(b"\r\n")


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: bun_extract.py <claude-binary> <output.js>", file=sys.stderr)
        return 2
    binary_path = Path(argv[1])
    output_path = Path(argv[2])
    project_root = Path(__file__).resolve().parents[1]
    js = extract_cli_js(binary_path, project_root)
    output_path.write_bytes(js)
    print(f"wrote {len(js):,} bytes to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
