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
- Adobe and agent login/payment/EULA are handled by the student. Do not change
  sandbox, OS privacy or AE settings yourself, install hidden services or add API
  credentials for this lesson.
- Native AE calls (`terminal.py` without `--dry-run`/`--list`, batch runs) send
  an Apple event on Mac or start `AfterFX.exe -r` on Windows; an agent sandbox
  blocks both. Run them outside the sandbox with the student's per-command
  approval from the first call (Codex: request escalated permissions). This is
  the expected path, not weakening security. A sandboxed call that failed before
  AE started (no `started.json` in its job folder) never reached AE: rerun the
  same sentence once with approval. Never resend a job with `started.json` or a
  receipt.
- The student works in their own fork: `origin` is the fork, `upstream` is
  `hyun2xyz/AFTEREFFECT_LAYA`. Follow `docs/fork-and-update.md`. Update with
  `git fetch upstream` + `git merge upstream/main`; never reset, force-push or
  discard the student's commits. Before a commit, check `git status` and stop if
  footage, AEP, generated media, weights or `tools.local.json` would be included.
- Codex asks for approval before network commands (git, gh, pip, brew, winget)
  and writes outside this folder. Request it and explain why; never change
  sandbox or security settings to avoid it.
- Keep personal jobs, AEP, screenshots, credentials, machine paths and weights in
  ignored `work/`, `models/` or a student-selected local directory; never publish them.
- Extend one concrete lesson at a time. This repository is not a full AE controller.
