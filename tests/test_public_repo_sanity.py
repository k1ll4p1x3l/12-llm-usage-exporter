from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCANNER = REPO_ROOT / "scripts/public_repo_sanity_check.py"


class PublicRepositoryScannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def run_scan(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCANNER), "--root", str(self.root), *extra],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_clean_text_and_binary_file_pass(self) -> None:
        (self.root / "README.md").write_text("public example\n", encoding="utf-8")
        (self.root / "asset.bin").write_bytes(b"\x00\xff\x01")
        result = self.run_scan()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_secret_value_is_reported_but_never_echoed(self) -> None:
        secret = "ghp_" + ("A" * 32)
        (self.root / "config.go").write_text(
            f'package fixture\nconst value = "{secret}"\n', encoding="utf-8"
        )
        result = self.run_scan()
        self.assertEqual(result.returncode, 1)
        self.assertIn("GitHub token", result.stdout)
        self.assertNotIn(secret, result.stdout + result.stderr)

    def test_secret_in_binary_file_is_not_hidden_by_nul_bytes(self) -> None:
        secret = "github_pat_" + ("B" * 32)
        (self.root / "asset.bin").write_bytes(b"\x00prefix " + secret.encode() + b" suffix")
        result = self.run_scan()
        self.assertEqual(result.returncode, 1)
        self.assertIn("GitHub token", result.stdout)
        self.assertNotIn(secret, result.stdout + result.stderr)

    def test_private_path_and_symlink_fail_closed(self) -> None:
        private = self.root / "references/private"
        private.mkdir(parents=True)
        (private / "note.md").write_text("private\n", encoding="utf-8")
        outside = self.root / "outside.txt"
        outside.write_text("outside\n", encoding="utf-8")
        (self.root / "linked.txt").symlink_to(outside)
        result = self.run_scan()
        self.assertEqual(result.returncode, 1)
        self.assertIn("private reference path", result.stdout)
        self.assertIn("symbolic link", result.stdout)

    def test_extra_literal_is_escaped_and_bounded(self) -> None:
        (self.root / "note.txt").write_text("marker[not-regex]\n", encoding="utf-8")
        result = self.run_scan("--extra-literal", "marker[not-regex]")
        self.assertEqual(result.returncode, 1)
        self.assertIn("configured literal", result.stdout)
        invalid = self.run_scan("--extra-literal", "")
        self.assertEqual(invalid.returncode, 2)

    def test_symlink_scan_root_fails_closed(self) -> None:
        actual = self.root / "actual"
        actual.mkdir()
        linked = self.root / "linked"
        linked.symlink_to(actual, target_is_directory=True)
        result = subprocess.run(
            [sys.executable, str(SCANNER), "--root", str(linked)],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("non-symlink directory", result.stderr)


if __name__ == "__main__":
    unittest.main()
