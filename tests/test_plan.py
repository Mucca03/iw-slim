import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import iwslim  # noqa: E402


def _touch(path: Path, size: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)


class PlanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.game = Path(self.tmp.name) / "iw"
        (self.game / "english").mkdir(parents=True)
        (self.game / "iw7-mod").mkdir()

        _touch(self.game / "common_sp.ff", 10)            # lista remove-root
        _touch(self.game / "cp_zmb.ff", 20)               # se conserva
        _touch(self.game / "english" / "eng_common_sp.ff", 5)  # se vacía
        _touch(self.game / "assetfile21.pak", 7)          # se conserva (restaurado)
        _touch(self.game / "imagefile84.pak", 9)          # lista remove-paks
        _touch(self.game / "unknown.ff", 3)               # desconocido: se conserva
        _touch(self.game / "iw7-mod.exe", 4)              # protegido
        _touch(self.game / "README.txt", 1)               # protegido
        _touch(self.game / "iw7-mod" / "config.cfg", 2)   # protegido

    def tearDown(self):
        self.tmp.cleanup()

    def _plan(self, **kwargs):
        return iwslim.build_plan(self.game, "zombies", **kwargs)

    def test_clasificacion(self):
        plan = self._plan()
        act = {a.path: a.action for a in plan.actions}

        self.assertEqual(act["common_sp.ff"], "quarantine")
        self.assertEqual(act["imagefile84.pak"], "quarantine")
        self.assertEqual(act["english/eng_common_sp.ff"], "quarantine")
        self.assertEqual(act["cp_zmb.ff"], "keep")
        self.assertEqual(act["assetfile21.pak"], "keep")
        self.assertEqual(act["unknown.ff"], "keep")
        self.assertEqual(act["iw7-mod.exe"], "keep")
        self.assertEqual(act["README.txt"], "keep")
        self.assertEqual(act["iw7-mod/config.cfg"], "keep")

    def test_keep_english(self):
        plan = self._plan(keep_english=True)
        act = {a.path: a.action for a in plan.actions}
        self.assertEqual(act["english/eng_common_sp.ff"], "keep")

    def test_aviso_idioma(self):
        plan = self._plan()
        self.assertTrue(any("english/" in w or "inglés" in w for w in plan.warnings))

    def test_resumen(self):
        plan = self._plan()
        self.assertEqual(plan.summary["files_quarantine"], 3)
        self.assertEqual(plan.summary["bytes_quarantine"], 24)

    def test_aviso_paks_no_verificados(self):
        # un pak que se mueve no debe avisar de "conservado no verificado"
        plan = self._plan()
        self.assertFalse(any("imagefile84.pak" in w for w in plan.warnings))
        # uno conservado fuera de keep-paks.txt sí debe avisar
        _touch(self.game / "assetfile999.pak", 3)
        plan = self._plan()
        self.assertTrue(any("assetfile999.pak" in w for w in plan.warnings))

    def test_apply_y_restore(self):
        plan = self._plan()
        plan_path = Path(self.tmp.name) / "plan.json"
        plan_path.write_text(json.dumps(plan.to_dict()), encoding="utf-8")
        quarantine = Path(self.tmp.name) / "cuarentena"

        rc = iwslim.cmd_apply(argparse.Namespace(
            plan=str(plan_path), quarantine=str(quarantine), yes=True, force=True))
        self.assertEqual(rc, 0)
        self.assertFalse((self.game / "common_sp.ff").exists())
        self.assertTrue((quarantine / "common_sp.ff").exists())
        self.assertTrue((quarantine / "manifest.json").exists())
        # la carpeta english/ debe seguir existiendo (vacía)
        self.assertTrue((self.game / "english").is_dir())
        self.assertFalse((self.game / "english" / "eng_common_sp.ff").exists())

        rc = iwslim.cmd_restore(argparse.Namespace(
            manifest=str(quarantine / "manifest.json"), game=None, from_zip=None,
            files=None, only=None, overwrite=False, quarantine=None))
        self.assertEqual(rc, 0)
        self.assertTrue((self.game / "common_sp.ff").exists())
        self.assertTrue((self.game / "english" / "eng_common_sp.ff").exists())


if __name__ == "__main__":
    unittest.main()
