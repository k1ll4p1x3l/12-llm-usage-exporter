package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/collectors/codex"
	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/config"
	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/platform"
	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/service"
)

var version = "0.0.0-dev"

func main() {
	if len(os.Args) < 2 {
		printUsage()
		os.Exit(2)
	}

	switch os.Args[1] {
	case "init":
		if err := runInit(os.Args[2:]); err != nil {
			log.Fatal(err)
		}
	case "doctor":
		if err := runDoctor(os.Args[2:]); err != nil {
			log.Fatal(err)
		}
	case "serve":
		if err := runServe(os.Args[2:]); err != nil {
			log.Fatal(err)
		}
	case "snapshot":
		if err := runSnapshot(os.Args[2:]); err != nil {
			log.Fatal(err)
		}
	case "validate-config":
		if err := runValidateConfig(os.Args[2:]); err != nil {
			log.Fatal(err)
		}
	case "version":
		fmt.Println(version)
	default:
		fmt.Printf("unknown command %q\n", os.Args[1])
		printUsage()
		os.Exit(2)
	}
}

func printUsage() {
	fmt.Println("usage: llm-usage-exporter <init|doctor|serve|snapshot|validate-config|version> [flags]")
}

func runInit(args []string) error {
	fs := flag.NewFlagSet("init", flag.ContinueOnError)
	configPath := fs.String("config", "", "path to write YAML config")
	force := fs.Bool("force", false, "overwrite an existing config")
	if err := fs.Parse(args); err != nil {
		return err
	}

	path, err := defaultConfigPath(*configPath)
	if err != nil {
		return err
	}
	if _, err := os.Stat(path); err == nil && !*force {
		return fmt.Errorf("config already exists: %s (use --force to overwrite)", path)
	} else if err != nil && !os.IsNotExist(err) {
		return fmt.Errorf("inspect config path: %w", err)
	}

	cfg := config.StarterConfig()
	if dir := filepath.Dir(path); dir != "." && dir != "" {
		if err := os.MkdirAll(dir, 0o755); err != nil {
			return fmt.Errorf("create config dir: %w", err)
		}
	}
	if err := os.WriteFile(path, config.StarterYAML(cfg), 0o600); err != nil {
		return fmt.Errorf("write config: %w", err)
	}
	fmt.Printf("wrote config: %s\n", path)
	return nil
}

func runDoctor(args []string) error {
	fs := flag.NewFlagSet("doctor", flag.ContinueOnError)
	configPath := fs.String("config", "", "path to JSON/YAML/TOML config")
	jsonOutput := fs.Bool("json", false, "print machine-readable JSON")
	if err := fs.Parse(args); err != nil {
		return err
	}

	report := buildDoctorReport(*configPath)
	if *jsonOutput {
		out, err := json.MarshalIndent(report, "", "  ")
		if err != nil {
			return err
		}
		fmt.Println(string(out))
	} else {
		fmt.Printf("doctor status: %s\n", report.Status)
		if report.ConfigPath != "" {
			fmt.Printf("config: %s\n", report.ConfigPath)
		}
		for _, check := range report.Checks {
			fmt.Printf("[%s] %s: %s\n", check.Status, check.Name, check.Message)
		}
	}
	if report.Status == "error" {
		return fmt.Errorf("doctor found errors")
	}
	return nil
}

func runServe(args []string) error {
	fs := flag.NewFlagSet("serve", flag.ContinueOnError)
	configPath := fs.String("config", "", "path to JSON/YAML/TOML config")
	once := fs.Bool("once", false, "run one cycle and exit")
	if err := fs.Parse(args); err != nil {
		return err
	}

	cfg, err := config.Load(existingConfigOrDefault(*configPath))
	if err != nil {
		return err
	}

	collectors, err := service.BuildCollectors(cfg)
	if err != nil {
		return err
	}

	runner := service.NewRunner(cfg, collectors)
	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()

	if cfg.Prometheus.Enabled {
		go func() {
			log.Printf("starting metrics endpoint on %s/metrics", cfg.Prometheus.ListenAddress)
			mux := http.NewServeMux()
			mux.Handle("/metrics", runner.PrometheusHandler().Handler())
			if err := http.ListenAndServe(cfg.Prometheus.ListenAddress, mux); err != nil {
				log.Printf("metrics server stopped: %v", err)
			}
		}()
	}

	if *once {
		_, err := runner.RunOnce(ctx)
		return err
	}
	return runner.Run(ctx)
}

func runSnapshot(args []string) error {
	fs := flag.NewFlagSet("snapshot", flag.ContinueOnError)
	configPath := fs.String("config", "", "path to JSON/YAML/TOML config")
	if err := fs.Parse(args); err != nil {
		return err
	}

	cfg, err := config.Load(existingConfigOrDefault(*configPath))
	if err != nil {
		return err
	}

	collectors, err := service.BuildCollectors(cfg)
	if err != nil {
		return err
	}

	runner := service.NewRunner(cfg, collectors)
	ctx := context.Background()
	snapshot, collectErr := runner.RunOnce(ctx)
	if collectErr != nil {
		log.Printf("snapshot warning: %v", collectErr)
	}
	out, err := json.MarshalIndent(snapshot, "", "  ")
	if err != nil {
		return err
	}
	fmt.Println(string(out))
	return collectErr
}

