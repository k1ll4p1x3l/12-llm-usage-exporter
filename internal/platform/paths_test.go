package platform

import "testing"

func TestDefaultPathsLinuxXDG(t *testing.T) {
	t.Parallel()

	paths, err := defaultPaths("linux", func(key string) string {
		switch key {
		case "XDG_CONFIG_HOME":
			return "/cfg"
		case "XDG_STATE_HOME":
			return "/state"
		default:
			return ""
		}
	}, "/home/test")
	if err != nil {
		t.Fatalf("defaultPaths returned error: %v", err)
	}
	if paths.ConfigPath != "/cfg/llm-usage-exporter/config.yaml" {
		t.Fatalf("unexpected config path: %q", paths.ConfigPath)
	}
	if paths.StatePath != "/state/llm-usage-exporter/usage.snapshot.json" {
		t.Fatalf("unexpected state path: %q", paths.StatePath)
	}
}

func TestDefaultPathsLinuxFallback(t *testing.T) {
	t.Parallel()

	paths, err := defaultPaths("linux", func(string) string { return "" }, "/home/test")
	if err != nil {
		t.Fatalf("defaultPaths returned error: %v", err)
	}
	if paths.ConfigPath != "/home/test/.config/llm-usage-exporter/config.yaml" {
		t.Fatalf("unexpected config path: %q", paths.ConfigPath)
	}
	if paths.StatePath != "/home/test/.local/state/llm-usage-exporter/usage.snapshot.json" {
		t.Fatalf("unexpected state path: %q", paths.StatePath)
	}
}

func TestDefaultPathsDarwin(t *testing.T) {
	t.Parallel()

	paths, err := defaultPaths("darwin", func(string) string { return "" }, "/Users/test")
	if err != nil {
		t.Fatalf("defaultPaths returned error: %v", err)
	}
	if paths.ConfigPath != "/Users/test/Library/Application Support/llm-usage-exporter/config.yaml" {
		t.Fatalf("unexpected config path: %q", paths.ConfigPath)
	}
	if paths.StatePath != "/Users/test/Library/Application Support/llm-usage-exporter/usage.snapshot.json" {
		t.Fatalf("unexpected state path: %q", paths.StatePath)
	}
}

func TestDefaultPathsWindows(t *testing.T) {
	t.Parallel()

	paths, err := defaultPaths("windows", func(key string) string {
		switch key {
		case "APPDATA":
			return `C:\Users\test\AppData\Roaming`
		case "LOCALAPPDATA":
			return `C:\Users\test\AppData\Local`
		default:
			return ""
		}
	}, `C:\Users\test`)
	if err != nil {
		t.Fatalf("defaultPaths returned error: %v", err)
	}
	if paths.ConfigPath != `C:\Users\test\AppData\Roaming\llm-usage-exporter\config.yaml` {
		t.Fatalf("unexpected config path: %q", paths.ConfigPath)
	}
	if paths.StatePath != `C:\Users\test\AppData\Local\llm-usage-exporter\usage.snapshot.json` {
		t.Fatalf("unexpected state path: %q", paths.StatePath)
	}
}
