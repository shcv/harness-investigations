# Changelog for version 2.1.173

## Summary

This release improves the accuracy of safety-refusal error messages, which now distinguish between actual cybersecurity/biology content blocks and generic safety flags. It also explicitly marks sandboxing as unsupported on Windows, and includes a display fix for model names containing "fable".


## Improvements


### More accurate safety-refusal messages

When the model's safety measures block a request, the error message now reflects the actual refusal category instead of always blaming cybersecurity or biology topic restrictions.

Previously, all safety refusals from a named model showed the same message:

> "{model} has safety measures that flag messages on most cybersecurity or biology topics … They may flag safe, normal content as well."

This message appeared even when the flagged content had nothing to do with cybersecurity or biology, which was confusing and inaccurate.

Starting in this version, the message is category-aware:

- Requests actually flagged for cybersecurity or biology content still show the specific message about those topic restrictions.
- Requests flagged for other reasons now show a softer, more accurate message: "This model has measures that flagged something in this session. This sometimes happens with safe, normal conversations. These measures let us bring you Mythos-level capability in other areas sooner, and we're working to refine them."

The same category-aware logic now applies to model-switch messages — when the CLI falls back to an alternative model after a refusal, it reports the appropriate reason rather than always citing cyber/bio restrictions.

Evidence: category check function (search for `"cyber" || H === "bio"`), generic refusal message (search for `"This model has measures that flagged something in this session"`)


### Sandboxing explicitly reported as unsupported on Windows

The sandboxing platform-support check now returns `false` immediately when running on Windows, before delegating to the native sandbox library's own check. This makes the "sandboxing unavailable" path reach the right code branch reliably on Windows builds.

No behavioral change is expected for users already on Windows — sandboxing was not functional on Windows before — but this closes a gap where the platform check could reach platform-specific native code unnecessarily.

Evidence: early-exit guard added to `isSupportedPlatform` (search for `if (s$() === "windows") return !1`)


### Model-name display fix for Fable models

A small formatting correction prevents an extra bold terminal marker (`[1m]`) from being appended to model names that contain "fable" in certain display contexts. Previously the name could render with a stray bold escape sequence. This only affects model-name display in the UI, not any behavior.

Evidence: new model-name helper (search for `H.toLowerCase().includes("fable")`)


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.173-2.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.173.txt`
