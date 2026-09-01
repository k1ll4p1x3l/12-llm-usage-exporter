from __future__ import annotations

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = (
    REPO_ROOT / "scripts/bootstrap-github-org.sh",
    REPO_ROOT / "scripts/bootstrap-github-settings.sh",
)


class GitHubPreviewContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.fake_bin = self.root / "bin"
        self.fake_bin.mkdir()
        self.marker = self.root / "gh-called"
        fake_gh = self.fake_bin / "gh"
        fake_gh.write_text(
            "#!/bin/sh\nprintf called >\"$GH_CALLED_MARKER\"\nexit 91\n",
            encoding="utf-8",
        )
        fake_gh.chmod(0o755)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def run_script(self, script: Path, **overrides: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.update(
            {
                "PATH": f"{self.fake_bin}:/usr/bin:/bin",
                "GH_CALLED_MARKER": str(self.marker),
                "GITHUB_REPO": "example/llm-usage-exporter",
                "DRY_RUN": "1",
            }
        )
        environment.update(overrides)
        return subprocess.run(
            ["/bin/bash", str(script)],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
            timeout=10,
        )

    def test_preview_never_invokes_gh(self) -> None:
        for script in SCRIPTS:
            with self.subTest(script=script.name):
                result = self.run_script(script, REQUIRE_BRANCH_PROTECTION="1")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("[preview]", result.stdout)
                self.assertIn("no network call", result.stdout.lower())
                self.assertFalse(self.marker.exists())

    def test_apply_mode_fails_before_any_tool_call(self) -> None:
        for script in SCRIPTS:
            with self.subTest(script=script.name):
                result = self.run_script(script, DRY_RUN="0")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("preview-only", result.stderr)
                self.assertFalse(self.marker.exists())

    def test_untrusted_identifiers_and_json_fail_closed(self) -> None:
        for script in SCRIPTS:
            with self.subTest(script=script.name):
                invalid_repo = self.run_script(
                    script, GITHUB_REPO="example/repo;touch-injection"
                )
                self.assertNotEqual(invalid_repo.returncode, 0)
                invalid_json = self.run_script(
                    script, REQUIRED_STATUS_CHECKS_JSON="not-json"
                )
                if script.name == "bootstrap-github-org.sh":
                    invalid_json = self.run_script(
                        script, REQUIRED_STATUS_CHECKS_JSON_OVERRIDE="not-json"
                    )
                self.assertNotEqual(invalid_json.returncode, 0)
                self.assertFalse(self.marker.exists())

    def test_scripts_have_no_dynamic_shell_evaluation(self) -> None:
        for script in SCRIPTS:
            content = script.read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"\beval\b", content), script.name)
            self.assertNotIn("bash -c", content)
            self.assertNotIn("sh -c", content)


if __name__ == "__main__":
    unittest.main()
