# Changelog for version 2.1.278

## Summary

Compared with 2.1.277, this release expands the existing server-side auto-mode classifier to more API configurations and improves recovery when classification results are missing. It also adds classifier billing notices, an “Auto mode server” status indicator, and consistent propagation of classifier settings to background sessions.

## Improvements


### Server-side auto-mode classification enabled by default on more routes

Eligible third-party API configurations now attempt server-side classification by default. Previously, this path required explicitly enabling `CLAUDE_CODE_AUTO_MODE_SERVER`.

Details:

- Provider routing now includes Anthropic’s AWS and Google Cloud routes.
- Custom Anthropic-compatible endpoints and non-SSH Unix-socket connections use the path that supports local fallback.
- Existing authentication, provider, and auto-mode eligibility checks still apply.
- Disabling experimental betas normally disables this default, with an exception for host-managed providers.
- The existing environment variable remains an explicit override.

Usage:

```bash
# Disable server-side classification on routes governed by this override.
CLAUDE_CODE_AUTO_MODE_SERVER=0 claude --permission-mode auto
```

Evidence: Compare the initialization of `thirdPartyServerClassifierEnabled` in both versions, searching for `"CLAUDE_CODE_AUTO_MODE_SERVER"` and `"arbiterWithLocalFallback"`. The original modules confirm the change from default-off to conditional default-on.


### Billing notice when auto mode falls back to billed classification

Auto mode now explains when a session cannot use the updated server-side classifier and continues with separately billed classifier requests.

Details:

- The notice identifies a configured gateway hostname or a recognized gateway when possible.
- It explains that auto mode continues working and supplies a documentation address for gateway compatibility or support.
- Press Enter to continue; Escape interrupts the current operation.
- For gateway-specific notices, acknowledgement suppresses another notice for 24 hours.
- Eligibility checks exclude several subscription categories; the notice is controlled by `tengu_velvet_heron`, which defaults to enabled.
- Noninteractive runs can emit the notice to stderr. Verbose `stream-json` output emits a structured warning after initialization.

The notice describes a billing transition for eligible sessions; it does not establish that classifier requests are free for every configuration.

Evidence: Search for `"We're changing auto mode to no longer charge for classifier requests in Claude Code."`, `"autoModeClassifierBillingNoticeAcknowledgedAt"`, and `"tengu_velvet_heron"`. These additions are present in the original 2.1.278 modules and absent from 2.1.277.


### Auto-mode server status is visible

The status display now includes an “Auto mode server” row showing “Enabled” or “Disabled,” making the current classifier configuration easier to inspect.

Usage:

```text
/status
```

The indicator considers the current permission mode and server-classifier eligibility. It reports configuration state rather than guaranteeing that every subsequent request will return a server verdict.

Evidence: Search for `"Auto mode server"` and its `"Enabled"` / `"Disabled"` values. The row and its status-display integration are new in 2.1.278.

## Bug Fixes

- **Recover from missing or unsupported server classification.** When the first-party server-classifier path receives no classification result or an explicit unsupported response, auto mode can switch to local classification for the remainder of the session. This recovery is controlled by `"tengu_quiet_lantern"`, defaulting to enabled. Search for `"no safeguard_results"` and `"so auto mode classifies locally for the rest of this session"`.

- **Handle more failures on routes with local fallback.** Local classification now covers additional server-unavailable conditions, missing per-call results, and results no longer retained by the session. Truncated per-call classifications remain excluded from this fallback. Search for `"server_results_not_held"`, `"server_unavailable_"`, and `"truncated"` in the fallback decision code.

- **Preserve classifier controls in background sessions.** Background launch configuration now explicitly forwards `CLAUDE_CODE_AUTO_MODE_SERVER`, including a disabling value, and the experimental-beta opt-out. Search for `"CLAUDE_CODE_AUTO_MODE_SERVER"` and `"CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS"` in the background launch environment.

- **Explain unavailable retained verdicts more precisely.** A missing stored classification result now has its own explanation and retry guidance instead of being reported as a generic missing server result. Search for `"this session no longer holds the result for this action"`.

## In Development


### Conditional Sonnet refusal retry [In Development]

What: Extends the existing silent refusal-retry mechanism to certain Sonnet responses.

Status: Feature-flagged through server-provided model capability data; availability cannot be established from the shipped code alone.

Details:

- The new branch recognizes API refusal categories `"cyber"` and `"frontier_llm"`.
- It requires the Sonnet model’s `"convolute_arcades"` capability to be explicitly enabled.
- It selects the same model for the retry and checks that a refusal fallback has not already occurred.
- Existing routing checks still apply; there is no new user command.
- The API refusal category is now passed into the retry-selection callback.

Evidence: Compare the refusal-retry selector in both versions. Search for `"convolute_arcades"`, `"cyber"`, `"frontier_llm"`, and `"refusalFallbackSilentRearm"` in the original modules. The previous selector admitted only the existing Opus path.


Generated with:
- tool: `harness-investigations@4e00000-dirty`
- provider: `codex`
- model: `gpt-6-astra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.278.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.278.txt`
- source modules: `archive/claude-code/original/cli-v2.1.278.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
