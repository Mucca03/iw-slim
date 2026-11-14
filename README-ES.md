# IW Slim

[English](README.md) · **Español**

**Recorta una instalación de Call of Duty: Infinite Warfare sin romper los modos que juegas.**

`iwslim` nació de un caso real: una instalación de **131 GB** usada solo para **Zombies**,
reducida a **51.6 GB** sin perder:

- los 5 mapas de Zombies (`cp_zmb`, `cp_rave`, `cp_disco`, `cp_final`, `cp_town`);
- texto y audio en español (o cualquier idioma que no sea inglés);
- el nombre del jugador y su configuración personal;
- el co-op LAN por IP (`connect <ip>`) con un segundo jugador.

Cada recorte es **reversible**: no se borra nada. Lo que no hace falta se mueve a una
carpeta de cuarentena con un manifiesto y un script de restauración.

**Objetivo:** esta herramienta está pensada para instalaciones que usan **iw7-mod**, el
cliente comunitario de Infinite Warfare (`iw7-mod.exe`). No instala ni actualiza el mod:
solo reorganiza los archivos de una instalación existente, y conoce su archivo de log, su
flag `-noupdate` y sus argumentos de arranque `-cpMode` / `+map`. iw7-mod es un proyecto
aparte con su propia distribución.

> Estado del ruleset `zombies`: **validado** contra `iw7-mod v1.0.2-144-g78d1a0a`.
> Los rulesets `multiplayer` y `campaign` son **plantillas**: no recortan nada hasta que
> generes y valides tus propias listas con [docs/MP-CP-GUIDE.md](docs/MP-CP-GUIDE.md).

---

## Cómo funciona

1. **Scan**: recorre la instalación y agrupa cada archivo por tipo, carpeta de idioma y tamaño.
2. **Plan**: aplica un ruleset explícito (JSON + listas de nombres) y marca cada archivo
   como `keep` o `quarantine`. Lo que no está en una lista **se conserva**.
3. **Apply**: mueve a cuarentena, escribe `manifest.json` + `restore.py` y deja una nota.
4. **Restore**: devuelve todo desde la cuarentena, o extrae paks sueltos de un ZIP.
5. **Verify** (Linux): lanza cada mapa y busca errores de assets/idioma en el log.

La regla de oro: **`plan` nunca toca el disco y `apply` solo mueve archivos, nunca borra.**

### Qué recorta el ruleset de Zombies

| Grupo | Archivos | Tamaño aprox. |
|---|---:|---:|
| Zonas de campaña/MP de la raíz (`.ff`, `.sabl`, `.sabs`) | 609 | ~24.2 GB |
| `english/` (sin usar si juegas en otro idioma) | 434 | ~11.7 GB |
| Vídeos que Zombies no usa (`.bik`) | 188 | ~6.9 GB |
| Paks de campaña/MP | 67 | ~35.8 GB |

Se conservan a propósito, entre otros: `mp_weapon_*`, `mp_head_*`, `mp_body_*`,
`mp_viewhands_*`, `livery_*`, `techsets_*`, `sysload_*`/`sysmain*` y `zombies_*`.

### Trampas conocidas (aprendidas jugando)

- **`english/` debe existir, aunque esté vacía.** Si borras la carpeta, el juego se cuelga
  al arrancar.
- **`assetfile21.pak` no se puede quitar.** La precarga de caches lo pide; el fallo aparece
  al cargar caches, no al entrar a un mapa (por eso tardó en detectarse).
- **`-noupdate` es obligatorio** con iw7-mod: el actualizador revierte el parche de idioma.
- El idioma se cambia parcheando el literal `"english"` dentro de `iw7-mod.exe` a
  `"spanish"` (ver [docs/METHOD.md](docs/METHOD.md)).

---

## Requisitos

Una instalación existente de Infinite Warfare con **iw7-mod**, más **Python 3.9+**.
Sin dependencias de Python de terceros.

```bash
git clone https://github.com/Mucca03/iw-slim.git
cd iw-slim
python3 iwslim.py --version
```

Para `trace` y `verify` en Linux: `inotify-tools`, `wine` y `xdotool`.

---

