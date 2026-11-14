# Sample output

Real output from the install used to validate the `zombies` ruleset
(`iw7-mod v1.0.2-144-g78d1a0a`), **after** trimming.

## `scan`

Verbatim output (the tool prints its console messages in Spanish):

```
Juego: /home/mucca/Documentos/games/iw
Archivos: 728   Total: 48.04 GiB

categoría               archivos        tamaño
----------------------------------------------
paks                          33     20.39 GiB
sonido                        36     12.92 GiB
idioma:spanish                77     11.29 GiB
zonas                        525      2.03 GiB
vídeos                        23      1.36 GiB
binarios                       8     58.95 MiB
otros                         20      1.32 MiB
scripts                        3      1.67 KiB
metadata                       2         512 B
```

Translation of the headers, in order: `Game`, `Files`, `Total`, `category`, `files`,
`size`; categories: `paks`, `sound`, `language:spanish`, `zones`, `videos`, `binaries`,
`other`, `scripts`, `metadata`.

## `plan` on an already trimmed install

Verbatim output, with the English meaning:

```
Modo: zombies   Juego: /home/mucca/Documentos/games/iw
Archivos: 728   conservar: 728 (48.04 GiB)   mover: 0 (0 B)
Quedaría en: 48.04 GiB (de 48.04 GiB)
```

i.e. `Mode: zombies   Game: ...`, `Files: 728   keep: 728 (48.04 GiB)   move: 0 (0 B)`,
`Result: 48.04 GiB (of 48.04 GiB)`.

This is expected: **move: 0** means none of the entries in the `remove-*.txt` lists are
still present on disk. It is a good idempotency check.

## `plan` on an untrimmed install (approximate)

What the tool reports on the first pass, with the same lists:

```
Files: ~4900   keep: ~1200   move: ~3700
Result: ~48 GiB (of ~131 GiB)

Largest cuts:
    3.17 GiB  english/zombies_...      — english localization (unused in another language)
    2.85 GiB  assetfileXX.pak          — campaign/multiplayer pak
    ...
```

Exact numbers depend on the build. What matters is reading the **warnings** before
applying.

## `trace` file format

Plain text, one relative path and its open count per line, separated by a tab:

```
# iwslim trace  2026-11-14T17:03:11+00:00
# map=cp_zmb  duration=150s
# relative_path<TAB>opens
code_post_gfx.ff	1
cp_zmb.ff	1
common_cp.ff	2
imagefile17.pak	4
assetfile21.pak	3
spanish/cp_zmb.ff	1
```

Only the first column is used to validate the plan (`plan --trace`). Lines starting
with `#` are ignored.
