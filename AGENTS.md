# AFTEREFFECT_LAYA — classroom starter

Use `.agents/skills/aftereffect-laya/SKILL.md` for this repository. Read
`START-HERE.md` and only the current OS setup when prerequisites are missing.
The whole repository is the project skill; no global skill installation is required.

- Teach one next step at a time. First locate Python, the actual OS and local AE.
  Use local desktop execution; a remote-only agent cannot operate the student's AE.
- Basic actions use stdlib Python and registered JSX, with native readback.
  No MCP, server, COLMAP, FFmpeg, Homebrew or model weights are required by core.
- Preserve the student's project. No automatic save, close, replacement, deletion
  or render. Act only on the intended active composition and selected layer.
- Use short result summaries; don't load full snapshots/keyframe arrays into chat.
  Respect job IDs, stale-snapshot checks and partial/unknown results; no blind retry.
- Optional Laya classifies short ambiguous requests only. It does not generate
  executable arguments, paths, JSX or authorization. No default model download.
- `setup_environment.py` prepares only this folder's venv/config. Terminal launcher
  installation is explicit and reversible. Keep existing Laya commands intact.
- Adobe and agent login/payment/EULA are handled by the student. Do not weaken
  sandbox/permissions, install hidden services or add API credentials for this lesson.
- Keep personal jobs, AEP, screenshots, credentials, machine paths and weights in
  ignored `work/`, `models/` or a student-selected local directory; never publish them.
- Extend one concrete lesson at a time. This repository is not a full AE controller.
