# IW Slim

**English** · [Español](README-ES.md)

**Shrink a Call of Duty: Infinite Warfare install without breaking the modes you actually play.**

`iwslim` was built for a real case: a **131 GB** install used only for **Zombies**, cut down
to **51.6 GB** without losing:

- all 5 Zombies maps (`cp_zmb`, `cp_rave`, `cp_disco`, `cp_final`, `cp_town`);
- Spanish text and audio (or any non-English language);
- the player name and personal config;
- LAN co-op over IP (`connect <ip>`) with a second player.

Every cut is **reversible**: nothing is deleted. Whatever is not needed is moved to a
quarantine folder with a manifest and a restore script.

**Target:** this tool is meant for installs running **iw7-mod**, the community client for
Infinite Warfare (`iw7-mod.exe`). It does not install or update the mod: it only reorganizes
the files of an existing install, and it knows about iw7-mod's log file, its `-noupdate` flag
and its `-cpMode` / `+map` launch arguments. iw7-mod itself is a separate project with its own
distribution.

> Zombies ruleset status: **validated** against `iw7-mod v1.0.2-144-g78d1a0a`.
> The `multiplayer` and `campaign` rulesets are **templates**: they trim nothing until you
> generate and validate your own lists with [docs/MP-CP-GUIDE-ENG.md](docs/MP-CP-GUIDE-ENG.md).

---

## How it works

1. **Scan**: walk the install and group every file by type, language folder and size.
2. **Plan**: apply an explicit ruleset (JSON + name lists) and mark each file
   `keep` or `quarantine`. Anything not listed **is kept**.
3. **Apply**: move files to quarantine, write `manifest.json` + `restore.py`, leave a note.
4. **Restore**: bring everything back from quarantine, or extract single paks from a ZIP.
5. **Verify** (Linux): launch each map and look for asset/language errors in the log.

The golden rule: **`plan` never touches the disk and `apply` only moves files, never deletes.**

### What the Zombies ruleset trims

| Group | Files | Approx. size |
|---|---:|---:|
| Campaign/MP zones in the root (`.ff`, `.sabl`, `.sabs`) | 609 | ~24.2 GB |
| `english/` (unused when playing in another language) | 434 | ~11.7 GB |
| Videos not used by Zombies (`.bik`) | 188 | ~6.9 GB |
| Campaign/MP paks | 67 | ~35.8 GB |

Kept on purpose, among others: `mp_weapon_*`, `mp_head_*`, `mp_body_*`, `mp_viewhands_*`,
`livery_*`, `techsets_*`, `sysload_*`/`sysmain*` and `zombies_*`.

### Known traps (learned the hard way)

- **`english/` must exist, even if empty.** Delete the folder and the game hangs on startup.
- **`assetfile21.pak` cannot be removed.** The cache preload requests it; the failure shows up
  during cache loading, not when entering a map (which is why it took a while to notice).
- **`-noupdate` is mandatory** with iw7-mod: the updater reverts the language patch.
- The language is switched by patching the `"english"` literal inside `iw7-mod.exe` to
  `"spanish"` (see [docs/METHOD-ENG.md](docs/METHOD-ENG.md)).

---

## Requirements

An existing Infinite Warfare install running **iw7-mod**, plus **Python 3.9+**.
No third-party Python packages.

```bash
git clone https://github.com/Mucca03/iw-slim.git
cd iw-slim
python3 iwslim.py --version
```

For `trace` and `verify` on Linux: `inotify-tools`, `wine` and `xdotool`.

---

## Usage

### 1. Inventory

```bash
python3 iwslim.py scan --game ~/Games/iw
```

### 2. Compute the plan (changes nothing)

```bash
python3 iwslim.py plan --game ~/Games/iw --mode zombies --out plan.json
```

Read the summary and the warnings. If your game runs in **English**, add `--keep-english`.

### 3. Apply (dry run first)

```bash
python3 iwslim.py apply --plan plan.json            # simulation
python3 iwslim.py apply --plan plan.json --yes      # for real
```

Quarantine defaults to `../iwslim_quarantine_zombies/` (override with `--quarantine`).

### 4. Verify on Linux (optional but recommended)

```bash
python3 iwslim.py trace  --game ~/Games/iw --map cp_zmb --duration 150
python3 iwslim.py plan   --game ~/Games/iw --mode zombies --trace traces/trace.txt
python3 iwslim.py verify --game ~/Games/iw --maps cp_zmb,cp_rave,cp_disco,cp_final,cp_town
```

`plan --trace` warns if the trace opened a file the plan would move.

### 5. Undo

```bash
python3 iwslim.py restore --manifest ~/Games/iwslim_quarantine_zombies/manifest.json
# or pull individual paks from your original backup:
python3 iwslim.py restore --game ~/Games/iw \
  --from-zip ~/backups/game-backup.zip --files assetfile21.pak
```

---

## Repository layout

```
iw-slim/
├── iwslim.py              # tool (scan / plan / apply / restore / trace / verify)
├── rules/
│   ├── zombies.json       # validated ruleset
│   ├── multiplayer.json   # template
│   └── campaign.json      # template
├── data/zombies/          # verified lists (what is kept and what is moved)
├── docs/
│   ├── METHOD.md / METHOD-ENG.md                  # full method and safety rules
│   ├── FINDINGS.md / FINDINGS-ENG.md              # technical findings (language, paks, zones)
│   ├── MP-CP-GUIDE.md / MP-CP-GUIDE-ENG.md        # how to adapt the tool to MP and campaign
│   └── AGENT-PROMPT.md / AGENT-PROMPT-ENG.md      # prompt for an AI agent to repeat the process
├── examples/
└── tests/
```

---

## Built with OpenCode

This project came out of a working session with **OpenCode**, an AI coding agent for the
terminal. The agent did not just write code: it **investigated the running game** on a real
installation.

What the agent did, in order:

1. **Measured** the install and grouped ~4,900 files by type, language and size.
2. **Instrumented the game with `inotifywait`** to record which files each map opened (that is
   how it learned that `english/` is never touched when playing in another language).
3. **Cut in stages**, playing and reading `iw7-mod/logs/console.log` after every cut.
4. **Found the `assetfile21.pak` failure** during cache preload and turned it into a permanent
   rule in the ruleset.
5. **Turned the manual procedure into this tool**, with tests, manifests and restore commands.

The lesson: an agent is useful here because the real work is not "delete big files", it is
**observe the game, form a hypothesis, cut, verify, and be able to roll back**. All the
evidence is in [docs/FINDINGS-ENG.md](docs/FINDINGS-ENG.md).

> To repeat the process for another game or for MP/campaign, use
> [docs/AGENT-PROMPT-ENG.md](docs/AGENT-PROMPT-ENG.md): same assignment, ready to paste.

---

## Disclaimer

This modifies files of a game installation you own. Use it only with legally obtained copies,
keep a backup of the original files, and accept that **every game build may ship different
lists**. If something breaks: restore the quarantine and read the log.

## License

MIT. See [LICENSE](LICENSE).
