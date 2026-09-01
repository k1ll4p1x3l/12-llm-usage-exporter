from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VERIFIER = REPO_ROOT / "scripts/verify_release_artifacts.py"
PLATFORMS = (
    ("linux", "amd64"),
    ("linux", "arm64"),
    ("darwin", "amd64"),
    ("darwin", "arm64"),
    ("windows", "amd64"),
    ("windows", "arm64"),
)
COMMON_FILES = {
    "LICENSE": b"license\n",
    "README.md": b"readme\n",
    "CHANGELOG.md": b"changes\n",
    "examples/llm-usage-exporter.yaml": b"providers: []\n",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_tar(path: Path, binary: bytes = b"binary\n", traversal: bool = False) -> None:
    members = dict(COMMON_FILES)
    members["llm-usage-exporter"] = binary
    if traversal:
        members["../escape"] = b"escape\n"
    with tarfile.open(path, "w:gz") as archive:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o755 if name == "llm-usage-exporter" else 0o644
            archive.addfile(info, io.BytesIO(data))


def write_zip(path: Path) -> None:
    members = dict(COMMON_FILES)
    members["llm-usage-exporter.exe"] = b"binary\n"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, data in members.items():
            archive.writestr(name, data)


class ReleaseArtifactContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.dist = Path(self.temporary_directory.name) / "dist"
        self.dist.mkdir()
        self.artifacts: list[dict] = []
        self.archives: list[Path] = []

        for goos, goarch in PLATFORMS:
            extension = ".zip" if goos == "windows" else ".tar.gz"
            archive = self.dist / f"llm-usage-exporter_0.0.0_{goos}_{goarch}{extension}"
            if goos == "windows":
                write_zip(archive)
            else:
                write_tar(archive)
            self.archives.append(archive)
            self.artifacts.append(
                {
                    "name": archive.name,
                    "path": archive.name,
                    "goos": goos,
                    "goarch": goarch,
                    "type": "Archive",
                }
            )
            sbom = self.dist / f"{archive.name}.sbom.json"
            sbom.write_text(
                json.dumps(
                    {
                        "spdxVersion": "SPDX-2.3",
                        "packages": [{"name": "llm-usage-exporter"}],
                    }
                ),
                encoding="utf-8",
            )
            self.artifacts.append(
                {
                    "name": sbom.name,
                    "path": sbom.name,
                    "goos": goos,
                    "goarch": goarch,
                    "type": "SBOM",
                }
            )

        checksum = self.dist / "checksums.txt"
        checksum.write_text(
            "".join(f"{digest(path)}  {path.name}\n" for path in self.archives),
            encoding="utf-8",
        )
        self.artifacts.append(
            {"name": checksum.name, "path": checksum.name, "type": "Checksum"}
        )
        self.write_metadata()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def write_metadata(self) -> None:
        (self.dist / "artifacts.json").write_text(
            json.dumps(self.artifacts), encoding="utf-8"
        )

    def refresh_checksums(self) -> None:
        (self.dist / "checksums.txt").write_text(
            "".join(f"{digest(path)}  {path.name}\n" for path in self.archives),
            encoding="utf-8",
        )

    def run_verifier(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VERIFIER), "--dist", str(self.dist)],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )

    def test_complete_matrix_archives_sboms_and_checksums_pass(self) -> None:
        result = self.run_verifier()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("archives=6 sboms=6", result.stdout)

    def test_traversal_member_fails_even_with_current_checksum(self) -> None:
        linux_archive = self.archives[0]
        write_tar(linux_archive, traversal=True)
        self.refresh_checksums()
        result = self.run_verifier()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsafe tar member", result.stderr)

    def test_missing_sbom_fails_closed(self) -> None:
        removed = next(item for item in self.artifacts if item["type"] == "SBOM")
        self.artifacts.remove(removed)
        self.write_metadata()
        result = self.run_verifier()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exactly one SBOM", result.stderr)

    def test_symlinked_artifact_fails_closed(self) -> None:
        archive = self.archives[0]
        target = archive.with_name("regular-target.tar.gz")
        archive.rename(target)
        archive.symlink_to(target.name)
        self.refresh_checksums()
        result = self.run_verifier()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symbolic link", result.stderr)

    def test_checksum_path_escape_fails_closed(self) -> None:
        checksum_entry = next(
            item for item in self.artifacts if item["type"] == "Checksum"
        )
        checksum_entry["path"] = "../checksums.txt"
        self.write_metadata()
        result = self.run_verifier()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsafe artifact path", result.stderr)


if __name__ == "__main__":
    unittest.main()
