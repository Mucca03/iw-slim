# Method

> English version of [METHOD.md](METHOD.md).

This document explains **how to trim an install without breaking it** and why the tool is
designed this way. It is written so that another person (or an agent) can repeat the process
with another build, another language or another mode.

## Principles

1. **Nothing is deleted: it is moved.** Everything that leaves the game folder goes to a
   quarantine with `manifest.json` and `restore.py`. Recovery is one command.
2. **Explicit lists, never heuristics.** The plan only moves names that appear in
   `data/<mode>/*.txt`. An unknown file is always kept.
3. **Small, verifiable cuts.** Each group of files is removed separately and the game is
   tested before the next cut.
4. **Evidence before the list.** A trace (`inotifywait`) or a clean launch justifies every
   entry in the removal list.
5. **The log rules.** `iw7-mod/logs/console.log` is the source of truth for knowing whether
   an asset or a language zone is missing.

## Phases

### Phase 0 — Preparation

- Back up the original files (ZIP or a copy of the paks and zones).
- Confirm the `iw7-mod` version (`v1.0.2-144-g78d1a0a` in the original validation).
- Confirm the active language. In the original validation it was **Spanish**, applied by
  patching the `english` literal → `spanish` in `iw7-mod.exe` (offset `0x357b18`), always
  launching with `-noupdate`.

### Phase 1 — Inventory

```bash
python3 iwslim.py scan --game ~/Games/iw --json inventory.json
```

It groups by extension and by language folder. The four groups that matter in IW7:

| Group | What it is | Does Zombies use it? |
|---|---|---|
| `*.ff` in the root | zones (maps, weapons, UI) | depends on the mode |
| `*.sabl` / `*.sabs` | sound banks for each zone | yes, if the zone is used |
| `*.pak` | packed assets/images | depends on the map |
| `english/`, `spanish/` | localizations | only the active language |

### Phase 2 — Trace (the part that prevents breakage)

```bash
python3 iwslim.py trace --game ~/Games/iw --map cp_zmb --duration 150
```

It launches the game and records every opened file with `inotifywait`. Repeat for each map
you want to keep. Then validate the plan against the trace:

```bash
python3 iwslim.py plan --game ~/Games/iw --mode zombies --trace traces/trace.txt
```

If the trace opened something the plan wants to move, the plan flags it as
`SEGURIDAD: la traza abrió ...` ("SAFETY: the trace opened ...").

**Shortcut measured in the original validation:** with the language set to Spanish, **not a
single** file under `english/` was opened in any of the 5 maps. That allowed emptying the
whole folder (11.7 GB) while keeping the folder itself (the game hangs if it is missing).

### Phase 3 — Cuts, one group at a time

Recommended order, from lowest to highest risk:

1. **Videos** (`.bik`): low risk. Keep `sysload_*`, `sysmain*` and `zombies_*`.
2. **Campaign/MP zones in the root**: medium risk. Do not remove `mp_weapon_*`, `mp_head_*`,
   `mp_body_*`, `mp_viewhands_*`, `livery_*`, `techsets_*`, nor the `common*`, `global*`,
   `cp_*` and `zombies_*` zones.
3. **English localization**: empty `english/`, never delete the folder.
4. **Paks**: the most dangerous cut. See the next section.

After every cut: launch, play a map and read the log.

### Phase 4 — Paks: the cut that deceives

Paks are not opened when entering a map; they are opened during the **cache preload** and
when loading assets on demand. A missing pak can take a while to show up.

In the original validation:

- 67 paks moved to quarantine; the game launched fine and a map was played for **one hour**.
- When the cache preload was allowed to finish, the real error appeared:
  `Could not find asset file assetfile21.pak`.
- Only that pak (944 MB) was restored, and the preload finished with no further errors.

Resulting rule: **keep the paks the cache preload asks for** and validate paks by letting the
full preload finish, not just by entering a map.

### Phase 5 — Final verification

```bash
python3 iwslim.py verify --game ~/Games/iw \
  --maps cp_zmb,cp_rave,cp_disco,cp_final,cp_town
```

The command launches each map, waits, and searches `console.log` for:

- `Could not find asset file`
- `MISSING FILE`
- `Tried to load missing language zone`
- a visible `Fatal Error` window (with `xdotool`)

### Phase 6 — Consolidate

- Rewrite the human-readable removal manifest (`_ELIMINADOS.txt` in the original install)
  with totals and the restore command.
- Leave a `restaurar_pak.sh` next to the game to recover paks from the ZIP.
- Update `data/<mode>/keep-paks.txt` with the real list left on disk.

## Ruleset safety rules

- `protected_globs` covers binaries, scripts, `.txt`, `iw7-mod/**`, `spanish/**` and `main`.
- `remove_dirs` is emptied but **the folder is kept** (`english/`).
- `keep_lists` is used to check that what is kept matches what was validated: if a kept pak
  is not in `keep-paks.txt`, the plan warns.
- `remove_lists` are the verified lists; any name not present is kept.

## What NOT to do

- Do not delete `english/` (the folder).
- Do not delete `assetfile21.pak`.
- Do not launch without `-noupdate` if you use iw7-mod with a language patch.
- Do not assume "the map loaded" means the trim is fine: you must let the cache preload
  finish.
- Do not mix campaign and Zombies cuts in the same ruleset without validating both.
