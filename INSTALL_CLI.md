# 🚀 SRE Agent CLI Installation Guide

Congratulations! You now have a powerful, aider-like CLI for your SRE Agent! 

## ✨ What You've Got

Your new **SRE Agent CLI** includes:

- 🎨 **Beautiful ASCII art banner** when you start the tool
- 🔍 **Direct diagnosis** with `sre-agent diagnose --service myapp --cluster prod`  
- 💬 **Interactive mode** with `sre-agent interactive` for conversational debugging
- 📊 **Continuous monitoring** with `sre-agent monitor --watch --namespace production`
- ⚙️ **Easy configuration** with setup wizard and credential management
- 🌈 **Rich terminal output** with colors, tables, and formatted displays

## 🚀 Quick Installation & Setup

### Step 1: Install the CLI

```bash
# Install the CLI in development mode
pip install -e .
```

### Step 2: Complete Setup

```bash
# Interactive setup wizard that handles EVERYTHING:
# - Detects your cloud platforms (AWS/GCP/kubectl)
# - Configures credentials if needed
# - Sets up environment variables (.env file)
# - Starts SRE Agent services automatically
# - Configures CLI settings
sre-agent config setup
```

### Step 3: Start Using!

```bash
sre-agent  # Shows the cool banner
sre-agent diagnose --service myapp
sre-agent interactive
```

> **Note**: If you need to manually start services later, you can use:
> ```bash
> sre-agent startup start --platform aws --wait
> ```

### Option 2: Install as Separate Package

```bash
# Install just the CLI package
pip install -e ./sre_agent/cli

# Or build and install
cd sre_agent/cli
pip install .
```

## 🎯 Usage Examples

### First Time Setup
```bash
# Interactive configuration wizard
sre-agent config setup

# Check your configuration
sre-agent config show
```

### Direct Diagnosis
```bash
# Basic service diagnosis
sre-agent diagnose --service myapp

# With specific cluster and namespace
sre-agent diagnose --service myapp --cluster prod --namespace production

# Follow diagnosis in real-time
sre-agent diagnose --service myapp --follow
```

### Interactive Mode
```bash
# Start interactive session
sre-agent interactive

# With specific context
sre-agent interactive --cluster prod --namespace production
```

Then ask questions like:
- "What's wrong with my service?"
- "Check logs for myapp"
- "Why is my pod crashing?"
- "Analyze recent errors"

### Monitoring
```bash
# Single health check
sre-agent monitor

# Continuous monitoring
sre-agent monitor --watch

# Monitor specific services with custom interval
sre-agent monitor --services myapp --services database --watch --interval 60
```

## ⚙️ Configuration

The CLI automatically detects your bearer token from:
1. `.env` file (`DEV_BEARER_TOKEN=your_token`)
2. Environment variables (`SRE_AGENT_TOKEN`)
3. Configuration wizard

Default config location: `~/.sre-agent.json`

## 🎨 Cool Features

### ASCII Art Banner
When you run `sre-agent` without arguments, you'll see:
```
███████╗██████╗ ███████╗     █████╗  ██████╗ ███████╗███╗   ██╗████████╗
██╔════╝██╔══██╗██╔════╝    ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝
███████╗██████╔╝█████╗      ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   
╚════██║██╔══██╗██╔══╝      ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   
███████║██║  ██║███████╗    ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   
╚══════╝╚═╝  ╚═╝╚══════╝    ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   

🚀 Your AI-powered Site Reliability Engineering assistant
   Diagnose • Monitor • Debug • Scale
```

### Rich Terminal Output
- 🌈 Colorful, formatted output
- 📊 Tables and panels for structured data
- 🔄 Real-time spinners and progress bars
- 💡 Helpful suggestions and recommendations

### Interactive Features
- Tab completion for commands
- Command history
- Context-aware suggestions
- Conversation memory in interactive mode

## 📖 Additional Commands

### Platform Detection & Setup
```bash
# Auto-detect platforms and clusters
sre-agent platform

# Configure specific platform
sre-agent platform --platform aws

# Configure specific cluster  
sre-agent platform --cluster my-prod-cluster
```

### Service Management
```bash
# Start SRE Agent services
sre-agent startup start --platform aws --wait

# Check service status
sre-agent startup status

# View service logs
sre-agent startup logs --service orchestrator

# Stop services
sre-agent startup stop
```

## 🆘 Getting Help

```bash
# General help
sre-agent --help

# Command-specific help  
sre-agent platform --help
sre-agent startup --help
sre-agent diagnose --help
sre-agent interactive --help
sre-agent monitor --help
sre-agent config --help
```

## 🎉 You're All Set!

Your SRE Agent now has a professional, aider-like CLI that makes debugging and monitoring a breeze. The CLI integrates seamlessly with your existing SRE Agent infrastructure and provides a modern, user-friendly interface for all your SRE needs.

**Happy debugging!** 🚀