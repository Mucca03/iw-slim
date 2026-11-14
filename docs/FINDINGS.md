# Hallazgos técnicos

> Versión en inglés: [FINDINGS-ENG.md](FINDINGS-ENG.md).

Evidencia recogida durante la reducción real de una instalación de Infinite Warfare
(`iw7-mod` v1.0.2-144-g78d1a0a) en Linux/Wine.
No son opiniones: cada punto se comprobó en la instalación o en `console.log`.

## 1. El idioma se controla en el ejecutable de iw7-mod

- `iw7-mod.exe` contiene el literal `english` en el offset `0x357b18`.
- Parchearlo a `spanish` hace que el juego cargue `spanish/` y no `english/`.
- **`-noupdate` es obligatorio**: sin él, el actualizador restaura el ejecutable y el
  idioma vuelve a inglés.
- Consecuencia para el recorte: la carpeta del idioma **no activo** es prescindible.

## 2. `english/` se puede vaciar, pero no borrar

- Con el idioma en español se registraron **0 aperturas** de archivos de `english/`
  en los 5 mapas (`inotifywait`).
- La carpeta contiene ~11.7 GB de localizaciones (zonas + audio) que nunca se leen.
- Si se borra la carpeta, el juego **se cuelga al arrancar**. Si se vacía y se deja la
  carpeta, arranca sin avisos de idioma.
- Regla: `english/` vacía y presente.

## 3. `assetfile21.pak` es obligatorio por la precarga de caches

- Al entrar a un mapa no hace falta, por eso el juego funcionó **una hora** sin él.
- Al dejar terminar la precarga completa: `Could not find asset file assetfile21.pak`
  y `Fatal Error`.
- Restaurado el pak (944 MB), la precarga terminó limpia.
- Regla: no entra en la lista de paks prescindibles.

## 4. La precarga de caches recorre TODOS los `techsets_*`

- El log muestra `Loading zone techsets_*` para campaña, MP y zombies, uno por uno.
- Por eso un `techsets_*` de campaña puede referenciar un pak que sí se usa.
- Los `techsets_*` son pequeños: conservarlos siempre.

## 5. Qué comparten los mapas de Zombies con MP

Los mapas zombie usan assets de MP. Lo que **no** se debe borrar aunque parezca de MP:

- `mp_weapon_*` (`world`, `view`, variantes `_tr`), `mp_head_*`, `mp_body_*`,
  `mp_viewhands_*`, `mp_fullbody*`.
- `livery_*`.
- Zonas `common*`, `global*`, `cp_*`, `zombies_*` y todos los `techsets_*`.
- `sysload_*` y `sysmain*` (vídeos de carga/menú).

## 6. Estructura de zonas y sonido

- Cada zona `X.ff` puede tener `X.sabl` (índice) y `X.sabs` (datos), pero no siempre.
- Un `.ff` conservado con su `.sabl`/`.sabs` movido es sospechoso; el plan avisa.
- `common_core_mp.sabs` es diminuto (4 KB) y `common_core_mp.sabl` es grande
  (352 MB): el tamaño no indica importancia.

## 7. Paks: qué se abrió de verdad

- La instalación trae `assetfile*.pak` e `imagefile*.pak`.
- Muchos paks son de campaña/MP y ningún mapa zombie los abre.
- Tras los cortes quedaron **33 paks** en disco (incluido `assetfile21.pak`).
- La lista exacta está en `data/zombies/keep-paks.txt`.

## 8. Logs y diagnóstico

- Log de ejecución: `iw7-mod/logs/console.log`.
- Mensajes útiles:
  - `Could not find asset file X.pak` → falta un pak.
  - `Tried to load missing language zone ...` → idioma/carpeta mal.
  - `Could not find fx "..."` → efecto ausente; en la práctica no impidió jugar.
  - `Loading zone <nombre>` → zona cargada (útil para saber el orden real).
- Las ventanas de error se detectan con `xdotool search --name "Fatal Error"`.

## 9. Wine en Linux

- Tras matar el juego, Wine puede quedarse colgado; `wineserver -k` y esperar antes de
  relanzar.
- Los lanzamientos automáticos deben matar el proceso al terminar (`iwslim verify` lo hace).
- El juego recrea archivos temporales en el prefijo (`Temp/iw7-tlsdll.dll`); son
  prescindibles y se regeneran.

## 10. Resultado medido

| Concepto | Antes | Después |
|---|---:|---:|
| Instalación | ~131.34 GB | **51.59 GB** |
| Paks en disco | 100 | 33 |
| `english/` | 11.7 GB | 0 B (carpeta presente) |
| Mapas zombie probados | — | 5/5 |
| Tiempo de juego validado | — | ~1 h en `cp_zmb` sin fallos |

El ZIP original (112.5 GB) se conservó como red de seguridad durante la validación;
con `iwslim restore --from-zip` se puede recuperar cualquier pak suelto.
