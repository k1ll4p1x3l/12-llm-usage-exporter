package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
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

var version = "0.5.0-beta.1-dev"

func main() {
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr))
}

func run(args []string, stdout, stderr io.Writer) int {
	if len(args) < 1 {
		printUsage(stderr)
		return 2
	}
	if isHelpArg(args[0]) {
		if args[0] == "help" && len(args) > 1 {
			if !printCommandUsage(args[1], stdout) {
				fmt.Fprintf(stderr, "unknown command %q\n", args[1])
				printUsage(stderr)
				return 2
			}
			return 0
		}
		printUsage(stdout)
		return 0
	}

	var err error
	switch args[0] {
	case "init":
		err = runInitWithOutput(args[1:], stdout)
	case "doctor":
		err = runDoctorWithOutput(args[1:], stdout)
	case "serve":
		err = runServeWithOutput(args[1:], stdout)
	case "snapshot":
		err = runSnapshotWithOutput(args[1:], stdout)
	case "validate-config":
		err = runValidateConfigWithOutput(args[1:], stdout)
	case "version":
		fmt.Fprintln(stdout, version)
	default:
		fmt.Fprintf(stderr, "unknown command %q\n", args[0])
		printUsage(stderr)
		return 2
	}

	if err != nil {
		if errors.Is(err, flag.ErrHelp) {
			return 0
		}
		fmt.Fprintln(stderr, err)
		return 1
	}
	return 0
}

func isHelpArg(arg string) bool {
	return arg == "-h" || arg == "--help" || arg == "help"
}

func printUsage(out io.Writer) {
	fmt.Fprintln(out, `usage: llm-usage-exporter <command> [flags]

Commands:
  init             Write a starter YAML config
  doctor           Diagnose config, Codex, outputs, and collection
  serve            Run the scheduled exporter and metrics endpoint
  snapshot         Collect once and print a JSON snapshot
  validate-config  Load and print the normalized config
  version          Print the binary version

Run "llm-usage-exporter help <command>" for command-specific flags.`)
}

func printCommandUsage(command string, out io.Writer) bool {
	fs := commandFlagSet(command, out)
	if fs == nil {
		return false
	}
	fs.Usage()
	return true
}

func commandFlagSet(name string, out io.Writer) *flag.FlagSet {
	switch name {
	case "init":
		return initFlagSet(out)
	case "doctor":
		return doctorFlagSet(out)
	case "serve":
		return serveFlagSet(out)
	case "snapshot":
		return snapshotFlagSet(out)
	case "validate-config":
		return validateConfigFlagSet(out)
	default:
		return nil
	}
}

func newCommandFlagSet(name, summary string, out io.Writer) *flag.FlagSet {
	fs := flag.NewFlagSet(name, flag.ContinueOnError)
	fs.SetOutput(out)
	fs.Usage = func() {
		fmt.Fprintf(fs.Output(), "usage: llm-usage-exporter %s [flags]\n\n%s\n\nFlags:\n", name, summary)
		fs.PrintDefaults()
	}
	return fs
}

func initFlagSet(out io.Writer) *flag.FlagSet {
	fs := newCommandFlagSet("init", "Write an OS-appropriate starter YAML config.", out)
	fs.String("config", "", "path to write YAML config")
	fs.Bool("force", false, "overwrite an existing config")
	return fs
}

func doctorFlagSet(out io.Writer) *flag.FlagSet {
	fs := newCommandFlagSet("doctor", "Check config, Codex command discovery, outputs, metrics, and collection.", out)
	fs.String("config", "", "path to JSON/YAML/TOML config")
	fs.Bool("json", false, "print machine-readable JSON")
	return fs
}

func serveFlagSet(out io.Writer) *flag.FlagSet {
	fs := newCommandFlagSet("serve", "Run the exporter loop, or a single cycle with --once.", out)
	fs.String("config", "", "path to JSON/YAML/TOML config")
	fs.Bool("once", false, "run one cycle and exit")
	return fs
}

