# Deployment

## Portable beta install

Download the archive for your OS and architecture from the GitHub release,
verify it against `checksums.txt`, then place the binary on your `PATH`.

Supported beta archive targets:

- `linux_amd64`
- `linux_arm64`
- `darwin_amd64`
- `darwin_arm64`
- `windows_amd64`
- `windows_arm64`

Create and check the default config:

```bash
llm-usage-exporter init
llm-usage-exporter doctor
```

Run a one-off snapshot:

```bash
llm-usage-exporter snapshot
```

Run continuously:

```bash
llm-usage-exporter serve
```

Default config and snapshot paths:

- Linux: `~/.config/llm-usage-exporter/config.yaml` and `~/.local/state/llm-usage-exporter/usage.snapshot.json`
- macOS: `~/Library/Application Support/llm-usage-exporter/config.yaml` and `~/Library/Application Support/llm-usage-exporter/usage.snapshot.json`
- Windows: `%AppData%\llm-usage-exporter\config.yaml` and `%LocalAppData%\llm-usage-exporter\usage.snapshot.json`

## Linux service (user unit)

```ini
# copy the built binary to /usr/local/bin/llm-usage-exporter
# copy examples/llm-usage-exporter.yaml to ~/.config/llm-usage-exporter/config.yaml
# copy examples/llm-usage-exporter.service to ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now llm-usage-exporter
```

## One-off snapshot

```bash
llm-usage-exporter snapshot --config examples/llm-usage-exporter.yaml
```

## Release artifacts

- GitHub Actions builds Linux, macOS, and Windows `amd64` and `arm64` archives for tags `v*`.
- Artifact checksums are produced as `checksums.txt`.
- SBOM generation is enabled in `.goreleaser.yaml`.
- See `docs/release.md` for milestone-first release sequencing and
  maintainer commands.
