package platform

import (
	"fmt"
	"os"
	"runtime"
	"strings"
)

const appDir = "llm-usage-exporter"

type Paths struct {
	ConfigPath string
	StatePath  string
}

func DefaultPaths() (Paths, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return Paths{}, fmt.Errorf("resolve home directory: %w", err)
	}
	return defaultPaths(runtime.GOOS, os.Getenv, home)
}

func defaultPaths(goos string, getenv func(string) string, home string) (Paths, error) {
	if strings.TrimSpace(home) == "" {
		return Paths{}, fmt.Errorf("home directory is empty")
	}

	switch goos {
	case "darwin":
		base := joinPath(goos, home, "Library", "Application Support", appDir)
		return Paths{
			ConfigPath: joinPath(goos, base, "config.yaml"),
			StatePath:  joinPath(goos, base, "usage.snapshot.json"),
		}, nil
	case "windows":
		configBase := getenv("APPDATA")
		if strings.TrimSpace(configBase) == "" {
			configBase = joinPath(goos, home, "AppData", "Roaming")
		}
		stateBase := getenv("LOCALAPPDATA")
		if strings.TrimSpace(stateBase) == "" {
			stateBase = joinPath(goos, home, "AppData", "Local")
		}
		return Paths{
			ConfigPath: joinPath(goos, configBase, appDir, "config.yaml"),
			StatePath:  joinPath(goos, stateBase, appDir, "usage.snapshot.json"),
		}, nil
	default:
		configBase := getenv("XDG_CONFIG_HOME")
		if strings.TrimSpace(configBase) == "" {
			configBase = joinPath(goos, home, ".config")
		}
		stateBase := getenv("XDG_STATE_HOME")
		if strings.TrimSpace(stateBase) == "" {
			stateBase = joinPath(goos, home, ".local", "state")
		}
		return Paths{
			ConfigPath: joinPath(goos, configBase, appDir, "config.yaml"),
			StatePath:  joinPath(goos, stateBase, appDir, "usage.snapshot.json"),
		}, nil
	}
}

func joinPath(goos string, elems ...string) string {
	sep := "/"
	if goos == "windows" {
		sep = `\`
	}

	parts := make([]string, 0, len(elems))
	for i, elem := range elems {
		elem = strings.TrimSpace(elem)
		if elem == "" {
			continue
		}
		if i == 0 {
			parts = append(parts, strings.TrimRight(elem, `/\`))
		} else {
			parts = append(parts, strings.Trim(elem, `/\`))
		}
	}
	return strings.Join(parts, sep)
}
