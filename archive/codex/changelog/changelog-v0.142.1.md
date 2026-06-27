# Changelog for version 0.142.1

## Official Release Highlights

Version 0.142.1 is a targeted patch that adds opt-in Windows system proxy support for authentication traffic. Windows users in corporate or managed network environments can now have Codex automatically discover and route through the system proxy — including PAC scripts, WPAD auto-detection, and static proxy entries — without manually mirroring proxy settings in environment variables.

## New Features


### Windows System Proxy Support

What: On Windows, Codex can now read the system proxy configuration and route outbound requests through it automatically. The implementation covers all Windows proxy discovery mechanisms: explicit PAC URL, WPAD auto-detection via DHCP and DNS, and static proxy entries with bypass rules.

Details:

- Codex calls the WinHTTP API (`WinHttpGetIEProxyConfigForCurrentUser`, `WinHttpGetProxyForUrl`) to read the current user's Internet Explorer / Windows proxy settings
- Discovery runs in order of priority: PAC URL → WPAD auto-detect → static proxy → direct
- PAC/WPAD: when a PAC URL is configured, Codex fetches and evaluates the script per-request to get the proxy decision. When auto-detect is enabled (and no PAC URL is set), Codex probes via DHCP and DNS-A (WPAD)
- Static proxy: reads the WinHTTP proxy list string, which supports per-scheme entries (`http=proxy:8080;https=secure-proxy:8443`) and bare host:port entries (`proxy.internal:8080`)
- Bypass rules: the proxy bypass list (`<local>`, `*.corp`, `auth.internal:443`) is evaluated before routing. `<local>` matches any hostname without a dot, matching Windows conventions
- Proxy string parsing handles PAC return values including `PROXY`, `DIRECT`, `HTTPS`, `SOCKS`, `SOCKS4`, `SOCKS5` — SOCKS schemes are recognised but fall through as unsupported (Codex does not tunnel SOCKS today)
- Wildcard matching in bypass and no-proxy lists supports `*` patterns and leading-dot suffix matching (`.openai.com` matches `auth.openai.com`)
- When no proxy is configured in IE settings and `WinHttpGetIEProxyConfigForCurrentUser` returns `ERROR_FILE_NOT_FOUND`, Codex falls back to attempting WPAD, matching WinHTTP's own fallback behaviour
- This feature is opt-in; the opt-in mechanism was introduced in the prior version. The 0.142.1 patch wires in the actual WinHTTP implementation that makes the opt-in meaningful on Windows

Code references:
- New `windows::resolve()` in `codex-rs/codex-client/src/outbound_proxy/windows.rs`
- `resolve_platform_system_proxy` in `codex-rs/codex-client/src/outbound_proxy.rs` (now `#[cfg(target_os = "windows")]` dispatches to `windows::resolve`)
- `parse_proxy_list`, `parse_proxy_token`, `no_proxy_matches_origin`, `wildcard_host_match` in `codex-rs/codex-client/src/outbound_proxy.rs`
- New Windows-only dependencies in `codex-rs/codex-client/Cargo.toml`: `windows-sys = "0.52"` (with `Win32_Foundation` and `Win32_Networking_WinHttp` features) and `sha2`

## Improvements


### Proxy Cache Keys Hashed on Windows

What: On Windows, the internal proxy decision cache now stores a SHA-256 hash of the request URL as the cache key rather than the raw URL string. This prevents URLs containing sensitive query parameters (such as OAuth access tokens or session identifiers) from persisting as plaintext in the process's heap.

Details:

- On non-Windows platforms the cache key remains the raw URL string (no change)
- On Windows the key is `SHA-256("system-proxy-cache-v1\0" + request_url)` as a hex string
- Cache capacity, TTL, and eviction behaviour are otherwise unchanged
- The hash prefix `system-proxy-cache-v1\0` is domain-separated so the same URL hashed for another purpose will not collide

Code references:
- `system_proxy_cache_key()` in `codex-rs/codex-client/src/outbound_proxy.rs`


Generated with:
- tool: `harness-investigations@0c752ef-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/codex/diff/v0.142.1.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.142.1.md`
