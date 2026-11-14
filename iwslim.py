#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""iwslim - recorta una instalación de Call of Duty: Infinite Warfare por modo.

Filosofía de seguridad
----------------------
* Nada se borra: lo que sobra se MUEVE a una carpeta de cuarentena.
* Las listas de recorte son explícitas, versionadas y reversibles.
* Lo que no aparece en una lista se conserva (nunca se adivina).
* La carpeta ``english/`` se vacía pero se conserva: el juego se cuelga si falta.

Uso rápido
----------
    python3 iwslim.py scan  --game /ruta/iw
    python3 iwslim.py plan  --game /ruta/iw --mode zombies --out plan.json
    python3 iwslim.py apply --plan plan.json --yes
    python3 iwslim.py restore --manifest /ruta/iw_cuarentena/manifest.json
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

VERSION = "0.1.0"

ROOT = Path(__file__).resolve().parent
RULES_DIR = ROOT / "rules"
DATA_DIR = ROOT / "data"

GAME_BINARIES = ("iw7-mod.exe", "iw7_ship.exe")

#: Motivo legible para cada lista de borrado.
LIST_REASONS = {
    "remove-root.txt": "zona de campaña/multijugador (verificada como no usada por Zombies)",
    "remove-videos.txt": "vídeo no usado por Zombies",
    "remove-paks.txt": "pak de campaña/multijugador (ningún mapa zombie lo abre)",
}

_EXT_CATEGORY = {
    ".ff": "zonas",
    ".sabl": "sonido",
    ".sabs": "sonido",
    ".pak": "paks",
    ".bik": "vídeos",
    ".exe": "binarios",
    ".dll": "binarios",
    ".bat": "scripts",
    ".sh": "scripts",
    ".pid": "runtime",
    ".vdf": "metadata",
    ".url": "metadata",
}


# --------------------------------------------------------------------------- #
# utilidades
# --------------------------------------------------------------------------- #
def human(n: float) -> str:
    """Tamaño legible (base 1024)."""
    n = float(n)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(n) < 1024 or unit == "TiB":
            if unit == "B":
                return f"{int(n)} B"
            return f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} TiB"


def eprint(*args, **kwargs) -> None:
    print(*args, file=sys.stderr, **kwargs)


_GLOB_CACHE: dict[str, re.Pattern[str]] = {}


def _glob_re(pattern: str) -> re.Pattern[str]:
    """Convierte un glob (con ``**``) a regex anclada a ruta POSIX."""
    if pattern in _GLOB_CACHE:
        return _GLOB_CACHE[pattern]
    out: list[str] = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    compiled = re.compile("^" + "".join(out) + "$")
    _GLOB_CACHE[pattern] = compiled
    return compiled


def match_any(rel: str, patterns: list[str]) -> bool:
    return any(_glob_re(p).match(rel) for p in patterns)


def iter_files(game: Path):
    for path in game.rglob("*"):
        if path.is_file():
            yield path


def load_rules(mode: str) -> dict:
    path = RULES_DIR / f"{mode}.json"
    if not path.is_file():
        raise SystemExit(f"No existe el ruleset '{path}'. Modos disponibles: "
                         + ", ".join(p.stem for p in RULES_DIR.glob("*.json")))
    return json.loads(path.read_text(encoding="utf-8"))


