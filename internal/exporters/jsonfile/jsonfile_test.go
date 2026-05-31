package jsonfile

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/model"
)

func TestWriteSnapshotCreatesPrettyJSON(t *testing.T) {
	t.Parallel()

	path := filepath.Join(t.TempDir(), "nested", "usage.snapshot.json")
	snapshot := model.Snapshot{
		SchemaVersion: model.SchemaVersion,
		Agent:         "test",
		GeneratedAt:   time.Date(2026, 5, 31, 12, 0, 0, 0, time.UTC),
		Source:        "test",
	}

	if err := WriteSnapshot(path, snapshot, true); err != nil {
		t.Fatalf("WriteSnapshot returned error: %v", err)
	}

	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read snapshot: %v", err)
	}
	if !strings.Contains(string(raw), "\n  ") {
		t.Fatalf("expected pretty JSON, got %q", raw)
	}
	var decoded model.Snapshot
	if err := json.Unmarshal(raw, &decoded); err != nil {
		t.Fatalf("snapshot is not JSON: %v", err)
	}
	if decoded.SchemaVersion != model.SchemaVersion {
		t.Fatalf("unexpected schema version: %q", decoded.SchemaVersion)
	}
}

func TestWriteSnapshotEmptyPathIsNoop(t *testing.T) {
	t.Parallel()

	if err := WriteSnapshot("", model.Snapshot{}, false); err != nil {
		t.Fatalf("expected empty path noop, got %v", err)
	}
}
