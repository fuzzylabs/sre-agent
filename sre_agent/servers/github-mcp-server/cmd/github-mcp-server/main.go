package main

import (
	"context"
	"fmt"
	"io"
	stdlog "log"
	"os"
	"os/signal"
	"syscall"
	"net/http"

	"github.com/github/github-mcp-server/pkg/github"
	iolog "github.com/github/github-mcp-server/pkg/log"
	"github.com/github/github-mcp-server/pkg/translations"
	gogithub "github.com/google/go-github/v69/github"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
	log "github.com/sirupsen/logrus"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var version = "version"
var commit = "commit"
var date = "date"

var (
	rootCmd = &cobra.Command{
		Use:     "server",
		Short:   "GitHub MCP Server",
		Long:    `A GitHub MCP server that handles various tools and resources.`,
		Version: fmt.Sprintf("Version: %s\nCommit: %s\nBuild Date: %s", version, commit, date),
	}

	stdioCmd = &cobra.Command{
		Use:   "stdio",
		Short: "Start stdio server",
		Long:  `Start a server that communicates via standard input/output streams using JSON-RPC messages.`,
		Run: func(_ *cobra.Command, _ []string) {
			logFile := viper.GetString("log-file")
			readOnly := viper.GetBool("read-only")
			exportTranslations := viper.GetBool("export-translations")
			logger, err := initLogger(logFile)
			if err != nil {
				stdlog.Fatal("Failed to initialize logger:", err)
			}

			// If you're wondering why we're not using viper.GetStringSlice("toolsets"),
			// it's because viper doesn't handle comma-separated values correctly for env
			// vars when using GetStringSlice.
			// https://github.com/spf13/viper/issues/380
			var enabledToolsets []string
			err = viper.UnmarshalKey("toolsets", &enabledToolsets)
			if err != nil {
				stdlog.Fatal("Failed to unmarshal toolsets:", err)
			}

			logCommands := viper.GetBool("enable-command-logging")
			cfg := runConfig{
				readOnly:           readOnly,
				logger:             logger,
				logCommands:        logCommands,
				exportTranslations: exportTranslations,
				enabledToolsets:    enabledToolsets,
			}
			if err := runStdioServer(cfg); err != nil {
				stdlog.Fatal("failed to run stdio server:", err)
			}
		},
	}

	sseCmd = &cobra.Command{
		Use:   "sse",
		Short: "Start SSE server",
		Long:  `Start a server that communicates via Server-Sent Event (SSE) streams using JSON-RPC messages.`,
		Run: func(_ *cobra.Command, _ []string) {
			logFile := viper.GetString("log-file")
			readOnly := viper.GetBool("read-only")
			exportTranslations := viper.GetBool("export-translations")
			logger, err := initLogger(logFile)
			if err != nil {
				stdlog.Fatal("Failed to initialize logger:", err)
			}

			// If you're wondering why we're not using viper.GetStringSlice("toolsets"),
			// it's because viper doesn't handle comma-separated values correctly for env
			// vars when using GetStringSlice.
			// https://github.com/spf13/viper/issues/380
			var enabledToolsets []string
			err = viper.UnmarshalKey("toolsets", &enabledToolsets)
			if err != nil {
				stdlog.Fatal("Failed to unmarshal toolsets:", err)
			}

			logCommands := viper.GetBool("enable-command-logging")
			cfg := runConfig{
				readOnly:           readOnly,
				logger:             logger,
				logCommands:        logCommands,
				exportTranslations: exportTranslations,
				enabledToolsets:    enabledToolsets,
			}
			if err := runSSEServer(cfg); err != nil {
				stdlog.Fatal("failed to run stdio server:", err)
			}
		},
	}
)

func init() {
	cobra.OnInitialize(initConfig)

	rootCmd.SetVersionTemplate("{{.Short}}\n{{.Version}}\n")

	// Add global flags that will be shared by all commands
	rootCmd.PersistentFlags().StringSlice("toolsets", github.DefaultTools, "An optional comma separated list of groups of tools to allow, defaults to enabling all")
	rootCmd.PersistentFlags().Bool("dynamic-toolsets", false, "Enable dynamic toolsets")
	rootCmd.PersistentFlags().Bool("read-only", false, "Restrict the server to read-only operations")
	rootCmd.PersistentFlags().String("log-file", "", "Path to log file")
	rootCmd.PersistentFlags().Bool("enable-command-logging", false, "When enabled, the server will log all command requests and responses to the log file")
	rootCmd.PersistentFlags().Bool("export-translations", false, "Save translations to a JSON file")
	rootCmd.PersistentFlags().String("gh-host", "", "Specify the GitHub hostname (for GitHub Enterprise etc.)")

	// Bind flag to viper
	_ = viper.BindPFlag("toolsets", rootCmd.PersistentFlags().Lookup("toolsets"))
	_ = viper.BindPFlag("dynamic_toolsets", rootCmd.PersistentFlags().Lookup("dynamic-toolsets"))
	_ = viper.BindPFlag("read-only", rootCmd.PersistentFlags().Lookup("read-only"))
	_ = viper.BindPFlag("log-file", rootCmd.PersistentFlags().Lookup("log-file"))
	_ = viper.BindPFlag("enable-command-logging", rootCmd.PersistentFlags().Lookup("enable-command-logging"))
	_ = viper.BindPFlag("export-translations", rootCmd.PersistentFlags().Lookup("export-translations"))
	_ = viper.BindPFlag("host", rootCmd.PersistentFlags().Lookup("gh-host"))

	// Add subcommands
	rootCmd.AddCommand(stdioCmd)
	rootCmd.AddCommand(sseCmd)
}

func initConfig() {
	// Initialize Viper configuration
	viper.SetEnvPrefix("github")
	viper.AutomaticEnv()
}

func initLogger(outPath string) (*log.Logger, error) {
	if outPath == "" {
		return log.New(), nil
	}

	file, err := os.OpenFile(outPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0666)
	if err != nil {
		return nil, fmt.Errorf("failed to open log file: %w", err)
	}

	logger := log.New()
	logger.SetLevel(log.DebugLevel)
	logger.SetOutput(file)

	return logger, nil
}

type runConfig struct {
	readOnly           bool
	logger             *log.Logger
	logCommands        bool
	exportTranslations bool
	enabledToolsets    []string
}


func createGhServer(cfg runConfig) (*server.MCPServer, error, func()) {
	// Create GH client
	token := viper.GetString("personal_access_token")
	if token == "" {
		cfg.logger.Fatal("GITHUB_PERSONAL_ACCESS_TOKEN not set")
	}
	ghClient := gogithub.NewClient(nil).WithAuthToken(token)
	ghClient.UserAgent = fmt.Sprintf("github-mcp-server/%s", version)

	host := viper.GetString("host")

	if host != "" {
		var err error
		ghClient, err = ghClient.WithEnterpriseURLs(host, host)
		if err != nil {
			return nil, fmt.Errorf("failed to create GitHub client with host: %w", err), nil
		}
	}

	t, dumpTranslations := translations.TranslationHelper()

	beforeInit := func(_ context.Context, _ any, message *mcp.InitializeRequest) {
		ghClient.UserAgent = fmt.Sprintf("github-mcp-server/%s (%s/%s)", version, message.Params.ClientInfo.Name, message.Params.ClientInfo.Version)
	}

	getClient := func(_ context.Context) (*gogithub.Client, error) {
		return ghClient, nil // closing over client
	}

	hooks := &server.Hooks{
		OnBeforeInitialize: []server.OnBeforeInitializeFunc{beforeInit},
	}
	// Create server
	ghServer := github.NewServer(version, server.WithHooks(hooks))

	enabled := cfg.enabledToolsets
	dynamic := viper.GetBool("dynamic_toolsets")
	if dynamic {
		// filter "all" from the enabled toolsets
		enabled = make([]string, 0, len(cfg.enabledToolsets))
		for _, toolset := range cfg.enabledToolsets {
			if toolset != "all" {
				enabled = append(enabled, toolset)
			}
		}
	}

	// Create default toolsets
	toolsets, err := github.InitToolsets(enabled, cfg.readOnly, getClient, t)
	context := github.InitContextToolset(getClient, t)

	if err != nil {
		stdlog.Fatal("Failed to initialize toolsets:", err)
	}

	// Register resources with the server
	github.RegisterResources(ghServer, getClient, t)
	// Register the tools with the server
	toolsets.RegisterTools(ghServer)
	context.RegisterTools(ghServer)

	if dynamic {
		dynamic := github.InitDynamicToolset(ghServer, toolsets, t)
		dynamic.RegisterTools(ghServer)
	}

	return ghServer, nil, dumpTranslations
}


func runStdioServer(cfg runConfig) error {
	// Create app context
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	ghServer, _, dumpTranslations := createGhServer(cfg)

	stdioServer := server.NewStdioServer(ghServer)

	stdLogger := stdlog.New(cfg.logger.Writer(), "stdioserver", 0)
	stdioServer.SetErrorLogger(stdLogger)

	if cfg.exportTranslations {
		// Once server is initialized, all translations are loaded
		dumpTranslations()
	}

	// Start listening for messages
	errC := make(chan error, 1)
	go func() {
		in, out := io.Reader(os.Stdin), io.Writer(os.Stdout)

		if cfg.logCommands {
			loggedIO := iolog.NewIOLogger(in, out, cfg.logger)
			in, out = loggedIO, loggedIO
		}

		errC <- stdioServer.Listen(ctx, in, out)
	}()

	// Output github-mcp-server string
	_, _ = fmt.Fprintf(os.Stderr, "GitHub MCP Server running on stdio\n")

	// Wait for shutdown signal
	select {
	case <-ctx.Done():
		cfg.logger.Infof("shutting down server...")
	case err := <-errC:
		if err != nil {
			return fmt.Errorf("error running server: %w", err)
		}
	}

	return nil
}


func runSSEServer(cfg runConfig) error {
	// Create app context
	_, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	ghServer, _, _ := createGhServer(cfg)

	sseServer := server.NewSSEServer(
		ghServer,
		server.WithBaseURL("http://github:3001"),
		server.WithUseFullURLForMessageEndpoint(true),
	)

	mux := http.NewServeMux()
	mux.Handle("/sse", sseServer.SSEHandler())
	mux.Handle("/message", sseServer.MessageHandler())

	log.Printf("Dynamic SSE server listening on %s", ":3001")
	if err := http.ListenAndServe(":3001", mux); err != nil {
		log.Fatalf("Server error: %v", err)
	}

	return nil
}


func main() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}
