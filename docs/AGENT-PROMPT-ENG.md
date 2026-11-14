# Prompt for an AI agent

> English version of [AGENT-PROMPT.md](AGENT-PROMPT.md).

Paste this text into an agent with file-system and terminal access (OpenCode, Claude Code,
etc.). It is meant to repeat the `iwslim` process for another mode, another language or
another build **without breaking the install**.

---

## Prompt

> You are working on a Call of Duty: Infinite Warfare install running `iw7-mod`.
> The goal is to **reduce its size as much as possible while keeping one specific mode** and
> to be able to **undo** any cut.
>
> ### Mandatory context
>
> 1. Before touching anything, run `python3 iwslim.py scan --game <PATH>` and save the
>    inventory. Identify the `iw7-mod` version.
> 2. Locate `iw7-mod/logs/console.log`: it is the source of truth.
> 3. Check whether the game is running. Do not apply anything while the game is open.
>
> ### Safety rules (non-negotiable)
>
> - **Never delete.** Move files to a quarantine with `iwslim apply`; every move is recorded
>   in `manifest.json` and can be reverted with `iwslim restore`.
> - **Never move a file that is not in an explicit list.** Anything unknown is kept.
> - **Never delete `english/`**: if the language is not English you may empty it, but the
>   folder must exist or the game hangs.
> - **Never move `assetfile21.pak`**: the cache preload asks for it.
> - **Do not launch without `-noupdate`** if the language was applied by patching
>   `iw7-mod.exe`.
> - Make **one cut per group** (videos, zones, language, paks) and validate after each one.
> - Do not accept a cut just because the map loads: **let the cache preload finish** and read
>   the whole `console.log`.
>
> ### Procedure
>
> 1. `scan` → inventory by type/size.
> 2. `trace` for each map/mission to keep, long enough for it to load and be played.
> 3. `plan` with the trace → read the `SEGURIDAD` ("safety") warnings.
> 4. `apply` in simulation, review, then `apply --yes`.
> 5. `verify` each map/mission.
> 6. If something fails: `restore`, read the log, adjust the list and repeat.
> 7. When done: update `data/<mode>/keep-paks.txt`, write a human-readable manifest of what
>    was moved, and leave a script to restore paks from the original ZIP.
>
> ### Deliverables
>
> - Ruleset at `rules/<mode>.json` with its status (`validated` or `template`).
> - Lists under `data/<mode>/` with the file count and the size they save.
> - A report with: build used, maps tested, time played, errors found, files restored and
>   final size.
> - Explicit confirmation that `restore` returns the install to its previous state.
>
> ### Example per mode
>
> ```bash
> # Zombies
> python3 iwslim.py trace  --game <PATH> --map cp_zmb --duration 150
> python3 iwslim.py plan   --game <PATH> --mode zombies --trace traces/trace.txt
> python3 iwslim.py verify --game <PATH> --maps cp_zmb,cp_rave,cp_disco,cp_final,cp_town
>
> # Multiplayer (trace the menu + every map you play)
> python3 iwslim.py trace  --game <PATH> --map mp_frontend --duration 180
> python3 iwslim.py trace  --game <PATH> --map mp_<map> --duration 300
> cat traces/*.txt > traces/mp_all.txt
> python3 iwslim.py plan   --game <PATH> --mode multiplayer --trace traces/mp_all.txt
>
> # Campaign (one trace per mission you keep)
> python3 iwslim.py trace  --game <PATH> --map <level> --duration 420
> python3 iwslim.py plan   --game <PATH> --mode campaign --trace traces/<level>.txt
> ```
>
> ### What you must NOT do
>
> - Turn "files not seen in a trace" into a removal list without validating.
> - Mix cuts for several modes in the same quarantine.
> - Touch `players2/` (config, player name, progress).
> - Report success without having played at least one full match/mission of the mode.

---

## Variant: "measure only" mode

If the user only wants to know how much can be saved, the agent must run `scan` and `plan`
and **stop there**. `plan` changes nothing; it is safe to present it as a report.

## Variant: Windows

`scan`, `plan`, `apply` and `restore` work on Windows. `trace` and `verify` are Linux-only
(they use `inotifywait` and `xdotool`). On Windows:

- Replace the trace with `Process Monitor` (filter `Path contains iw7`) and export to CSV;
  convert paths to relative paths with `\t` as the separator for `--trace`.
- Verify manually: launch, play a map, read `console.log`.
