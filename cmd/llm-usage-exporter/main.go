package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"

	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/config"
	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/service"
)

var version = "0.0.0-dev"

func main() {
	if len(os.Args) < 2 {
		fmt.Println("usage: llm-usage-exporter <serve|snapshot|validate-config|version> [flags]")
		os.Exit(2)
	}

	switch os.Args[1] {
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
		fmt.Println("usage: llm-usage-exporter <serve|snapshot|validate-config|version> [flags]")
		os.Exit(2)
	}
}

func runServe(args []string) error {
	fs := flag.NewFlagSet("serve", flag.ContinueOnError)
	configPath := fs.String("config", "", "path to JSON/YAML/TOML config")
	once := fs.Bool("once", false, "run one cycle and exit")
	if err := fs.Parse(args); err != nil {
		return err
	}

	cfg, err := config.Load(*configPath)
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

	cfg, err := config.Load(*configPath)
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

	cfg, err := config.Load(*configPath)
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
