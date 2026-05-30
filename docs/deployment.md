# Deployment

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

- GitHub Actions builds Linux `amd64` and `arm64` archives for tags `v*`.
- Artifact checksums are produced as `checksums.txt`.
- SBOM generation is enabled in `.goreleaser.yaml`.
- See `docs/release.md` for milestone-first release sequencing and
  maintainer commands.
