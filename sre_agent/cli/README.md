# SRE Agent CLI

🚀 **Your AI-powered Site Reliability Engineering assistant**

The SRE Agent CLI is a powerful command-line interface that brings AI-powered debugging, monitoring, and troubleshooting capabilities directly to your terminal. Diagnose issues, monitor services, and debug problems across your Kubernetes clusters, GitHub repositories, and Slack channels with natural language commands.

## ✨ Features

- 🔍 **AI-Powered Diagnosis** - Get intelligent insights into service issues
- 💬 **Interactive Mode** - Conversational debugging with your AI assistant
- 📊 **Real-time Monitoring** - Watch your services and get instant alerts
- 🔧 **Easy Configuration** - Simple setup wizard for all your credentials
- 🎨 **Beautiful Output** - Rich, colourful terminal interface
- 🚀 **Fast & Reliable** - Built for production environments

## 🚀 Quick Start

### Installation

```bash
pip install sre-agent-cli
```

### Setup

Run the comprehensive setup wizard to configure everything:

```bash
sre-agent config setup
```

This single command handles:
- ✅ Cloud platform detection (AWS/GCP + kubectl)
- ✅ Environment variable configuration (.env file)
- ✅ Service startup and health checks
- ✅ CLI settings and API configuration

### Basic Usage

```bash
# Direct diagnosis
sre-agent diagnose --service myapp --cluster prod

# Interactive mode
sre-agent interactive

# Continuous monitoring
sre-agent monitor --watch --namespace production
```

## 📖 Commands

### `diagnose`
Diagnose issues with a specific service using AI analysis.

```bash
# Basic service diagnosis
sre-agent diagnose --service myapp

# With specific cluster and namespace
sre-agent diagnose --service myapp --cluster prod --namespace production

# Follow diagnosis in real-time
sre-agent diagnose --service myapp --follow
```

### `interactive`
Start an interactive debugging session with the AI assistant.

```bash
# Start interactive session
sre-agent interactive

# With specific context
sre-agent interactive --cluster prod --namespace production
```

In interactive mode, you can ask questions like:
- "What's wrong with my service?"
- "Check logs for myapp"
- "Why is my pod crashing?"
- "Analyse recent errors"

### `monitor`
Monitor services and infrastructure health.

```bash
# Single health check
sre-agent monitor

# Continuous monitoring
sre-agent monitor --watch

# Monitor specific services
sre-agent monitor --services myapp --services database --watch

# Custom interval and duration
sre-agent monitor --watch --interval 60 --duration 300
```

### `config`
Manage CLI configuration and settings.

```bash
# Interactive setup wizard
sre-agent config setup

# Show current configuration
sre-agent config show

# Validate configuration
sre-agent config validate

# Reset to defaults
sre-agent config reset
```

## ⚙️ Configuration

The CLI stores configuration in `~/.sre-agent.json` by default. You can also use environment variables:

- `SRE_AGENT_TOKEN` - Bearer token for API authentication
- `SRE_AGENT_API_URL` - API endpoint URL (default: http://localhost:8003)
- `SRE_AGENT_DEFAULT_CLUSTER` - Default Kubernetes cluster
- `SRE_AGENT_DEFAULT_NAMESPACE` - Default namespace (default: default)

## 🎨 Output Formats

Choose from multiple output formats:

- `rich` (default) - Beautiful, colourful terminal output
- `json` - Machine-readable JSON format
- `plain` - Simple text output

```bash
sre-agent diagnose --service myapp --output json
```

## 🔧 Advanced Usage

### Custom Configuration File

```bash
sre-agent --config-path /path/to/config.json diagnose --service myapp
```

### Verbose Output

```bash
sre-agent --verbose diagnose --service myapp
```

### Environment Integration

The CLI automatically detects bearer tokens from your `.env` file:

```bash
# In your .env file
DEV_BEARER_TOKEN=your_token_here
```

## 🆘 Getting Help

```bash
# General help
sre-agent --help

# Command-specific help
sre-agent diagnose --help
sre-agent interactive --help
sre-agent monitor --help
sre-agent config --help
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](https://github.com/fuzzylabs/sre-agent/blob/main/CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/fuzzylabs/sre-agent/blob/main/LICENSE) file for details.

## 🙏 Acknowledgements

Built with ❤️ by [Fuzzy Labs](https://fuzzylabs.ai) as part of the [SRE Agent](https://github.com/fuzzylabs/sre-agent) project.
