#!/usr/bin/env python3
"""Verify the complete, unpublished GoReleaser archive and SBOM contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import tarfile
import zipfile
from pathlib import Path, PurePosixPath


EXPECTED_PLATFORMS = {
    ("linux", "amd64"),
    ("linux", "arm64"),
    ("darwin", "amd64"),
    ("darwin", "arm64"),
    ("windows", "amd64"),
    ("windows", "arm64"),
}
REQUIRED_ARCHIVE_FILES = {
    "LICENSE",
    "README.md",
    "CHANGELOG.md",
    "examples/llm-usage-exporter.yaml",
}
CONTROL_PATTERN = re.compile(r"[\x00-\x1f\x7f]")
CHECKSUM_PATTERN = re.compile(r"^([0-9a-f]{64})\s+\*?(.+)$")
MAX_ARTIFACTS = 100
MAX_ARTIFACT_SIZE = 256 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 100
MAX_ARCHIVE_UNCOMPRESSED = 512 * 1024 * 1024


class ContractError(ValueError):
    """A release contract violation."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_member_name(value: str, label: str) -> PurePosixPath:
    if not value or "\\" in value or CONTROL_PATTERN.search(value):
        raise ContractError(f"unsafe {label}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ContractError(f"unsafe {label}")
    return path


def canonical_dist(raw_dist: str) -> Path:
    candidate = Path(raw_dist).expanduser()
    try:
        if candidate.is_symlink() or not candidate.is_dir():
            raise ContractError("dist must be a non-symlink directory")
        return candidate.resolve(strict=True)
    except OSError as exc:
        raise ContractError(f"cannot resolve dist: {exc}") from exc


def resolve_artifact(dist: Path, raw_path: object) -> Path:
    if not isinstance(raw_path, str):
        raise ContractError("artifact path must be a string")
    relative = safe_member_name(raw_path, "artifact path")
    if relative.parts[0] == dist.name:
        candidate = dist.parent.joinpath(*relative.parts)
    else:
        candidate = dist.joinpath(*relative.parts)
    if not candidate.is_relative_to(dist):
        raise ContractError("artifact escapes dist")
    relative_parts = candidate.relative_to(dist).parts
    if not relative_parts:
        raise ContractError("artifact path points to dist itself")
    cursor = dist
    for index, part in enumerate(relative_parts):
        cursor /= part
        try:
            file_stat = cursor.lstat()
        except OSError as exc:
            raise ContractError(f"cannot inspect artifact {relative}: {exc}") from exc
        if stat.S_ISLNK(file_stat.st_mode):
            raise ContractError(f"artifact path contains a symbolic link: {relative}")
        if index < len(relative_parts) - 1:
            if not stat.S_ISDIR(file_stat.st_mode):
                raise ContractError(f"artifact parent is not a directory: {relative}")
        elif not stat.S_ISREG(file_stat.st_mode):
            raise ContractError(f"artifact is not a regular file: {relative}")
    size = file_stat.st_size
    if size <= 0 or size > MAX_ARTIFACT_SIZE:
        raise ContractError(f"artifact size is invalid: {relative}")
    return candidate


def load_artifacts(dist: Path) -> list[dict]:
    metadata_path = dist / "artifacts.json"
    try:
        if metadata_path.is_symlink() or not metadata_path.is_file():
            raise ContractError("artifacts.json is missing or unsafe")
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot read artifacts.json: {exc}") from exc
    if not isinstance(payload, list) or not payload or len(payload) > MAX_ARTIFACTS:
        raise ContractError("artifacts.json must be a bounded non-empty array")
    if not all(isinstance(item, dict) for item in payload):
        raise ContractError("artifacts.json contains a non-object entry")
    return payload


def inspect_zip(path: Path) -> set[str]:
    names: list[str] = []
    total_size = 0
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ARCHIVE_MEMBERS:
                raise ContractError("ZIP has too many members")
            for info in infos:
                member = safe_member_name(info.filename.rstrip("/"), "ZIP member")
                names.append(member.as_posix())
                if info.flag_bits & 0x1:
                    raise ContractError("encrypted ZIP member")
                total_size += info.file_size
                if total_size > MAX_ARCHIVE_UNCOMPRESSED:
                    raise ContractError("ZIP exceeds uncompressed-size limit")
                mode = info.external_attr >> 16
                file_type = stat.S_IFMT(mode)
                if file_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
                    raise ContractError("ZIP contains a special member")
    except (OSError, zipfile.BadZipFile) as exc:
        raise ContractError(f"invalid ZIP {path.name}: {exc}") from exc
    if len(names) != len(set(names)):
        raise ContractError("ZIP contains duplicate members")
    return set(names)


def inspect_tar(path: Path) -> set[str]:
    names: list[str] = []
    total_size = 0
    try:
        with tarfile.open(path, "r:*") as archive:
            members = archive.getmembers()
            if len(members) > MAX_ARCHIVE_MEMBERS:
                raise ContractError("tar archive has too many members")
            for info in members:
                member = safe_member_name(info.name.rstrip("/"), "tar member")
                names.append(member.as_posix())
                if not (info.isfile() or info.isdir()):
                    raise ContractError("tar archive contains a link or special member")
                total_size += info.size
                if total_size > MAX_ARCHIVE_UNCOMPRESSED:
                    raise ContractError("tar archive exceeds uncompressed-size limit")
    except (OSError, tarfile.TarError) as exc:
        raise ContractError(f"invalid tar archive {path.name}: {exc}") from exc
    if len(names) != len(set(names)):
        raise ContractError("tar archive contains duplicate members")
    return set(names)


def validate_archive(path: Path, goos: str) -> None:
    if goos == "windows":
        if path.suffix.lower() != ".zip":
            raise ContractError(f"Windows archive must be ZIP: {path.name}")
        names = inspect_zip(path)
        binary = "llm-usage-exporter.exe"
    else:
        if not path.name.endswith(".tar.gz"):
            raise ContractError(f"Unix archive must be tar.gz: {path.name}")
        names = inspect_tar(path)
        binary = "llm-usage-exporter"
    if not REQUIRED_ARCHIVE_FILES.issubset(names) or binary not in names:
        missing = sorted((REQUIRED_ARCHIVE_FILES | {binary}) - names)
        raise ContractError(f"archive {path.name} misses required members: {missing}")


def platform_pair(artifact: dict) -> tuple[str, str]:
    goos = artifact.get("goos")
    goarch = artifact.get("goarch")
    if not isinstance(goos, str) or not isinstance(goarch, str):
        raise ContractError("archive has no platform identity")
    return goos, goarch


def validate_sbom(path: Path) -> None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"invalid SBOM {path.name}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ContractError(f"SBOM {path.name} is not a JSON object")
    if "spdxVersion" not in payload and payload.get("bomFormat") != "CycloneDX":
        raise ContractError(f"SBOM {path.name} has no recognized schema marker")
    components = payload.get("packages", payload.get("components"))
    if not isinstance(components, list) or not components:
        raise ContractError(f"SBOM {path.name} has no package or component inventory")


def parse_checksums(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise ContractError(f"cannot read checksums: {exc}") from exc
    checksums: dict[str, str] = {}
    for line in lines:
        match = CHECKSUM_PATTERN.fullmatch(line.strip())
        if not match:
            raise ContractError("malformed checksums.txt line")
        name = safe_member_name(match.group(2), "checksum filename").as_posix()
        if name in checksums:
            raise ContractError("duplicate checksums.txt entry")
        checksums[name] = match.group(1)
    if not checksums:
        raise ContractError("checksums.txt is empty")
    return checksums


def verify(dist: Path) -> tuple[int, int]:
    artifacts = load_artifacts(dist)
    archive_entries = [item for item in artifacts if item.get("type") == "Archive"]
    sbom_entries = [item for item in artifacts if item.get("type") == "SBOM"]
    checksum_entries = [item for item in artifacts if item.get("type") == "Checksum"]
    if len(archive_entries) != len(EXPECTED_PLATFORMS):
        raise ContractError("release must contain exactly six archives")
    if len(sbom_entries) != len(archive_entries):
        raise ContractError("release must contain exactly one SBOM per archive")
    if len(checksum_entries) != 1:
        raise ContractError("release must contain exactly one checksum artifact")

    archives: dict[tuple[str, str], tuple[dict, Path]] = {}
    for entry in archive_entries:
        pair = platform_pair(entry)
        if pair in archives:
            raise ContractError(f"duplicate archive platform: {pair}")
        path = resolve_artifact(dist, entry.get("path"))
        if entry.get("name") != path.name:
            raise ContractError(f"archive metadata name mismatch: {path.name}")
        validate_archive(path, pair[0])
        archives[pair] = (entry, path)
    if set(archives) != EXPECTED_PLATFORMS:
        raise ContractError(f"release platform matrix drift: {sorted(archives)}")

    sboms: list[tuple[dict, Path]] = []
    for entry in sbom_entries:
        path = resolve_artifact(dist, entry.get("path"))
        if entry.get("name") != path.name:
            raise ContractError(f"SBOM metadata name mismatch: {path.name}")
        validate_sbom(path)
        sboms.append((entry, path))
    for pair, (_, archive_path) in archives.items():
        matches = [
            path
            for entry, path in sboms
            if (entry.get("goos"), entry.get("goarch")) == pair
            or path.name.startswith(archive_path.name + ".")
        ]
        if len(matches) != 1:
            raise ContractError(f"archive has no unique SBOM: {archive_path.name}")

    checksum_path = resolve_artifact(dist, checksum_entries[0].get("path"))
    checksums = parse_checksums(checksum_path)
    for _, archive_path in archives.values():
        expected = checksums.get(archive_path.name)
        if expected is None or expected != sha256_file(archive_path):
            raise ContractError(f"archive checksum mismatch: {archive_path.name}")
    return len(archives), len(sboms)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", default="dist")
    return parser


def main() -> int:
    try:
        archives, sboms = verify(canonical_dist(build_parser().parse_args().dist))
    except ContractError as exc:
        print(f"[release-contract] {exc}", file=os.sys.stderr)
        return 1
    print(f"[release-contract] archives={archives} sboms={sboms} matrix=linux,darwin,windows/amd64,arm64")
    print("[release-contract] artifact, archive, checksum, and SBOM contracts pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
