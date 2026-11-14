# Guía: adaptar IW Slim a Multijugador y Campaña

> Versión en inglés: [MP-CP-GUIDE-ENG.md](MP-CP-GUIDE-ENG.md).

Los rulesets `multiplayer.json` y `campaign.json` son **plantillas vacías a propósito**.
No recortan nada hasta que tú generes y valides las listas. Esta guía es el procedimiento
que usamos para Zombies, aplicado a MP y CP.

> Resumen de la diferencia: en Zombies solo necesitas 5 mapas. En MP necesitas **todos
> los mapas que juegues + armas + personalización + UI**. En CP necesitas **todas las
> misiones que vayas a jugar + vídeos + guardados**. Por eso la validación es más larga:
> no hay un único mapa que pruebe todo.

---

## 0. Antes de empezar

1. Copia de seguridad o ZIP original disponible.
2. Versión de `iw7-mod` identificada.
3. Idioma decidido. Si juegas en inglés, **no vacíes `english/`**.
4. Una carpeta de cuarentena separada por modo:
   `--quarantine ~/Documentos/games/iwslim_quarantine_mp`.
5. No mezcles modos en la misma cuarentena ni en el mismo ruleset.

---

## 1. Crear el ruleset de partida

`rules/multiplayer.json` (o `campaign.json`) ya tiene `protected_globs` correctos.
Solo hay que rellenar `remove_lists` y `keep_lists` cuando existan las listas.

```jsonc
{
  "remove_lists": ["remove-maps.txt", "remove-videos.txt", "remove-paks.txt"],
  "keep_lists":   ["keep-shared.txt", "keep-paks.txt"]
}
```

Las listas viven en `data/multiplayer/` o `data/campaign/`. Empieza con archivos
**vacíos**: el plan conservará todo y te dará el inventario base.

---

## 2. Multijugador

### 2.1 Qué conservar siempre

- `common_mp.ff`, `common_core_mp.*`, `global_mp.ff`, `global_core_mp.ff`,
  `mp_frontend.ff`, `ui_mp.ff`.
- **Todos** los `techsets_*` (la precarga los recorre).
- **Todos** los `mp_weapon_*`, `mp_head_*`, `mp_body_*`, `mp_viewhands_*`,
  `mp_fullbody*`, `livery_*`: son las armas, operadores y personalización.
- Los mapas MP que juegues: `mp_<mapa>.ff` + su `.sabl`/`.sabs` si existen.
- `patch_*` y las zonas de UI.

### 2.2 Qué se puede recortar

- Zonas de **campaña**: `cp_*`, `*_sp.ff` y sus `techsets_cp_*` (ojo: la precarga
  los pide, así que quitarlos puede generar avisos; solo quítalos si el log queda limpio).
- Zonas de **Zombies** si no las juegas: `cp_zmb`, `cp_rave`, `cp_disco`, `cp_final`,
  `cp_town`, `zombies_*`, `*_zm*`.
- **Vídeos de campaña** (`.bik` que no sean `sysload_*`, `sysmain*` ni de menú MP).
- Localización del idioma no usado (con las mismas reglas que Zombies).

### 2.3 Validar MP (importante: no hay un solo mapa)

MP tiene varios modos que cargan zonas distintas (TDM, Domination, Zombies-in-Spaceland,
etc.). Para validar:

1. Traza un arranque completo del menú MP:
   ```bash
   python3 iwslim.py trace --game ~/Documentos/games/iw --map mp_frontend --duration 180
   ```
2. Traza **cada mapa** que quieras conservar, jugando una partida contra bots o en LAN.
   ```bash
   python3 iwslim.py trace --game ~/Documentos/games/iw --map mp_<mapa> --duration 300
   ```
3. Junta las trazas y valida el plan:
   ```bash
   cat traces/*.txt > traces/mp_all.txt
   python3 iwslim.py plan --game ~/Documentos/games/iw --mode multiplayer --trace traces/mp_all.txt
   ```
4. Deja terminar la **precarga de caches** antes de dar por bueno el corte.

> En MP el co-op LAN se hace con `connect <ip>`; si tu recorte toca el mapa o las armas,
> la partida fallará al entrar, no al arrancar. Prueba siempre una partida real.

---

## 3. Campaña

### 3.1 Qué conservar siempre

- `common_sp.ff`, `common_core_sp.*`, `global_sp.ff`, `ui_sp.ff`.
- `techsets_common_sp` y los `techsets_*` que use cada misión.
- Los `.ff` de cada misión que vayas a jugar, con sus `.sabl`/`.sabs`.
- Los **vídeos de campaña** que aparezcan en esa misión.
- `players2/` si quieres conservar progreso y guardados (fuera de `protected_globs`,
  pero nunca lo muevas).

### 3.2 Qué se puede recortar

- Mapas MP que no juegues (pero cuidado: algunas armas/UI son compartidas).
- Mapas Zombies si no los juegas.
- Localización del idioma no usado.
- Misiones de campaña que no vayas a jugar (una por una, con traza).

### 3.3 Validar CP

1. Traza el menú y cada misión con la que quieras quedarte:
   ```bash
   python3 iwslim.py trace --game ~/Documentos/games/iw --map <nivel> --duration 420
   ```
2. El nombre de nivel es el del `.ff` sin extensión (por ejemplo `cp_<mision>`).
3. Comprueba que la misión carga, se juega y **guarda partida**.
4. Revisa `console.log` tras cada corte.

> La campaña es el modo más frágil: usa vídeos, guardados y checkpoints. Si dudas,
> conserva. El ahorro por misión suele ser menor que el riesgo.

---

## 4. Reglas para generar listas desde una traza

```bash
# todo lo que abrió la traza
cut -f1 traces/mp_all.txt | sort -u > traces/vistos.txt

# lo que está en disco y NO se abrió (candidatos, no borres aún)
cd ~/Documentos/games/iw
find . -type f | sed 's|^\./||' | sort > /tmp/en_disco.txt
comm -23 /tmp/en_disco.txt traces/vistos.txt > /tmp/no_vistos.txt
```

**No conviertas `/tmp/no_vistos.txt` directamente en lista de borrado.** Una traza
solo cubre lo que probaste. Úsala para *proponer* y luego valida mapa a mapa.

---

## 5. Checklist de validación por modo

| Prueba | MP | CP |
|---|---|---|
| Arranca al menú | sí | sí |
| Precarga de caches termina sin errores | sí | sí |
| Entra al primer mapa/misión | sí | sí |
| Juega 10+ minutos | sí | sí |
| Cambia de mapa/misión | sí | sí |
| Personalización / armas / perks | sí | — |
| Guarda y carga partida | — | sí |
| Co-op LAN `connect <ip>` | sí | — |
| Log sin `Could not find asset file` | sí | sí |

Si algo falla:

```bash
python3 iwslim.py restore --manifest <cuarentena>/manifest.json
```

y revisa qué archivo pedía el log antes de reintentar.

---

## 6. Prompt corto para un agente

Si prefieres delegarlo, usa [AGENT-PROMPT.md](AGENT-PROMPT.md) y cambia `--mode` y los
mapas del ejemplo. El prompt ya incluye las reglas de seguridad y la obligación de
validar con trazas y log.
