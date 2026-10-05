# Changelog for version 0.160.1

## Summary

Version 0.160.1 fixes environment handling when Codex launches a stdio MCP server on a Windows remote executor, particularly when Codex itself runs on Unix. Compared with 0.160.0, this is the only substantive user-facing change in the Rust diff.

## Official Release Highlights


### Windows remote MCP servers retain essential environment variables

What: Remote stdio MCP launches now preserve the executor’s `SYSTEMROOT`, `TEMP`, and `TMP` variables when explicitly configured remote environment variables activate environment filtering. This matches the [published release notes](https://github.com/openai/codex/releases/tag/rust-v0.160.1).

Usage:

For an existing MCP server configured to run on a Windows remote executor, an environment entry such as this now retains the Windows startup variables automatically:

```toml
[mcp_servers.my_server]
# Keep your existing command and remote-executor configuration.
env_vars = [{ name = "REMOTE_TOKEN", source = "remote" }]
```

Details:

- In 0.160.0, the filter combined Codex’s platform-specific default environment names with explicitly requested remote names. When Codex ran on Unix, its defaults omitted these Windows variables.
- In 0.160.1, `SYSTEMROOT`, `TEMP`, and `TMP` are explicitly included alongside those defaults and requested names. Their values come from the remote executor’s environment.
- Preserving these values avoids stripping inputs needed for Windows runtime initialization and temporary-directory handling.
- Matching is case-insensitive, so `SYSTEMROOT` also preserves an executor variable spelled `SystemRoot`.
- Unrequested variables remain filtered out. The fix does not grant unrestricted environment inheritance.
- Existing configurations benefit automatically after upgrading. Remote environment configuration already existed; this release corrects its behavior.

Code references:

- `ExecutorStdioServerLauncher::remote_env_policy` in `codex-rs/rmcp-client/src/stdio_server_launcher.rs` adds `.chain(["SYSTEMROOT", "TEMP", "TMP"].iter())` to the filtered environment names.
- `DEFAULT_ENV_VARS` in `codex-rs/rmcp-client/src/utils.rs` supplies the platform-specific defaults that previously left a Unix-to-Windows launch without these names.
- `shell_environment_policy` in `codex-rs/exec-server/src/local_process.rs` applies case-insensitive matching to `include_only`.
- `McpServerEnvVar::is_remote_source` in `codex-rs/config/src/mcp_types.rs` identifies the existing `source = "remote"` configuration shown above.


Generated with:
- tool: `harness-investigations@899c6e9-dirty`
- provider: `codex`
- model: `gpt-6.1-sol`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.160.1.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.160.1.md`
