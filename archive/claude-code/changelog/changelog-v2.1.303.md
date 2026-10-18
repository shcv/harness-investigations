# Changelog for version 2.1.303

## Summary

Version 2.1.303 hardens certificate trust handling compared with 2.1.302. It filters deny-listed root certificates, adds actionable warnings for affected custom CA bundles, and improves fallback behavior when system certificates cannot be loaded.

## Improvements


### Deny-list filtering for trusted certificates

Claude Code now filters certificates loaded through its CA loader before using them for TLS connections. The checks apply to bundled roots, system roots, and certificates supplied through the existing `NODE_EXTRA_CA_CERTS` environment variable.

Details:

- Checks certificates against four built-in certificate fingerprints and four corresponding public-key fingerprints.
- Also rejects certificates with matching public keys, even when the certificate fingerprint differs.
- Detects blocked certificates inside certain unreadable or nested PEM blocks.
- Attempts to preserve the remaining certificates by removing affected blocks. Entries that cannot be safely cleaned are discarded.
- Runs directly in the certificate-loading path, without a feature flag.

Evidence: Certificate and public-key fingerprint checks, followed by PEM filtering (search for `"Dropped blocked certificate"` and `"Dropped an unreadable block from"`). These checks are present in the original 2.1.303 module sources and absent from 2.1.302.


### Actionable warnings for affected custom CA bundles

When a blocked certificate appears in an unreadable block within a `NODE_EXTRA_CA_CERTS` file, Claude Code now explains whether it ignored that block or the entire file.

Usage:

```bash
NODE_EXTRA_CA_CERTS=/path/to/company-ca.pem claude --debug
```

Details:

- If an affected block can be removed while retaining usable certificates, the warning says the other certificates are still used.
- If the whole file is rejected because an unreadable blocked certificate remains, the warning recommends using `--debug` to record its SHA-256 fingerprint, then removing that certificate.
- Excessively nested blocked certificates produce a separate warning explaining that the file must be cleaned before its remaining certificates can be used.

Evidence: New console warnings (search for `"Claude Code ignored a block in the NODE_EXTRA_CA_CERTS file"`, `"Claude Code ignored all of the NODE_EXTRA_CA_CERTS file"`, and `"nested too deeply to cut out"`).

## Bug Fixes

- Fixed the system-only certificate-loading path returning early when the runtime lacks the system CA API. Claude Code now falls back to bundled roots and continues processing `NODE_EXTRA_CA_CERTS`. Previously, this path deferred to runtime defaults. Evidence: Search for `"CA certs: stores=system but system CA API unavailable, using bundled roots"`; 2.1.302 instead contains `"deferring to runtime"`.

- Added a filtered bundled-root fallback when no configured root entries survive certificate filtering. If bundled roots also yield no acceptable entries, Claude Code stops with an explicit instruction to update. Evidence: Search for `"No root certificates are left to trust: every root built into this runtime is on the CLI's deny list. Update Claude Code."`.

## Notes

`NODE_EXTRA_CA_CERTS` and `CLAUDE_CODE_CERT_STORE` already existed in 2.1.302. This release changes how their certificate inputs are processed. If a custom bundle triggers the new warnings, remove the identified blocked certificate or affected block and restart Claude Code.


Generated with:
- tool: `harness-investigations@b259592-dirty`
- provider: `codex`
- model: `gpt-6.1-sol`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.303.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.303.txt`
- source modules: `archive/claude-code/original/cli-v2.1.303.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
