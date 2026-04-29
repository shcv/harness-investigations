#!/usr/bin/env python3
"""Extract the CLI JS bundle from a Bun-compiled claude binary.

Starting with @anthropic-ai/claude-code v2.1.113, the npm package is a thin
wrapper and the real CLI ships as a Bun-compiled executable in platform
sibling packages (@anthropic-ai/claude-code-linux-x64 etc.). The binary is
an ELF (or Mach-O/PE) with a dedicated `.bun` section holding a single
pre-bundled CJS module wrapped in:

    (function(exports, require, module, __filename, __dirname) { ... })

This module reads the ELF section directly (no objcopy dependency) and
shells out to `node -e` with acorn's tokenizer to find the matched closing
paren of the top-level expression. Acorn is required because minified
bundles contain regex literals that fool a naive brace counter.

Usage as CLI:
    python bun_extract.py <claude-binary> <output.js>
"""
from __future__ import annotations

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
process.stdout.write(String(end));
"""


def find_bun_section(binary: bytes) -> bytes:
    """Return the contents of the ELF64 `.bun` section."""
    if binary[:4] != b"\x7fELF":
        raise ValueError("not an ELF binary")
    if binary[4] != 2:
        raise ValueError("only ELF64 is supported (claude binaries are 64-bit)")
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


def extract_cli_js(binary_path: Path, project_root: Path) -> bytes:
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
        raise RuntimeError("CLI wrapper marker not found in .bun section")
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
