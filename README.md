# Human Anatomy Atlas 7.4.01: Hungarian–Latin language pack

An unofficial, community-made Hungarian translation for the Windows desktop app **Human Anatomy Atlas 7.4.01** by Visible Body. The app's original Latin terminology stays unchanged. The English language slot is replaced with Hungarian.

The user guide is in Hungarian: **[README.hu.md](README.hu.md)**.

> Not affiliated with or endorsed by Visible Body / Argosy Publishing. This repository contains **no part of the application**, its 3D assets or its original texts. You need your own legitimate copy of Atlas 7.4.01.
> The translation is a study aid. **It has not been reviewed by a medical professional.**

## What it does
- Translates 241 UI rows, 4,643 anatomical name rows and 11,385 catalog text fields (definitions, health descriptions, quizzes and labels) into Hungarian. It also translates 4 hard-coded UI strings.
- Adds Hungarian search that works with or without accents.
- Lets you pick one of three variants at install time:
  - `magyar`: Hungarian-style terms (*oldalsó / belső*)
  - `latinos`: Latin-style terms (*laterális / mediális*), derived from the native Latin names
  - `latinkviz`: Hungarian names, but quiz questions name the target by its native Latin name (for Latin practice); prompts stay Hungarian where the Latin would be ambiguous
- Is reversible. The installer verifies every file by SHA-256, writes a verified backup, and refuses to touch unknown or modified files. Running `Restore.cmd` brings back the original English files.

## How it works
Releases ship **binary deltas** (copy ranges plus our literal bytes) that the installer applies on the user's machine to their own original files:
- `Human Anatomy Atlas_Data/resources.assets`: translated TextAssets (UI, names, search index, catalog fields)
- `Human Anatomy Atlas_Data/Managed/Assembly-UnityScript.dll`: Hungarian vowels in the A–Z index, a runtime sort fix for the search table, and 4 display strings

| Path | Purpose |
|---|---|
| `pack_builder.py` | Builds the patched assets for a variant, verifies the round trip and emits the delta |
| `variants.py` | Derives the `latinos` variant from native Latin (lateralis/medialis only, never internus/externus) |
| `build_release.py` | Release ZIP; gated by `release-policy.json` |
| `ManagedPatcher/` | Mono.Cecil patch of the managed DLL, pinned to the original hash, with fingerprints of every other method |
| `Install-Pack.ps1`, `Install.cmd`, `Restore.cmd` | Windows installer, variant switching and restore |
| `translations/` | Hungarian anatomical names and UI (Hungarian only) |
| `corrections/` | Hash-guarded correction overlays for the names and UI |
| `quality-review/` | QA summaries, open terminology questions (`NYITOTT-KERDESEK.csv`) and check scripts |
| `test_*.py` | Unit tests; `test_windows_fixture.py` exercises the installer on a Windows host over SSH with synthetic files |

## Building from source
The Hungarian translations of the long catalog texts (definitions, health descriptions, quizzes) are a translation of the publisher's copyrighted prose. They ship only inside the release ZIP and are not published as source here.

A rebuild needs files that are **not** in this repository and must come from your own Atlas 7.4.01 install: `originals/resources.assets`, `originals/Assembly-UnityScript.dll` and the TextAssets extracted from it (`inventory_fulltext.py`, `prepare_fulltext_jobs.py`), plus the long-text translation files. Python 3 with `UnityPy` and the .NET SDK are required.

```bash
python -m unittest test_pack test_fulltext test_collect_fulltext test_manifest test_variants
python pack_builder.py magyar latinos
python build_release.py
```

## Accuracy and contributions
All names and texts went through automated checks for direction, side, structure type, movement, number and negation consistency, and the flagged items were reviewed by hand. Several factual errors in the original English were corrected. Around 280 names remain open questions, usually because the English and Latin labels disagree; they are listed in `quality-review/name-accuracy/NYITOTT-KERDESEK.csv`. Corrections from anatomists and students are welcome.
