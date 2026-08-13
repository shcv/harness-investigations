# Changelog for version 2.1.231

## Summary

This is a narrow maintenance release from 2.1.229. The only user-observable code change updates the default OAuth callback URL used when connecting OAuth-authenticated MCP servers, replacing the IPv4 loopback address with `localhost`.

## Bug Fixes

- OAuth-authenticated MCP servers now use `http://localhost:<port>/callback` as their default browser redirect URI instead of `http://127.0.0.1:<port>/callback`. This can improve compatibility with identity providers that register or accept `localhost` callback URLs. Claude Code still binds its local callback listener to `127.0.0.1`, so the callback remains local-only. Evidence: the default redirect helper changed from `"http://127.0.0.1:${e}/callback"` to `"http://localhost:${e}/callback"`; it is used when an MCP server has no custom `redirectUri`.

## Notes

No migration is required. If an MCP OAuth provider explicitly allowlists redirect URIs, ensure it permits `http://localhost:<port>/callback` rather than only the prior `127.0.0.1` form.


Generated with:
- tool: `harness-investigations@90d1a16-dirty`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.231.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.231.txt`
