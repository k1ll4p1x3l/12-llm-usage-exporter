package jsonfile

import (
	"encoding/json"
	"fmt"
	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/model"
	"os"
	"path/filepath"
)

func WriteSnapshot(path string, snapshot model.Snapshot, pretty bool) error {
	if path == "" {
		return nil
	}
	data, err := marshal(snapshot, pretty)
	if err != nil {
		return err
	}

	dir := filepath.Dir(path)
	if dir != "." && dir != "" {
		if err := os.MkdirAll(dir, 0o755); err != nil {
			return fmt.Errorf("create output dir: %w", err)
		}
	}

	tmp, err := os.CreateTemp(dir, ".llm-usage-exporter-*.tmp")
	if err != nil {
		return fmt.Errorf("create temp file: %w", err)
	}
	tmpPath := tmp.Name()

	if _, err := tmp.Write(data); err != nil {
		closeErr := tmp.Close()
		_ = os.Remove(tmpPath)
		return fmt.Errorf("write snapshot: %w (close: %v)", err, closeErr)
	}
	if err := tmp.Sync(); err != nil {
		closeErr := tmp.Close()
		_ = os.Remove(tmpPath)
		return fmt.Errorf("flush snapshot: %w (close: %v)", err, closeErr)
	}
	if err := tmp.Close(); err != nil {
		_ = os.Remove(tmpPath)
		return fmt.Errorf("close snapshot: %w", err)
	}

	if err := os.Rename(tmpPath, path); err != nil {
		_ = os.Remove(tmpPath)
		return fmt.Errorf("rename snapshot: %w", err)
	}
	return nil
}

func marshal(snapshot model.Snapshot, pretty bool) ([]byte, error) {
	if pretty {
		return json.MarshalIndent(snapshot, "", "  ")
	}
	return json.Marshal(snapshot)
}
