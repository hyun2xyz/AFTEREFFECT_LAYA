---
name: aftereffect-laya
description: Start a clean Mac/Windows classroom computer and teach basic AE composition/layer/keyframe commands with stdlib Python, registered JSX and optional local Laya classification. Repository-bound; no MCP.
---

# Aftereffect Laya classroom starter

This is a repository-bound skill. Locate the root containing `scripts/terminal.py`;
all commands below run from that root. Keep the whole repository (the student's fork) together.
Do not install the teacher's global harness or copy this SKILL.md alone.

## Start from the student's actual computer

1. Read [START-HERE](../../../START-HERE.md). Locate the OS, local working folder,
   Python and AE before issuing commands. Read only [Mac setup](../../../docs/setup-macos.md)
   or [Windows setup](../../../docs/setup-windows.md). No Python present means the
   official installer comes first. Remote-only coding hosts cannot control local AE.
2. Core supports Python3.12/3.13 and AE24+. `scripts/setup_environment.py` checks
   and prepares only this root's venv/config. No base pip packages, weights,
   Homebrew, Git, MCP, network service or global skill install are required.
3. Adobe/agent accounts, login, licenses and EULA belong to the student. Explain
   necessary local native-automation/receipt permissions; do not silently change them.
4. Teach [the first lesson](../../../docs/first-lesson.md): dry-run, native inspect,
   create one new1920×1090 composition, then green composition background. Preserve
   all existing project items and unsaved work; no auto save/close/delete/render.

## Spend context only on the next operation

- Clear supported phrases use `scripts/terminal.py` directly. Don't generate new
  JSX or call a model for every property. `--list` shows the fixed vocabulary.
  Use the current active composition and exactly one selected layer when needed.
- For a batch, read only the relevant entry from `scripts/ae_basic.py catalog --op`;
  use native inspect, validated action JSON, then generated `run.jsx`. Details:
  [commands](../../../docs/commands.md). No free-form code/paths/permissions from a model.
- Read short result summaries, not complete snapshots or keyframe arrays. Use
  Python to select/check large data. `prepared` and process exit0 are not native proof.
- Native transport is AE's DoScriptFile Apple event on Mac / AfterFX.exe -r on
  Windows. Agent sandboxes block both: run native calls outside the sandbox with
  the student's approval as `AGENTS.md` describes. If still unavailable, hand the generated JSX to the student for AE's
  File > Scripts > Run Script File and wait for a real receipt before claiming success.
- Native snapshot/session IDs and receipts prevent stale/duplicate operations.
  If partial/unknown/timed out, preserve logs and inspect before choosing another job.
  Do not resend a completed or uncertain job. One undo group is not a transaction.
- Existing expressions/animation, separated position and camera/light transforms
  are outside the static-edit shortcut. Do not clear them to make a command pass.

## Optional next lesson

Only read [Laya](../../../docs/laya.md) when local repeated semantic classification
would help or the student requests it. Fixed commands need no inference. The model
recommends a known operation/mode; it never creates executable arguments or grants
authorization. Cancellation, quotes and explanation requests still need the
original human intent. Missing backend/invalid probabilities/truncation means abstain.

Use [validation](../../../docs/validation.md) to distinguish source/CI checks,
the teacher's Mac native proof and a student's unverified native host. Do not turn
synthetic classifier samples into accuracy or token-savings promises.

After a lesson, record only files, verified result, observed issue and one next
step in ignored `work/<lesson>/next.md`. Extend one requested capability at a time.