func snapshotFlagSet(out io.Writer) *flag.FlagSet {
	fs := newCommandFlagSet("snapshot", "Collect once and print the JSON snapshot.", out)
	fs.String("config", "", "path to JSON/YAML/TOML config")
	return fs
}

func validateConfigFlagSet(out io.Writer) *flag.FlagSet {
	fs := newCommandFlagSet("validate-config", "Load, validate, and print the normalized config.", out)
	fs.String("config", "", "path to JSON/YAML/TOML config")
	return fs
}

func runInit(args []string) error {
	return runInitWithOutput(args, os.Stdout)
}

func runInitWithOutput(args []string, out io.Writer) error {
	fs := initFlagSet(out)
	if err := fs.Parse(args); err != nil {
		return err
	}
	configPath := fs.Lookup("config").Value.String()
	force := fs.Lookup("force").Value.String() == "true"

	path, err := defaultConfigPath(configPath)
	if err != nil {
		return err
	}
	if _, err := os.Stat(path); err == nil && !force {
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
	fmt.Fprintf(out, "wrote config: %s\n", path)
	return nil
}

func runDoctor(args []string) error {
	return runDoctorWithOutput(args, os.Stdout)
}

func runDoctorWithOutput(args []string, out io.Writer) error {
	fs := doctorFlagSet(out)
	if err := fs.Parse(args); err != nil {
		return err
	}
	configPath := fs.Lookup("config").Value.String()
	jsonOutput := fs.Lookup("json").Value.String() == "true"

	report := buildDoctorReport(configPath)
	if jsonOutput {
		payload, err := json.MarshalIndent(report, "", "  ")
		if err != nil {
			return err
		}
		fmt.Fprintln(out, string(payload))
	} else {
		fmt.Fprintf(out, "doctor status: %s\n", report.Status)
		if report.ConfigPath != "" {
			fmt.Fprintf(out, "config: %s\n", report.ConfigPath)
		}
		for _, check := range report.Checks {
			fmt.Fprintf(out, "[%s] %s: %s\n", check.Status, check.Name, check.Message)
		}
	}
	if report.Status == "error" {
		return fmt.Errorf("doctor found errors")
	}
	return nil
}

func runServe(args []string) error {
	return runServeWithOutput(args, os.Stdout)
}

func runServeWithOutput(args []string, out io.Writer) error {
	fs := serveFlagSet(out)
	if err := fs.Parse(args); err != nil {
		return err
	}
	configPath := fs.Lookup("config").Value.String()
	once := fs.Lookup("once").Value.String() == "true"

	cfg, err := config.Load(existingConfigOrDefault(configPath))
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

	if once {
		_, err := runner.RunOnce(ctx)
		return err
	}
	return runner.Run(ctx)
}

func runSnapshot(args []string) error {
	return runSnapshotWithOutput(args, os.Stdout)
}

func runSnapshotWithOutput(args []string, out io.Writer) error {
	fs := snapshotFlagSet(out)
	if err := fs.Parse(args); err != nil {
		return err
	}
	configPath := fs.Lookup("config").Value.String()

	cfg, err := config.Load(existingConfigOrDefault(configPath))
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
	payload, err := json.MarshalIndent(snapshot, "", "  ")
	if err != nil {
		return err
	}
	fmt.Fprintln(out, string(payload))
	return collectErr
}

func runValidateConfig(args []string) error {
	return runValidateConfigWithOutput(args, os.Stdout)
}

func runValidateConfigWithOutput(args []string, out io.Writer) error {
	fs := validateConfigFlagSet(out)
	if err := fs.Parse(args); err != nil {
		return err
	}
	configPath := fs.Lookup("config").Value.String()

	cfg, err := config.Load(existingConfigOrDefault(configPath))
	if err != nil {
		return err
	}
	payload, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return err
	}
	fmt.Fprintln(out, string(payload))
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