def read_list(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    names = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        # admite comentarios al final de la línea: "archivo.pak  # nota"
        line = line.split("  #", 1)[0].strip()
        if line and not line.startswith("#"):
            names.add(line)
    return names


def is_game_running() -> bool:
    if os.name == "nt":
        try:
            out = subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()
        except OSError:
            return False
        return any(name in out for name in GAME_BINARIES)
    try:
        proc = subprocess.run(["pgrep", "-x", GAME_BINARIES[0]], capture_output=True)
    except FileNotFoundError:
        return False
    return proc.returncode == 0


# --------------------------------------------------------------------------- #
# inventario y plan
# --------------------------------------------------------------------------- #
@dataclass
class Action:
    path: str
    size: int
    action: str  # keep | quarantine
    reason: str


@dataclass
class Plan:
    mode: str
    game: str
    created: str
    actions: list[Action] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = asdict(self)
        return data


def build_plan(game: Path, mode: str, trace: Path | None = None,
               keep_english: bool = False) -> Plan:
    rules = load_rules(mode)
    protected = list(rules.get("protected_globs", []))
    remove_dirs = [] if keep_english else list(rules.get("remove_dirs", []))

    remove_sets: dict[str, set[str]] = {}
    for name in rules.get("remove_lists", []):
        remove_sets[name] = read_list(DATA_DIR / mode / name)
    keep_sets: dict[str, set[str]] = {}
    for name in rules.get("keep_lists", []):
        keep_sets[name] = read_list(DATA_DIR / mode / name)

    trace_set: set[str] = set()
    if trace and trace.is_file():
        for line in trace.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            trace_set.add(line.split("\t", 1)[0])

    plan = Plan(mode=mode, game=str(game), created=datetime.now(timezone.utc).isoformat())
    paks_kept: set[str] = set()

    for path in iter_files(game):
        rel = path.relative_to(game).as_posix()
        size = path.stat().st_size
        top = rel.split("/", 1)[0]

        reason: str | None = None
        if top in remove_dirs and "/" in rel:
            reason = "localización inglesa (no se usa con el idioma en español)"
        elif not match_any(rel, protected):
            for name, names in remove_sets.items():
                if rel in names:
                    reason = LIST_REASONS.get(name, f"lista de borrado: {name}")
                    break

        if reason:
            plan.actions.append(Action(rel, size, "quarantine", reason))
        else:
            plan.actions.append(Action(rel, size, "keep", "necesario o no listado"))

        if rel.endswith(".pak") and reason is None:
            paks_kept.add(rel)

    # ------------------------- comprobaciones de seguridad -------------------------
    english_dir = game / "english"
    if not english_dir.is_dir():
        plan.warnings.append(
            "No existe la carpeta 'english/'. El juego se cuelga al arrancar si falta: "
            "créala vacía antes de jugar."
        )
    elif any(a.action == "quarantine" and a.path.startswith("english/")
             for a in plan.actions):
        plan.warnings.append(
            "Se va a vaciar 'english/'. Esto solo es correcto si el juego NO está en inglés."
        )

    verified_paks = keep_sets.get("keep-paks.txt", set())
    if verified_paks:
        for pak in sorted(paks_kept - verified_paks):
            plan.warnings.append(f"Pak conservado pero NO verificado por las pruebas: {pak}")

    # bancos de sonido huérfanos (zona conservada sin su .sabl/.sabs, o al revés)
    action_by_path = {a.path: a for a in plan.actions}
    for action in plan.actions:
        if not action.path.endswith(".ff"):
            continue
        base = action.path[:-3]
        sound = [base + ".sabl", base + ".sabs"]
        if action.action == "keep":
            for s in sound:
                other = action_by_path.get(s)
                if other and other.action == "quarantine":
                    plan.warnings.append(
                        f"Zona '{action.path}' conservada pero '{s}' se movería (¿sonido huérfano?)."
                    )
        else:
            for s in sound:
                other = action_by_path.get(s)
                if other and other.action == "keep" and (action.path.endswith(".ff")):
                    # es normal en zonas sin banco propio; solo avisar de .sabs grandes
                    pass

    if trace_set:
        for rel in sorted(trace_set):
            act = action_by_path.get(rel)
            if act and act.action == "quarantine":
                plan.warnings.append(
                    f"SEGURIDAD: la traza abrió '{rel}' pero el plan lo movería."
                )

    # ------------------------------- resumen -------------------------------
    q = [a for a in plan.actions if a.action == "quarantine"]
    k = [a for a in plan.actions if a.action == "keep"]
    plan.summary = {
        "files_total": len(plan.actions),
        "files_keep": len(k),
        "files_quarantine": len(q),
        "bytes_total": sum(a.size for a in plan.actions),
        "bytes_keep": sum(a.size for a in k),
        "bytes_quarantine": sum(a.size for a in q),
    }
    return plan


# --------------------------------------------------------------------------- #
# comandos
# --------------------------------------------------------------------------- #
def cmd_scan(args) -> int:
    game = Path(args.game).resolve()
    if not game.is_dir():
        raise SystemExit(f"No existe la carpeta del juego: {game}")

    by_cat: collections.Counter[str] = collections.Counter()
    size_cat: collections.Counter[str] = collections.Counter()
    total = 0
    files = 0
    for path in iter_files(game):
        rel = path.relative_to(game)
        size = path.stat().st_size
        ext = path.suffix.lower()
        cat = _EXT_CATEGORY.get(ext, "otros")
        if rel.parts and rel.parts[0] in ("english", "spanish"):
            cat = f"idioma:{rel.parts[0]}"
        by_cat[cat] += 1
        size_cat[cat] += size
        total += size
        files += 1

    print(f"Juego: {game}")
    print(f"Archivos: {files}   Total: {human(total)}\n")
    print(f"{'categoría':<22}{'archivos':>10}{'tamaño':>14}")
    print("-" * 46)
    for cat, _ in size_cat.most_common():
        print(f"{cat:<22}{by_cat[cat]:>10}{human(size_cat[cat]):>14}")

    if args.json:
        data = {
            "game": str(game),
            "files": files,
            "bytes": total,
            "categories": {
                cat: {"files": by_cat[cat], "bytes": size_cat[cat]}
                for cat in size_cat
            },
        }
        Path(args.json).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nInventario escrito en {args.json}")
    return 0


def cmd_plan(args) -> int:
    game = Path(args.game).resolve()
    plan = build_plan(game, args.mode, Path(args.trace) if args.trace else None,
                      keep_english=args.keep_english)
    if args.out:
        Path(args.out).write_text(
            json.dumps(plan.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )

    s = plan.summary
    print(f"Modo: {plan.mode}   Juego: {game}")
    print(f"Archivos: {s['files_total']}   "
          f"conservar: {s['files_keep']} ({human(s['bytes_keep'])})   "
          f"mover: {s['files_quarantine']} ({human(s['bytes_quarantine'])})")
    print(f"Quedaría en: {human(s['bytes_keep'])} (de {human(s['bytes_total'])})")

    q = sorted((a for a in plan.actions if a.action == "quarantine"),
               key=lambda a: a.size, reverse=True)
    if q:
        print("\nMayores recortes:")
        for a in q[:10]:
            print(f"  {human(a.size):>10}  {a.path}  — {a.reason}")

    if plan.warnings:
        print("\nAvisos:")
        for w in plan.warnings:
            print(f"  ! {w}")
    if args.out:
        print(f"\nPlan escrito en {args.out}")
    return 0


def cmd_apply(args) -> int:
    plan_data = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    game = Path(plan_data["game"]).resolve()
    mode = plan_data["mode"]

    if is_game_running() and not args.force:
        raise SystemExit("El juego parece estar abierto. Ciérralo o usa --force.")

    todo = [a for a in plan_data["actions"] if a["action"] == "quarantine"]
    total = sum(a["size"] for a in todo)
    quarantine = (Path(args.quarantine).resolve() if args.quarantine
                  else game.parent / f"iwslim_quarantine_{mode}")

    print(f"Cuarentena: {quarantine}")
    print(f"Se moverán {len(todo)} archivos ({human(total)}).")
    if not args.yes:
        print("\nModo simulación: no se movió nada. Repite con --yes para aplicar.")
        return 0

    quarantine.mkdir(parents=True, exist_ok=True)
    moved: list[dict] = []
    errors: list[str] = []

    for item in todo:
        rel = item["path"]
        src = game / rel
        if not src.is_file():
            errors.append(f"no existe: {rel}")
            continue
        dst = quarantine / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            dst = dst.with_name(dst.name + ".dup")
        try:
            shutil.move(str(src), str(dst))
        except OSError as exc:
            errors.append(f"{rel}: {exc}")
            continue
        moved.append({"path": rel, "size": item["size"], "reason": item["reason"]})

    manifest = {
        "tool": "iwslim",
        "version": VERSION,
        "mode": mode,
        "game": str(game),
        "quarantine": str(quarantine),
        "created": datetime.now(timezone.utc).isoformat(),
        "files": moved,
    }
    (quarantine / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (quarantine / "restore.py").write_text(_RESTORE_PY, encoding="utf-8")
    (quarantine / "LEEME.txt").write_text(
        "Cuarentena creada por iwslim.\n\n"
        "Para devolver TODOS los archivos al juego:\n"
        f"    python3 {quarantine / 'restore.py'}\n\n"
        "O con la herramienta:\n"
        f"    python3 {ROOT / 'iwslim.py'} restore --manifest {quarantine / 'manifest.json'}\n",
        encoding="utf-8",
    )

    moved_bytes = sum(m["size"] for m in moved)
    print(f"\nMovidos {len(moved)} archivos ({human(moved_bytes)}).")
    if errors:
        print(f"Errores: {len(errors)}")
        for e in errors[:10]:
            print(f"  ! {e}")
    print(f"Manifiesto: {quarantine / 'manifest.json'}")
    return 0 if not errors else 1


_RESTORE_PY = '''#!/usr/bin/env python3
"""Devuelve esta cuarentena a la carpeta del juego.

Uso: python3 restore.py [--overwrite]
"""
import json
import shutil
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
manifest = json.loads((here / "manifest.json").read_text(encoding="utf-8"))
game = Path(manifest["game"])
overwrite = "--overwrite" in sys.argv

restored = 0
for item in manifest["files"]:
    src = here / item["path"]
    dst = game / item["path"]
    if not src.exists():
        print("Falta en cuarentena:", item["path"])
        continue
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and not overwrite:
        print("Ya existe (usa --overwrite):", item["path"])
        continue
    shutil.move(str(src), str(dst))
    restored += 1

print(f"Restaurados {restored} archivos en {game}")
'''


def cmd_restore(args) -> int:
    game: Path
    files: list[dict] = []

    if args.manifest:
        manifest_path = Path(args.manifest).resolve()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        quarantine = manifest_path.parent
        game = Path(args.game).resolve() if args.game else Path(manifest["game"])
        files = [{"path": f["path"], "size": f.get("size", 0)} for f in manifest["files"]]
    elif args.files and args.from_zip:
        game = Path(args.game).resolve()
        quarantine = Path(args.quarantine).resolve() if args.quarantine else Path(".")
        files = [{"path": name, "size": 0} for name in args.files]
    else:
        raise SystemExit("Usa --manifest, o bien --from-zip junto con --files.")

    if args.only:
        files = [f for f in files if _glob_re(args.only).match(f["path"])]

    restored = 0
    missing: list[str] = []
    for item in files:
        rel = item["path"]
        src = quarantine / rel
        dst = game / rel
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists() and not args.overwrite:
                print(f"Ya existe en el juego: {rel}")
                continue
            shutil.move(str(src), str(dst))
            restored += 1
        else:
            missing.append(rel)

    if missing and args.from_zip:
        restored += _restore_from_zip(Path(args.from_zip), missing, game)

    print(f"Restaurados {restored} archivos en {game}")
    if missing and not args.from_zip:
        print("No estaban en la cuarentena:")
        for rel in missing[:20]:
            print(f"  - {rel}")
        print("Puedes recuperarlos del ZIP original con --from-zip.")
    return 0


def _restore_from_zip(zip_path: Path, names: list[str], game: Path) -> int:
    if not zip_path.is_file():
        raise SystemExit(f"No existe el ZIP: {zip_path}")
    restored = 0
    with zipfile.ZipFile(zip_path) as zf:
        members = {Path(n).as_posix(): n for n in zf.namelist() if not n.endswith("/")}
        by_base = collections.defaultdict(list)
        for posix, member in members.items():
            by_base[Path(posix).name].append(member)

        for rel in names:
            member = members.get(rel)
            if member is None:
                candidates = by_base.get(Path(rel).name, [])
                if len(candidates) == 1:
                    member = candidates[0]
            if member is None:
                print(f"No está en el ZIP: {rel}")
                continue
            dst = game / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, open(dst, "wb") as out:
                shutil.copyfileobj(src, out)
            print(f"Extraído del ZIP: {rel}")
            restored += 1
    return restored


def cmd_trace(args) -> int:
    if os.name == "nt":
        raise SystemExit("El modo trace solo está disponible en Linux (inotifywait).")
    if not shutil.which("inotifywait"):
        raise SystemExit("Falta inotifywait (paquete inotify-tools).")

    game = Path(args.game).resolve()
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    raw = out.with_suffix(out.suffix + ".raw")

    trace = subprocess.Popen(
        ["inotifywait", "-m", "-r", "-e", "open,access", "--format", "%w%f",
         "-o", str(raw), str(game)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    launch = args.cmd or (
        f"wine iw7-mod.exe -nosteam -noupdate -stdout -cpMode +map {args.map}"
    )
    print(f"Lanzando: {launch}")
    print(f"Traza durante {args.duration}s -> {out}")
    game_proc = subprocess.Popen(shlex.split(launch), cwd=game,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(args.duration)
    finally:
        _kill_game()
        time.sleep(2)
        trace.terminate()
        try:
            trace.wait(timeout=5)
        except subprocess.TimeoutExpired:
            trace.kill()

    counts: collections.Counter[str] = collections.Counter()
    if raw.is_file():
        for line in raw.read_text(encoding="utf-8", errors="replace").splitlines():
            p = Path(line.strip())
            try:
                rel = p.resolve().relative_to(game).as_posix()
            except (ValueError, OSError):
                continue
            counts[rel] += 1
    raw.unlink(missing_ok=True)

    with open(out, "w", encoding="utf-8") as fh:
        fh.write(f"# iwslim trace  {datetime.now(timezone.utc).isoformat()}\n")
        fh.write(f"# map={args.map}  duration={args.duration}s\n")
        fh.write("# ruta_relativa<TAB>aperturas\n")
        for rel, n in sorted(counts.items()):
            fh.write(f"{rel}\t{n}\n")

    print(f"Archivos distintos vistos: {len(counts)}")
    print(f"Traza escrita en {out}")
    return 0


def _kill_game() -> None:
    if os.name == "nt":
        for name in GAME_BINARIES:
            subprocess.run(["taskkill", "/F", "/IM", name], capture_output=True)
        return
    subprocess.run(["pkill", "-x", "iw7-mod.exe"], capture_output=True)
    subprocess.run(["pkill", "-x", "iw7_ship.exe"], capture_output=True)


def cmd_verify(args) -> int:
    if os.name == "nt":
        raise SystemExit("El modo verify solo está disponible en Linux (wine + xdotool).")
    game = Path(args.game).resolve()
    maps = [m.strip() for m in args.maps.split(",") if m.strip()]
    console = game / "iw7-mod" / "logs" / "console.log"
    results = []

    for map_name in maps:
        print(f"\n=== {map_name} ===")
        _kill_game()
        if shutil.which("wineserver"):
            subprocess.run(["wineserver", "-k"], capture_output=True)
        time.sleep(4)
        if console.exists():
            console.unlink()
        launch = (args.cmd or "wine iw7-mod.exe -nosteam -noupdate -stdout -cpMode "
                  f"+map {map_name}")
        subprocess.Popen(shlex.split(launch), cwd=game,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(args.wait)

        problems: list[str] = []
        if console.exists():
            text = console.read_text(encoding="utf-8", errors="replace")
            for needle in ("Could not find asset file", "MISSING FILE",
                           "Tried to load missing language zone"):
                hits = [ln for ln in text.splitlines() if needle in ln]
                if hits:
                    problems.extend(hits[:5])
        else:
            problems.append("no se creó console.log (¿arrancó?)")

        if shutil.which("xdotool"):
            fatal = subprocess.run(
                ["xdotool", "search", "--onlyvisible", "--name", "Fatal Error"],
                capture_output=True, text=True,
            )
            if fatal.stdout.strip():
                problems.append("ventana 'Fatal Error' visible")

        ok = not problems
        results.append((map_name, ok, problems))
        print("OK" if ok else "FALLÓ")
        for p in problems[:8]:
            print(f"  ! {p}")

        _kill_game()
        time.sleep(3)

    bad = [r for r in results if not r[1]]
    print("\nResumen:", ", ".join(f"{m}={'OK' if ok else 'FALLO'}" for m, ok, _ in results))
    return 0 if not bad else 1


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="iwslim",
        description="Recorta una instalación de Infinite Warfare por modo, de forma reversible.",
    )
    parser.add_argument("--version", action="version", version=f"iwslim {VERSION}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("scan", help="inventario de la instalación")
    p.add_argument("--game", required=True)
    p.add_argument("--json", help="escribir inventario JSON")
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("plan", help="calcular qué se conserva y qué se mueve")
    p.add_argument("--game", required=True)
    p.add_argument("--mode", default="zombies", help="ruleset a usar (rules/<modo>.json)")
    p.add_argument("--out", help="escribir el plan en JSON")
    p.add_argument("--trace", help="traza de archivos abiertos (modo trace) para validar")
    p.add_argument("--keep-english", action="store_true",
                   help="no vaciar english/ (obligatorio si el juego está en inglés)")
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("apply", help="mover a cuarentena lo que marque el plan")
    p.add_argument("--plan", required=True)
    p.add_argument("--quarantine", help="carpeta de cuarentena (por defecto, junto al juego)")
    p.add_argument("--yes", action="store_true", help="aplicar de verdad (sin esto es simulación)")
    p.add_argument("--force", action="store_true", help="aplicar aunque el juego esté abierto")
    p.set_defaults(func=cmd_apply)

    p = sub.add_parser("restore", help="devolver archivos desde la cuarentena o el ZIP")
    p.add_argument("--manifest", help="manifest.json de la cuarentena")
    p.add_argument("--quarantine", help="carpeta de cuarentena (con --files)")
    p.add_argument("--from-zip", help="ZIP con los archivos originales del juego")
    p.add_argument("--files", nargs="+", help="archivos sueltos a restaurar desde el ZIP")
    p.add_argument("--game", help="carpeta del juego (si no está en el manifiesto)")
    p.add_argument("--only", help="restaurar solo rutas que casen con este glob")
    p.add_argument("--overwrite", action="store_true")
    p.set_defaults(func=cmd_restore)

    p = sub.add_parser("trace", help="grabar qué archivos abre el juego (Linux)")
    p.add_argument("--game", required=True)
    p.add_argument("--map", default="cp_zmb")
    p.add_argument("--duration", type=int, default=150)
    p.add_argument("--out", default="traces/trace.txt")
    p.add_argument("--cmd", help="comando de lanzamiento alternativo")
    p.set_defaults(func=cmd_trace)

    p = sub.add_parser("verify", help="lanzar mapas y detectar archivos faltantes (Linux)")
    p.add_argument("--game", required=True)
    p.add_argument("--maps", default="cp_zmb")
    p.add_argument("--wait", type=int, default=120, help="segundos de espera por mapa")
    p.add_argument("--cmd", help="comando de lanzamiento alternativo")
    p.set_defaults(func=cmd_verify)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
