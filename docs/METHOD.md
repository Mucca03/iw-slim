# Método

> Versión en inglés: [METHOD-ENG.md](METHOD-ENG.md).

Este documento explica **cómo se recorta una instalación sin romperla** y por qué la
herramienta está diseñada así. Está escrito para que otra persona (o un agente) pueda
repetir el proceso con otro build, otro idioma u otro modo.

## Principios

1. **No se borra: se mueve.** Todo lo que sale de la carpeta del juego va a una
   cuarentena con `manifest.json` y `restore.py`. Recuperar es un comando.
2. **Listas explícitas, nunca heurísticas.** El plan solo mueve nombres que aparecen en
   `data/<modo>/*.txt`. Un archivo desconocido se conserva siempre.
3. **Cortes pequeños y verificables.** Cada grupo de archivos se elimina por separado y
   se prueba el juego antes del siguiente corte.
4. **Evidencia antes de la lista.** Una traza (`inotifywait`) o un arranque limpio
   justifican cada entrada de la lista de borrado.
5. **El log manda.** `iw7-mod/logs/console.log` es la fuente de verdad para saber si
   falta un asset o una zona de idioma.

## Fases

### Fase 0 — Preparación

- Copia de seguridad de los archivos originales (ZIP o copia de los paks y zonas).
- Confirmar la versión de `iw7-mod` (`v1.0.2-144-g78d1a0a` en la validación original).
- Confirmar el idioma activo. En la validación original era **español**, aplicado
  parcheando el literal `english` → `spanish` en `iw7-mod.exe` (offset `0x357b18`),
  lanzando siempre con `-noupdate`.

### Fase 1 — Inventario

```bash
python3 iwslim.py scan --game ~/Documentos/games/iw --json inventario.json
```

Agrupa por extensión y por carpeta de idioma. Los cuatro grupos que importan en IW7:

| Grupo | Qué es | ¿Lo usa Zombies? |
|---|---|---|
| `*.ff` de la raíz | zonas (mapas, armas, UI) | depende del modo |
| `*.sabl` / `*.sabs` | bancos de sonido de cada zona | sí, si la zona se usa |
| `*.pak` | assets/imágenes empaquetados | depende del mapa |
| `english/`, `spanish/` | localizaciones | solo el idioma activo |

### Fase 2 — Traza (la parte que evita romperlo)

```bash
python3 iwslim.py trace --game ~/Documentos/games/iw --map cp_zmb --duration 150
```

Lanza el juego y graba con `inotifywait` cada archivo abierto. Repite por cada mapa que
quieras conservar. Luego valida el plan contra la traza:

```bash
python3 iwslim.py plan --game ~/Documentos/games/iw --mode zombies --trace traces/trace.txt
```

Si la traza abrió algo que el plan quiere mover, el plan lo marca como
`SEGURIDAD: la traza abrió ...`.

**Atajo medido en la validación original:** con el idioma en español no se abrió
**ningún** archivo de `english/` en ninguno de los 5 mapas. Eso permitió vaciar la
carpeta entera (11.7 GB) conservando la carpeta (el juego se cuelga si no existe).

### Fase 3 — Cortes, uno por grupo

Orden recomendado por riesgo creciente:

1. **Vídeos** (`.bik`): riesgo bajo. Conserva `sysload_*`, `sysmain*` y `zombies_*`.
2. **Zonas de campaña/MP de la raíz**: riesgo medio. No borres `mp_weapon_*`,
   `mp_head_*`, `mp_body_*`, `mp_viewhands_*`, `livery_*`, `techsets_*` ni las zonas
   `common*`, `global*`, `cp_*` y `zombies_*`.
3. **Localización inglesa**: vaciar `english/`, nunca borrar la carpeta.
4. **Paks**: el corte más peligroso. Ver la sección siguiente.

Después de cada corte: arrancar, jugar un mapa y revisar el log.

### Fase 4 — Paks: el corte que engaña

Los paks no se abren al entrar al mapa, se abren en la **precarga de caches** y al
cargar assets bajo demanda. Un pak que falta puede tardar en aparecer.

En la validación original:

- 67 paks movidos a cuarentena; el juego arrancó bien y un mapa se jugó **una hora**.
- Al dejar terminar la precarga de caches apareció el error real:
  `Could not find asset file assetfile21.pak`.
- Se restauró **solo** ese pak (944 MB) y la precarga terminó sin más errores.

Regla resultante: **conserva los paks que la precarga de caches pida** y valida paks
dejando terminar la precarga completa, no solo entrando a un mapa.

### Fase 5 — Verificación final

```bash
python3 iwslim.py verify --game ~/Documentos/games/iw \
  --maps cp_zmb,cp_rave,cp_disco,cp_final,cp_town
```

El comando lanza cada mapa, espera, y busca en `console.log`:

- `Could not find asset file`
- `MISSING FILE`
- `Tried to load missing language zone`
- ventana de `Fatal Error` visible (con `xdotool`)

### Fase 6 — Consolidar

- Reescribir el manifiesto legible de borrados (`_ELIMINADOS.txt` en la instalación
  original) con totales y el comando de restauración.
- Dejar un `restaurar_pak.sh` junto al juego para recuperar paks del ZIP.
- Actualizar `data/<modo>/keep-paks.txt` con la lista real que quedó en disco.

## Reglas de seguridad del ruleset

- `protected_globs` cubre binarios, scripts, `.txt`, `iw7-mod/**`, `spanish/**` y `main`.
- `remove_dirs` se vacía pero **la carpeta se conserva** (`english/`).
- `keep_lists` sirve para comprobar que lo conservado coincide con lo validado: si
  aparece un pak conservado que no está en `keep-paks.txt`, el plan avisa.
- `remove_lists` son las listas verificadas; cualquier nombre ausente se conserva.

## Qué NO hacer

- No borrar `english/` (la carpeta).
- No borrar `assetfile21.pak`.
- No lanzar sin `-noupdate` si usas iw7-mod con parche de idioma.
- No asumir que "el mapa cargó" significa que el recorte está bien: hay que dejar
  terminar la precarga de caches.
- No mezclar recortes de campaña y Zombies en el mismo ruleset sin validar ambos.
