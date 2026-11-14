# Technical findings

> English version of [FINDINGS.md](FINDINGS.md).

Evidence collected during the real reduction of an Infinite Warfare install
(`iw7-mod` v1.0.2-144-g78d1a0a) on Linux/Wine. These are not opinions: every point was
checked either on the install itself or in `console.log`.

## 1. The language is controlled by the iw7-mod executable

- `iw7-mod.exe` contains the literal `english` at offset `0x357b18`.
- Patching it to `spanish` makes the game load `spanish/` and not `english/`.
- **`-noupdate` is mandatory**: without it, the updater restores the executable and the
  language goes back to English.
- Consequence for trimming: the folder of the **inactive** language can be discarded.

## 2. `english/` can be emptied, but not deleted

- With the language set to Spanish, **0 opens** of files under `english/` were recorded in
  the 5 maps (`inotifywait`).
- The folder holds ~11.7 GB of localizations (zones + audio) that are never read.
- If the folder is deleted, the game **hangs on startup**. If it is emptied and kept, it
  starts with no language warnings.
- Rule: `english/` empty but present.

## 3. `assetfile21.pak` is required by the cache preload

- It is not needed to enter a map, which is why the game ran for **one hour** without it.
- When the full preload was allowed to finish: `Could not find asset file assetfile21.pak`
  and `Fatal Error`.
- After restoring the pak (944 MB), the preload finished cleanly.
- Rule: it does not belong in the list of disposable paks.

## 4. The cache preload walks ALL `techsets_*`

- The log shows `Loading zone techsets_*` for campaign, MP and zombies, one by one.
- That is why a campaign `techsets_*` can reference a pak that is actually used.
- `techsets_*` files are small: always keep them.

## 5. What Zombies maps share with MP

Zombies maps use MP assets. What must **not** be removed even if it looks like MP:

- `mp_weapon_*` (`world`, `view`, `_tr` variants), `mp_head_*`, `mp_body_*`,
  `mp_viewhands_*`, `mp_fullbody*`.
- `livery_*`.
- `common*`, `global*`, `cp_*`, `zombies_*` zones and all `techsets_*`.
- `sysload_*` and `sysmain*` (loading/menu videos).

## 6. Zone and sound structure

- Each `X.ff` zone may have `X.sabl` (index) and `X.sabs` (data), but not always.
- A kept `.ff` whose `.sabl`/`.sabs` was moved is suspicious; the plan warns about it.
- `common_core_mp.sabs` is tiny (4 KB) while `common_core_mp.sabl` is large (352 MB):
  size does not indicate importance.

## 7. Paks: what was actually opened

- The install ships `assetfile*.pak` and `imagefile*.pak`.
- Many paks are campaign/MP and no Zombies map opens them.
- After the cuts, **33 paks** were left on disk (including `assetfile21.pak`).
- The exact list is in `data/zombies/keep-paks.txt`.

## 8. Logs and diagnostics

- Runtime log: `iw7-mod/logs/console.log`.
- Useful messages:
  - `Could not find asset file X.pak` → a pak is missing.
  - `Tried to load missing language zone ...` → wrong language/folder.
  - `Could not find fx "..."` → missing effect; in practice it did not prevent playing.
  - `Loading zone <name>` → zone loaded (useful to learn the real order).
- Error windows are detected with `xdotool search --name "Fatal Error"`.

## 9. Wine on Linux

- After killing the game, Wine can hang; run `wineserver -k` and wait before relaunching.
- Automated launches must kill the process when done (`iwslim verify` does this).
- The game recreates temporary files in the prefix (`Temp/iw7-tlsdll.dll`); they are
  disposable and get regenerated.

## 10. Measured result

| Item | Before | After |
|---|---:|---:|
| Install | ~131.34 GB | **51.59 GB** |
| Paks on disk | 100 | 33 |
| `english/` | 11.7 GB | 0 B (folder present) |
| Zombies maps tested | — | 5/5 |
| Gameplay validated | — | ~1 h on `cp_zmb` with no issues |

The original ZIP (112.5 GB) was kept as a safety net during validation; with
`iwslim restore --from-zip` any single pak can be recovered.