## Uso

### 1. Inventario

```bash
python3 iwslim.py scan --game ~/Juegos/iw
```

### 2. Calcular el plan (no modifica nada)

```bash
python3 iwslim.py plan --game ~/Juegos/iw --mode zombies --out plan.json
```

Lee el resumen y los avisos. Si tu juego está en **inglés**, añade `--keep-english`.

### 3. Aplicar (simulación primero)

```bash
python3 iwslim.py apply --plan plan.json            # simulación
python3 iwslim.py apply --plan plan.json --yes      # aplicar de verdad
```

La cuarentena va por defecto a `../iwslim_quarantine_zombies/` (cámbialo con `--quarantine`).

### 4. Verificar en Linux (opcional pero recomendado)

```bash
python3 iwslim.py trace  --game ~/Juegos/iw --map cp_zmb --duration 150
python3 iwslim.py plan   --game ~/Juegos/iw --mode zombies --trace traces/trace.txt
python3 iwslim.py verify --game ~/Juegos/iw --maps cp_zmb,cp_rave,cp_disco,cp_final,cp_town
```

`plan --trace` avisa si la traza abrió un archivo que el plan movería.

### 5. Deshacer

```bash
python3 iwslim.py restore --manifest ~/Juegos/iwslim_quarantine_zombies/manifest.json
# o recuperar paks sueltos de tu copia original:
python3 iwslim.py restore --game ~/Juegos/iw \
  --from-zip ~/copias/game-backup.zip --files assetfile21.pak
```

---

## Estructura del repositorio

```
iw-slim/
├── iwslim.py              # herramienta (scan / plan / apply / restore / trace / verify)
├── rules/
│   ├── zombies.json       # ruleset validado
│   ├── multiplayer.json   # plantilla
│   └── campaign.json      # plantilla
├── data/zombies/          # listas verificadas (qué se conserva y qué se mueve)
├── docs/
│   ├── METHOD.md / METHOD-ENG.md                  # método completo y reglas de seguridad
│   ├── FINDINGS.md / FINDINGS-ENG.md              # hallazgos técnicos (idioma, paks, zonas)
│   ├── MP-CP-GUIDE.md / MP-CP-GUIDE-ENG.md        # cómo adaptar la herramienta a MP y campaña
│   └── AGENT-PROMPT.md / AGENT-PROMPT-ENG.md      # prompt para que un agente de IA repita el proceso
├── examples/
└── tests/
```

---

## Hecho con OpenCode

Este proyecto salió de una sesión de trabajo con **OpenCode**, un agente de IA para
programar en la terminal. El agente no se limitó a escribir código: **investigó el juego en
marcha** sobre una instalación real.

Lo que hizo el agente, en orden:

1. **Midió** la instalación y agrupó ~4 900 archivos por tipo, idioma y tamaño.
2. **Instrumentó el juego con `inotifywait`** para grabar qué archivos abría cada mapa (así
   supo que `english/` no se toca cuando juegas en otro idioma).
3. **Cortó por etapas**, jugando y leyendo `iw7-mod/logs/console.log` después de cada corte.
4. **Encontró el fallo de `assetfile21.pak`** en la precarga de caches y lo convirtió en una
   regla permanente del ruleset.
5. **Convirtió el proceso manual en esta herramienta**, con tests, manifiestos y comandos de
   restauración.

La lección: un agente es útil aquí porque el trabajo real no es "borrar archivos grandes",
es **observar el juego, formular una hipótesis, cortar, verificar y poder volver atrás**.
Toda la evidencia está en [docs/FINDINGS.md](docs/FINDINGS.md).

> Para repetir el proceso con otro juego o con MP/campaña, usa
> [docs/AGENT-PROMPT.md](docs/AGENT-PROMPT.md): es el mismo encargo, listo para pegar.

---

## Aviso

Esto modifica archivos de una instalación que es tuya. Úsalo solo con copias obtenidas
legalmente, guarda una copia de los archivos originales y acepta que **cada build del juego
puede traer listas distintas**. Si algo falla: restaura la cuarentena y lee el log.

## Licencia

MIT. Ver [LICENSE](LICENSE).
