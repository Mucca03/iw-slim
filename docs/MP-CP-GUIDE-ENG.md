# Guide: adapting IW Slim to Multiplayer and Campaign

> English version of [MP-CP-GUIDE.md](MP-CP-GUIDE.md).

The `multiplayer.json` and `campaign.json` rulesets are **empty templates on purpose**. They
trim nothing until you generate and validate the lists. This guide is the procedure we used
for Zombies, applied to MP and CP.

> Summary of the difference: for Zombies you only need 5 maps. For MP you need **every map
> you play + weapons + customization + UI**. For CP you need **every mission you are going
> to play + videos + saves**. That is why validation takes longer: there is no single map
> that tests everything.

---

## 0. Before you start

1. A backup or the original ZIP available.
2. The `iw7-mod` version identified.
3. Language decided. If you play in English, **do not empty `english/`**.
4. A separate quarantine folder per mode:
   `--quarantine ~/Games/iwslim_quarantine_mp`.
5. Do not mix modes in the same quarantine or in the same ruleset.

---

## 1. Create the starting ruleset

`rules/multiplayer.json` (or `campaign.json`) already has correct `protected_globs`.
You only need to fill in `remove_lists` and `keep_lists` once the lists exist.

```jsonc
{
  "remove_lists": ["remove-maps.txt", "remove-videos.txt", "remove-paks.txt"],
  "keep_lists":   ["keep-shared.txt", "keep-paks.txt"]
}
```

The lists live in `data/multiplayer/` or `data/campaign/`. Start with **empty** files: the
plan will keep everything and give you the baseline inventory.

---

## 2. Multiplayer

### 2.1 What to always keep

- `common_mp.ff`, `common_core_mp.*`, `global_mp.ff`, `global_core_mp.ff`,
  `mp_frontend.ff`, `ui_mp.ff`.
- **All** `techsets_*` (the preload walks them).
- **All** `mp_weapon_*`, `mp_head_*`, `mp_body_*`, `mp_viewhands_*`, `mp_fullbody*`,
  `livery_*`: these are the weapons, operators and customization.
- The MP maps you play: `mp_<map>.ff` + its `.sabl`/`.sabs` if present.
- `patch_*` and the UI zones.

### 2.2 What can be trimmed

- **Campaign** zones: `cp_*`, `*_sp.ff` and their `techsets_cp_*` (note: the preload asks for
  them, so removing them may produce warnings; only remove them if the log stays clean).
- **Zombies** zones if you do not play them: `cp_zmb`, `cp_rave`, `cp_disco`, `cp_final`,
  `cp_town`, `zombies_*`, `*_zm*`.
- **Campaign videos** (`.bik` that are not `sysload_*`, `sysmain*` or MP menu videos).
- Localization for the unused language (same rules as Zombies).

### 2.3 Validate MP (important: there is no single map)

MP has several modes that load different zones (TDM, Domination, Zombies-in-Spaceland,
etc.). To validate:

1. Trace a full MP menu startup:
   ```bash
   python3 iwslim.py trace --game ~/Games/iw --map mp_frontend --duration 180
   ```
2. Trace **each map** you want to keep, playing a match against bots or on LAN.
   ```bash
   python3 iwslim.py trace --game ~/Games/iw --map mp_<map> --duration 300
   ```
3. Merge the traces and validate the plan:
   ```bash
   cat traces/*.txt > traces/mp_all.txt
   python3 iwslim.py plan --game ~/Games/iw --mode multiplayer --trace traces/mp_all.txt
   ```
4. Let the **cache preload** finish before accepting the cut.

> In MP, LAN co-op uses `connect <ip>`; if your trim touches the map or the weapons, the
> match will fail when joining, not at startup. Always test a real match.

---

## 3. Campaign

### 3.1 What to always keep

- `common_sp.ff`, `common_core_sp.*`, `global_sp.ff`, `ui_sp.ff`.
- `techsets_common_sp` and the `techsets_*` used by each mission.
- The `.ff` for each mission you are going to play, with their `.sabl`/`.sabs`.
- The **campaign videos** that appear in that mission.
- `players2/` if you want to keep progress and saves (outside `protected_globs`, but never
  move it).

### 3.2 What can be trimmed

- MP maps you do not play (but careful: some weapons/UI are shared).
- Zombies maps if you do not play them.
- Localization for the unused language.
- Campaign missions you are not going to play (one at a time, with a trace).

### 3.3 Validate CP

1. Trace the menu and each mission you want to keep:
   ```bash
   python3 iwslim.py trace --game ~/Games/iw --map <level> --duration 420
   ```
2. The level name is the `.ff` name without the extension (for example `cp_<mission>`).
3. Check that the mission loads, is playable and **saves the game**.
4. Read `console.log` after every cut.

> Campaign is the most fragile mode: it uses videos, saves and checkpoints. When in doubt,
> keep it. The savings per mission are usually smaller than the risk.

---

## 4. Rules for generating lists from a trace

```bash
# everything the trace opened
cut -f1 traces/mp_all.txt | sort -u > traces/seen.txt

# what is on disk and was NOT opened (candidates, do not delete yet)
cd ~/Games/iw
find . -type f | sed 's|^\./||' | sort > /tmp/on_disk.txt
comm -23 /tmp/on_disk.txt traces/seen.txt > /tmp/not_seen.txt
```

**Do not turn `/tmp/not_seen.txt` directly into a removal list.** A trace only covers what
you tested. Use it to *propose* candidates, then validate map by map.

---

## 5. Per-mode validation checklist

| Test | MP | CP |
|---|---|---|
| Starts to the menu | yes | yes |
| Cache preload finishes with no errors | yes | yes |
| Enters the first map/mission | yes | yes |
| Plays for 10+ minutes | yes | yes |
| Switches map/mission | yes | yes |
| Customization / weapons / perks | yes | — |
| Saves and loads a game | — | yes |
| LAN co-op `connect <ip>` | yes | — |
| Log free of `Could not find asset file` | yes | yes |

If something fails:

```bash
python3 iwslim.py restore --manifest <quarantine>/manifest.json
```

and check which file the log was asking for before trying again.

---

## 6. Short prompt for an agent

If you prefer to delegate, use [AGENT-PROMPT-ENG.md](AGENT-PROMPT-ENG.md) and change `--mode`
and the maps in the example. The prompt already includes the safety rules and the requirement
to validate with traces and the log.
