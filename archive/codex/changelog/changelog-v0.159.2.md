# Changelog for version 0.159.2

## Release Status

> **Not yet released:** `rust-v0.159.2` is present in Git, but no published GitHub Release was found at sync time. This may be an intermediate development snapshot or a release prepared ahead of publication.


## Summary

Compared with 0.159.1, this snapshot prevents unwanted Windows console windows during background operations, including Git commands, hooks, authentication helpers, diagnostics, and sandboxed command execution. These fixes apply automatically to the affected Windows execution paths and introduce no new CLI commands, configuration keys, or app-server methods.

## Release Status

The source tag `rust-v0.159.2` exists, but no published GitHub Release was found when the sync ran. This changelog describes an intermediate development snapshot; it does not indicate that binaries or release assets were published.

## Bug Fixes

- Background shell commands and execution helpers on Windows now suppress console-window creation. This covers shell-tool commands with redirected input/output, shell-environment capture, stdio exec-server startup, and the `taskkill` helper used for process cleanup.

  Code references: `spawn_child_async` in `codex-rs/core/src/spawn.rs`; `run_script_with_timeout` in `codex-rs/core/src/shell_snapshot.rs`; `stdio_command_process` in `codex-rs/exec-server/src/client_transport.rs`; `kill_windows_process_tree` in `codex-rs/exec-server/src/connection.rs`.

- Git and hook processes now remain console-free even when Windows Job Object creation or process assignment fails and Codex retries without containment. The fallback clears the suspended-start flag while retaining console suppression. Hook cleanup commands also suppress console creation.

  Code references: `JobObject::spawn_background` and `JobObject::prepare_suspended_spawn` in `codex-rs/utils/pty/src/win/job.rs`; `spawn_git_command` in `codex-rs/git-utils/src/git_process.rs`; `run_command`, `build_command`, and `ProcessTreeGuard::drop` in `codex-rs/hooks/src/engine/command_runner.rs`.

- Plugin and marketplace operations now suppress Windows console windows when launching Git or running `npm pack`. The same launch policy applies to hook commands constructed from argument lists.

  Code references: `PluginGitMode::command` in `codex-rs/core-plugins/src/git_policy.rs`; `run_git` in `codex-rs/core-plugins/src/marketplace_add/install.rs`; `pack_npm_package` in `codex-rs/core-plugins/src/npm_source.rs`; `command_from_argv` in `codex-rs/hooks/src/registry.rs`.

- External bearer-token commands and Amazon Bedrock credential-export commands now run without allocating a Windows console. Bedrock authentication refresh also suppresses console creation when standard input is not a terminal; terminal-based refresh continues to support interactive authentication.

  Code references: `run_provider_auth_command` in `codex-rs/login/src/auth/external_bearer.rs`; `AwsCredentialExport` in `codex-rs/model-provider/src/amazon_bedrock/credential_export.rs`; `AwsAuthRecovery` in `codex-rs/model-provider/src/amazon_bedrock/auth_refresh.rs`.

- Diagnostic subprocesses and conversation-history searches now avoid creating Windows console windows. This includes feedback doctor reports, Windows event-log queries, security-product inspection, and searches that invoke ripgrep.

  Code references: `doctor_command` in `codex-rs/app-server/src/request_processors/feedback_doctor_report.rs`; `query_channel` in `codex-rs/cli/src/doctor/desktop/windows_security.rs`; `product_command` in `codex-rs/cli/src/doctor/security.rs`; `ripgrep_rollout_paths` in `codex-rs/rollout/src/search.rs`.

- Windows sandbox execution now explicitly requests `ConsoleMode::NoWindow` for legacy non-TTY commands and captured-output commands. Sandbox setup refreshes, working-directory junction creation, and ripgrep scans for denied-read paths also suppress console creation.

  Code references: `spawn_legacy_process` in `codex-rs/windows-sandbox-rs/src/unified_exec/backends/legacy.rs`; `run_windows_sandbox_capture_with_filesystem_overrides` in `codex-rs/windows-sandbox-rs/src/lib.rs`; `run_setup_refresh_payload` in `codex-rs/windows-sandbox-rs/src/setup.rs`; `create_cwd_junction` in `codex-rs/windows-sandbox-rs/src/bin/command_runner/win/cwd_junction.rs`; `ripgrep_files` in `codex-rs/windows-sandbox-rs/src/deny_read_resolver.rs`.


Generated with:
- tool: `harness-investigations@9f6feb2-dirty`
- provider: `codex`
- model: `gpt-6-astra`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.159.2.diff` (raw diff)
- release status: `unreleased Git tag; no published GitHub Release found at sync time`