func runValidateConfig(args []string) error {
	fs := flag.NewFlagSet("validate-config", flag.ContinueOnError)
	configPath := fs.String("config", "", "path to JSON/YAML/TOML config")
	if err := fs.Parse(args); err != nil {
		return err
	}

	cfg, err := config.Load(existingConfigOrDefault(*configPath))
	if err != nil {
		return err
	}
	out, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return err
	}
	fmt.Println(string(out))
	return nil
}

type doctorReport struct {
	Status     string        `json:"status"`
	ConfigPath string        `json:"config_path,omitempty"`
	Checks     []doctorCheck `json:"checks"`
}

type doctorCheck struct {
	Name    string `json:"name"`
	Status  string `json:"status"`
	Message string `json:"message"`
}

func buildDoctorReport(requestedConfigPath string) doctorReport {
	report := doctorReport{Status: "ok"}
	configPath := existingConfigOrDefault(requestedConfigPath)
	if configPath == "" {
		if defaultPath, err := defaultConfigPath(""); err == nil {
			report.ConfigPath = defaultPath
			report.Checks = append(report.Checks, doctorCheck{
				Name:    "config",
				Status:  "warn",
				Message: "no config file found; using built-in defaults",
			})
		}
	} else {
		report.ConfigPath = configPath
	}

	cfg, err := config.Load(configPath)
	if err != nil {
		report.Checks = append(report.Checks, doctorCheck{Name: "config", Status: "error", Message: err.Error()})
		report.Status = "error"
		return report
	}
	if configPath != "" {
		report.Checks = append(report.Checks, doctorCheck{Name: "config", Status: "ok", Message: "configuration is valid"})
	}

	commandOK := true
	for _, provider := range cfg.Providers {
		if !provider.Enabled || provider.Type != "codex" {
			continue
		}
		resolved, err := codex.ResolveCommand(provider.Command)
		if err != nil {
			commandOK = false
			report.Checks = append(report.Checks, doctorCheck{Name: "codex command", Status: "error", Message: err.Error()})
			continue
		}
		report.Checks = append(report.Checks, doctorCheck{Name: "codex command", Status: "ok", Message: resolved})
	}

	report.Checks = append(report.Checks, checkJSONOutput(cfg))
	report.Checks = append(report.Checks, checkMetrics(cfg))

	if commandOK {
		collectCfg := cfg
		collectCfg.JSONOutput.Enabled = false
		collectCfg.Prometheus.Enabled = false
		collectors, err := service.BuildCollectors(collectCfg)
		if err != nil {
			report.Checks = append(report.Checks, doctorCheck{Name: "codex collection", Status: "error", Message: err.Error()})
		} else {
			runner := service.NewRunner(collectCfg, collectors)
			ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
			defer cancel()
			snapshot, err := runner.RunOnce(ctx)
			if err != nil {
				report.Checks = append(report.Checks, doctorCheck{Name: "codex collection", Status: "error", Message: err.Error()})
			} else {
				report.Checks = append(report.Checks, doctorCheck{Name: "codex collection", Status: "ok", Message: fmt.Sprintf("%d provider(s), health=%s", len(snapshot.Providers), snapshot.Health.Status)})
			}
		}
	}

	report.Status = aggregateDoctorStatus(report.Checks)
	return report
}

func checkJSONOutput(cfg config.Config) doctorCheck {
	if !cfg.JSONOutput.Enabled {
		return doctorCheck{Name: "json output", Status: "ok", Message: "disabled"}
	}
	if cfg.JSONOutput.Path == "" {
		return doctorCheck{Name: "json output", Status: "error", Message: "enabled but path is empty"}
	}
	dir := filepath.Dir(cfg.JSONOutput.Path)
	if dir == "." || dir == "" {
		return doctorCheck{Name: "json output", Status: "ok", Message: "writes to current directory"}
	}
	if info, err := os.Stat(dir); err != nil {
		if os.IsNotExist(err) {
			return doctorCheck{Name: "json output", Status: "warn", Message: fmt.Sprintf("directory will be created on first write: %s", dir)}
		}
		return doctorCheck{Name: "json output", Status: "error", Message: err.Error()}
	} else if !info.IsDir() {
		return doctorCheck{Name: "json output", Status: "error", Message: fmt.Sprintf("parent path is not a directory: %s", dir)}
	}
	return doctorCheck{Name: "json output", Status: "ok", Message: cfg.JSONOutput.Path}
}

func checkMetrics(cfg config.Config) doctorCheck {
	if !cfg.Prometheus.Enabled {
		return doctorCheck{Name: "prometheus", Status: "ok", Message: "disabled"}
	}
	listener, err := net.Listen("tcp", cfg.Prometheus.ListenAddress)
	if err != nil {
		return doctorCheck{Name: "prometheus", Status: "error", Message: err.Error()}
	}
	_ = listener.Close()
	return doctorCheck{Name: "prometheus", Status: "ok", Message: cfg.Prometheus.ListenAddress}
}

func aggregateDoctorStatus(checks []doctorCheck) string {
	status := "ok"
	for _, check := range checks {
		switch check.Status {
		case "error":
			return "error"
		case "warn":
			status = "warn"
		}
	}
	return status
}

func existingConfigOrDefault(path string) string {
	if path != "" {
		return path
	}
	defaultPath, err := defaultConfigPath("")
	if err != nil {
		return ""
	}
	if _, err := os.Stat(defaultPath); err == nil {
		return defaultPath
	}
	return ""
}

func defaultConfigPath(path string) (string, error) {
	if path != "" {
		return path, nil
	}
	paths, err := platform.DefaultPaths()
	if err != nil {
		return "", err
	}
	return paths.ConfigPath, nil
}
