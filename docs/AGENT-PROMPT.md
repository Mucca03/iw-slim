# Prompt para un agente de IA

> Versión en inglés: [AGENT-PROMPT-ENG.md](AGENT-PROMPT-ENG.md).

Pega este texto en un agente con acceso al sistema de archivos y a la terminal
(OpenCode, Claude Code, etc.). Está pensado para repetir el proceso de `iwslim` con
otro modo, otro idioma u otro build **sin romper la instalación**.

---

## Prompt

> Trabajas sobre una instalación de Call of Duty: Infinite Warfare con `iw7-mod`.
> El objetivo es **reducir el tamaño todo lo posible conservando un modo concreto**
> y poder **deshacer** cualquier recorte.
>
> ### Contexto obligatorio
>
> 1. Antes de tocar nada, ejecuta `python3 iwslim.py scan --game <RUTA>` y guarda el
>    inventario. Identifica la versión de `iw7-mod`.
> 2. Localiza `iw7-mod/logs/console.log`: es la fuente de verdad.
> 3. Comprueba si el juego está abierto. No apliques nada con el juego abierto.
>
> ### Reglas de seguridad (no negociables)
>
> - **Nunca borres.** Mueve a una cuarentena con `iwslim apply`; cada movimiento queda
>   en `manifest.json` y se puede revertir con `iwslim restore`.
> - **Nunca muevas un archivo que no esté en una lista explícita.** Lo desconocido se
>   conserva.
> - **Nunca borres `english/`**: si el idioma no es inglés puedes vaciarla, pero la
>   carpeta debe existir o el juego se cuelga.
> - **Nunca muevas `assetfile21.pak`**: la precarga de caches lo pide.
> - **No lances sin `-noupdate`** si el idioma se aplicó parcheando `iw7-mod.exe`.
> - Haz **un corte por grupo** (vídeos, zonas, idioma, paks) y valida tras cada uno.
> - No des por bueno un corte solo porque el mapa carga: **deja terminar la precarga
>   de caches** y revisa `console.log` completo.
>
> ### Procedimiento
>
> 1. `scan` → inventario por tipo/tamaño.
> 2. `trace` por cada mapa/misión que se quiera conservar, durante suficiente tiempo
>    para que cargue y se juegue.
> 3. `plan` con la traza → revisa los avisos `SEGURIDAD`.
> 4. `apply` en simulación, revisa, y luego `apply --yes`.
> 5. `verify` de cada mapa/misión.
> 6. Si algo falla: `restore`, lee el log, ajusta la lista y repite.
> 7. Al terminar: actualiza `data/<modo>/keep-paks.txt`, escribe un manifiesto legible
>    de lo movido y deja un script para restaurar paks desde el ZIP original.
>
> ### Entregables
>
> - Ruleset en `rules/<modo>.json` con estado (`validated` o `template`).
> - Listas en `data/<modo>/` con el número de archivos y el tamaño que ahorran.
> - Un informe con: build usado, mapas probados, tiempo jugado, errores encontrados,
>   archivos restaurados y tamaño final.
> - Confirmación explícita de que `restore` devuelve la instalación a su estado previo.
>
> ### Ejemplo por modo
>
> ```bash
> # Zombies
> python3 iwslim.py trace  --game <RUTA> --map cp_zmb --duration 150
> python3 iwslim.py plan   --game <RUTA> --mode zombies --trace traces/trace.txt
> python3 iwslim.py verify --game <RUTA> --maps cp_zmb,cp_rave,cp_disco,cp_final,cp_town
>
> # Multijugador (traza menú + cada mapa que se juegue)
> python3 iwslim.py trace  --game <RUTA> --map mp_frontend --duration 180
> python3 iwslim.py trace  --game <RUTA> --map mp_<mapa> --duration 300
> cat traces/*.txt > traces/mp_all.txt
> python3 iwslim.py plan   --game <RUTA> --mode multiplayer --trace traces/mp_all.txt
>
> # Campaña (una traza por misión que se conserve)
> python3 iwslim.py trace  --game <RUTA> --map <nivel> --duration 420
> python3 iwslim.py plan   --game <RUTA> --mode campaign --trace traces/<nivel>.txt
> ```
>
> ### Lo que NO debes hacer
>
> - Convertir "archivos no vistos en una traza" en lista de borrado sin validar.
> - Mezclar recortes de varios modos en la misma cuarentena.
> - Tocar `players2/` (configuración, nombre, progreso).
> - Reportar éxito sin haber jugado al menos una partida completa del modo.

---

## Variante: modo "solo medir"

Si el usuario solo quiere saber cuánto puede ahorrar, el agente debe ejecutar `scan` y
`plan` y **detenerse ahí**. `plan` no modifica nada; es seguro mostrarlo como informe.

## Variante: Windows

`scan`, `plan`, `apply` y `restore` funcionan en Windows. `trace` y `verify` son solo
Linux (usan `inotifywait` y `xdotool`). En Windows:

- Sustituye la traza por `Process Monitor` (filtro `Path contains iw7`) y exporta a CSV;
  convierte las rutas a relativas con `\t` como separador para `--trace`.
- Verifica a mano: arranca, juega un mapa, revisa `console.log`.
