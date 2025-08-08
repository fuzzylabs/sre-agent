"""Environment variable setup utilities for SRE Agent CLI."""

import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table

console = Console()


class EnvSetup:
    """Handles environment variable setup for SRE Agent services."""
    
    def __init__(self, platform: str = 'aws', minimal: bool = False):
        self.platform = platform
        self.minimal = minimal
        self.env_file = Path.cwd() / ".env"
        
    def get_required_env_vars(self) -> Dict[str, Dict[str, str]]:
        """Get required environment variables based on platform and mode."""
        
        if self.minimal:
            # Minimal configuration - only essential variables for basic functionality
            essential_vars = {
                # Security & Access (ESSENTIAL)
                "DEV_BEARER_TOKEN": {
                    "description": "Bearer token for API access (can be any secure string)",
                    "required": True,
                    "sensitive": True,
                    "category": "Security"
                },

                
                # LLM Configuration (ESSENTIAL)
                "PROVIDER": {
                    "description": "LLM Provider (anthropic or google)",
                    "required": True,
                    "sensitive": False,
                    "category": "LLM"
                },
                "MODEL": {
                    "description": "LLM Model name",
                    "required": True,
                    "sensitive": False,
                    "category": "LLM"
                },
                "ANTHROPIC_API_KEY": {
                    "description": "Anthropic API Key (required if using Anthropic)",
                    "required": False,  # Only required if PROVIDER=anthropic
                    "sensitive": True,
                    "category": "LLM"
                },
                "GEMINI_API_KEY": {
                    "description": "Google Gemini API Key (required if using Google)",
                    "required": False,  # Only required if PROVIDER=google
                    "sensitive": True,
                    "category": "LLM"
                },
                
                # GitHub Configuration (REQUIRED - for prompt server)
                "GITHUB_ORGANISATION": {
                    "description": "GitHub Organization name (default: fuzzylabs)",
                    "required": True,
                    "sensitive": False,
                    "category": "GitHub"
                },
                "GITHUB_REPO_NAME": {
                    "description": "GitHub Repository name (default: microservices-demo)",
                    "required": True,
                    "sensitive": False,
                    "category": "GitHub"
                },
                "PROJECT_ROOT": {
                    "description": "Project root directory (default: src)",
                    "required": True,
                    "sensitive": False,
                    "category": "GitHub"
                },
                
                # Docker Compose Required Variables (with defaults for minimal setup)
                "GITHUB_PERSONAL_ACCESS_TOKEN": {
                    "description": "GitHub Personal Access Token (required for GitHub MCP server)",
                    "required": True,
                    "sensitive": True,
                    "category": "GitHub",
                    "default": ""
                },
                "TOOLS": {
                    "description": "Available tools for the agent",
                    "required": False,
                    "sensitive": False,
                    "category": "Configuration",
                    "default": '["list_pods", "get_logs", "get_file_contents"]'
                },
                "SERVICES": {
                    "description": "Services to monitor",
                    "required": False,
                    "sensitive": False,
                    "category": "Configuration", 
                    "default": '["cartservice", "adservice", "emailservice"]'
                },
                
            }
            return essential_vars
        
        # Full configuration - all variables for complete functionality (Slack removed from UI)
        common_vars = {
            # Slack variables intentionally omitted from display/prompt
            
            # GitHub Configuration (OPTIONAL - for reading files and creating issues)
            "GITHUB_PERSONAL_ACCESS_TOKEN": {
                "description": "GitHub Personal Access Token (for reading files and creating issues)",
                "required": False,
                "sensitive": True,
                "category": "GitHub"
            },
            "GITHUB_ORGANISATION": {
                "description": "GitHub Organization name",
                "required": True,
                "sensitive": False,
                "category": "GitHub"
            },
            "GITHUB_REPO_NAME": {
                "description": "GitHub Repository name",
                "required": True,
                "sensitive": False,
                "category": "GitHub"
            },
            "PROJECT_ROOT": {
                "description": "Project root directory in GitHub repo",
                "required": True,
                "sensitive": False,
                "category": "GitHub"
            },
            
            # LLM Configuration
            "PROVIDER": {
                "description": "LLM Provider (anthropic, google)",
                "required": True,
                "sensitive": False,
                "category": "LLM"
            },
            "MODEL": {
                "description": "LLM Model name",
                "required": True,
                "sensitive": False,
                "category": "LLM"
            },
            "ANTHROPIC_API_KEY": {
                "description": "Anthropic API Key (if using Anthropic)",
                "required": False,
                "sensitive": True,
                "category": "LLM"
            },
            "GEMINI_API_KEY": {
                "description": "Google Gemini API Key (if using Google)",
                "required": False,
                "sensitive": True,
                "category": "LLM"
            },
            "MAX_TOKENS": {
                "description": "Maximum tokens for LLM responses",
                "required": False,
                "sensitive": False,
                "category": "LLM"
            },
            
            # Security & Access
            "DEV_BEARER_TOKEN": {
                "description": "Bearer token for API access",
                "required": True,
                "sensitive": True,
                "category": "Security"
            },

        }
        
        # Platform-specific variables (only in full mode)
        if self.platform == 'aws':
            platform_vars = {
                "AWS_REGION": {
                    "description": "AWS Region (used by Kubernetes MCP server to update kubeconfig)",
                    "required": False,  # Optional if kubectl context is already configured
                    "sensitive": False,
                    "category": "AWS"
                },
                "AWS_ACCOUNT_ID": {
                    "description": "AWS Account ID",
                    "required": False,
                    "sensitive": False,
                    "category": "AWS"
                },
                "TARGET_EKS_CLUSTER_NAME": {
                    "description": "Target EKS Cluster Name (used to update kubeconfig)",
                    "required": False,  # Optional if kubectl context is already configured
                    "sensitive": False,
                    "category": "AWS"
                },
            }
        elif self.platform == 'gcp':
            platform_vars = {
                "CLOUDSDK_CORE_PROJECT": {
                    "description": "GCP Project ID (used by Kubernetes MCP server)",
                    "required": False,  # Optional if kubectl context is already configured
                    "sensitive": False,
                    "category": "GCP"
                },
                "CLOUDSDK_COMPUTE_REGION": {
                    "description": "GCP Region (used to update kubeconfig)",
                    "required": False,  # Optional if kubectl context is already configured
                    "sensitive": False,
                    "category": "GCP"
                },
                "TARGET_GKE_CLUSTER_NAME": {
                    "description": "Target GKE Cluster Name (used to update kubeconfig)",
                    "required": False,  # Optional if kubectl context is already configured
                    "sensitive": False,
                    "category": "GCP"
                },
                "QUERY_TIMEOUT": {
                    "description": "Query timeout in seconds",
                    "required": False,
                    "sensitive": False,
                    "category": "GCP"
                },
            }
        else:
            platform_vars = {}
            
        return {**common_vars, **platform_vars}
    
    def load_existing_env(self) -> Dict[str, str]:
        """Load existing environment variables from .env file."""
        env_vars = {}
        
        if self.env_file.exists():
            try:
                with open(self.env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            env_vars[key.strip()] = value.strip().strip('"\'')
            except Exception as e:
                console.print(f"[yellow]Warning: Could not read .env file: {e}[/yellow]")
                
        return env_vars
    
    def check_missing_env_vars(self) -> Tuple[List[str], List[str]]:
        """Check for missing required and optional environment variables."""
        required_vars = self.get_required_env_vars()
        existing_vars = self.load_existing_env()
        
        missing_required = []
        missing_optional = []
        
        # Get the selected provider to determine which API key is required
        selected_provider = existing_vars.get("PROVIDER")
        
        for var_name, config in required_vars.items():
            if var_name not in existing_vars or not existing_vars[var_name]:
                is_required = config['required']
                
                # Dynamic requirement for API keys based on provider
                if var_name == "ANTHROPIC_API_KEY" and selected_provider == "anthropic":
                    is_required = True
                elif var_name == "GEMINI_API_KEY" and selected_provider == "google":
                    is_required = True
                elif var_name in ["ANTHROPIC_API_KEY", "GEMINI_API_KEY"] and selected_provider:
                    # If provider is selected but this isn't the matching API key, skip it entirely
                    continue
                
                if is_required:
                    missing_required.append(var_name)
                else:
                    missing_optional.append(var_name)
                    
        return missing_required, missing_optional
    
    def display_env_status(self) -> bool:
        """Display current environment variable status. Returns True if all required vars are set."""
        required_vars = self.get_required_env_vars()
        existing_vars = self.load_existing_env()
        missing_required, missing_optional = self.check_missing_env_vars()
        
        # Get selected provider for dynamic API key requirements
        selected_provider = existing_vars.get("PROVIDER")
        
        # Group by category
        categories = {}
        for var_name, config in required_vars.items():
            # Skip API keys that don't match the selected provider
            if var_name in ["ANTHROPIC_API_KEY", "GEMINI_API_KEY"] and selected_provider:
                if var_name == "ANTHROPIC_API_KEY" and selected_provider != "anthropic":
                    continue
                elif var_name == "GEMINI_API_KEY" and selected_provider != "google":
                    continue
            
            category = config['category']
            if category not in categories:
                categories[category] = []
            
            status = "✅" if var_name in existing_vars and existing_vars[var_name] else "❌"
            value = existing_vars.get(var_name, "Not set")
            
            # Mask sensitive values
            if config['sensitive'] and value != "Not set":
                if len(value) > 6:
                    value = f"{value[:3]}...{value[-3:]}"
                else:
                    value = "*" * len(value)
            
            # Dynamic requirement for API keys
            is_required = config['required']
            if var_name == "ANTHROPIC_API_KEY" and selected_provider == "anthropic":
                is_required = True
            elif var_name == "GEMINI_API_KEY" and selected_provider == "google":
                is_required = True
            
            categories[category].append({
                'name': var_name,
                'status': status,
                'value': value,
                'required': is_required
            })
        
        console.print("\n[bold]Environment Variables Status:[/bold]")
        
        for category, vars_list in categories.items():
            table = Table(title=f"{category} Configuration", show_header=True)
            table.add_column("Variable", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Value", style="dim")
            table.add_column("Required", style="yellow")
            
            for var_info in vars_list:
                table.add_row(
                    var_info['name'],
                    var_info['status'],
                    var_info['value'],
                    "Yes" if var_info['required'] else "No"
                )
            
            console.print(table)
            console.print()
        
        if missing_required:
            console.print(f"[red]❌ Missing {len(missing_required)} required variables[/red]")
            return False
        else:
            console.print("[green]✅ All required environment variables are set[/green]")
            return True
    
    def get_cluster_name_from_kubectl(self) -> Optional[str]:
        """Try to get cluster name from current kubectl context."""
        try:
            result = subprocess.run(
                ['kubectl', 'config', 'current-context'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                context = result.stdout.strip()
                # Extract cluster name from context
                if self.platform == 'aws' and 'eks' in context.lower():
                    # AWS EKS context format: arn:aws:eks:region:account:cluster/cluster-name
                    if '/cluster/' in context:
                        return context.split('/cluster/')[-1]
                    elif context.startswith('arn:aws:eks:'):
                        return context.split('/')[-1]
                elif self.platform == 'gcp' and 'gke' in context.lower():
                    # GCP GKE context format: gke_project_zone_cluster-name
                    parts = context.split('_')
                    if len(parts) >= 4:
                        return parts[-1]
                
                # Fallback: use the context name itself
                return context
        except Exception:
            pass
        return None
    
    def get_aws_region_from_config(self) -> Optional[str]:
        """Try to get AWS region from AWS CLI config."""
        try:
            result = subprocess.run(
                ['aws', 'configure', 'get', 'region'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None
    
    def get_gcp_project_from_config(self) -> Optional[str]:
        """Try to get GCP project from gcloud config."""
        try:
            result = subprocess.run(
                ['gcloud', 'config', 'get-value', 'project'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                project = result.stdout.strip()
                return project if project != "(unset)" else None
        except Exception:
            pass
        return None
    
    def interactive_setup(self) -> bool:
        """Interactive setup of environment variables."""
        mode_text = "Minimal" if self.minimal else "Full"
        console.print(f"\n[bold]{mode_text} Environment Variable Setup for {self.platform.upper()}[/bold]")
        if self.minimal:
            console.print("[dim]Setting up only essential variables for basic SRE Agent functionality...[/dim]")
            console.print("[dim]Slack integration and GitHub file access will be disabled.[/dim]\n")
        else:
            console.print("[dim]Setting up all environment variables for complete SRE Agent functionality...[/dim]\n")
        
        required_vars = self.get_required_env_vars()
        existing_vars = self.load_existing_env()
        missing_required, missing_optional = self.check_missing_env_vars()
        
        if not missing_required and not missing_optional:
            console.print("[green]✅ All environment variables are already configured![/green]")
            return True
        
        # Show what we need to configure
        if missing_required:
            console.print(f"[yellow]Missing {len(missing_required)} required variables:[/yellow]")
            for var in missing_required:
                console.print(f"  • {var}")
        
        # Filter out API keys from optional variables display
        optional_vars_display = [var for var in missing_optional 
                               if var not in ['ANTHROPIC_API_KEY', 'GEMINI_API_KEY']]
        
        if optional_vars_display:
            console.print(f"[dim]Missing {len(optional_vars_display)} optional variables:[/dim]")
            for var in optional_vars_display:
                console.print(f"  • {var}")
        
        console.print()
        
        if not Confirm.ask("Configure environment variables now?", default=True):
            console.print("[yellow]Environment variables are required for services to work properly.[/yellow]")
            return False
        
        # Configure variables
        updated_vars = existing_vars.copy()
        
        # Auto-detect some values
        if self.platform == 'aws':
            if 'AWS_REGION' not in updated_vars:
                auto_region = self.get_aws_region_from_config()
                if auto_region:
                    console.print(f"[green]Auto-detected AWS region: {auto_region}[/green]")
                    updated_vars['AWS_REGION'] = auto_region
            
            if 'TARGET_EKS_CLUSTER_NAME' not in updated_vars:
                auto_cluster = self.get_cluster_name_from_kubectl()
                if auto_cluster:
                    console.print(f"[green]Auto-detected EKS cluster: {auto_cluster}[/green]")
                    updated_vars['TARGET_EKS_CLUSTER_NAME'] = auto_cluster
                else:
                    # Try to get cluster name from AWS CLI if kubectl context is not available
                    try:
                        result = subprocess.run(['aws', 'eks', 'list-clusters', '--region', updated_vars.get('AWS_REGION', 'eu-west-2')], 
                                              capture_output=True, text=True, timeout=30)
                        if result.returncode == 0:
                            import json
                            data = json.loads(result.stdout)
                            clusters = data.get('clusters', [])
                            if clusters:
                                console.print(f"[cyan]Found {len(clusters)} EKS cluster(s) in {updated_vars.get('AWS_REGION', 'eu-west-2')}[/cyan]")
                                if len(clusters) == 1:
                                    cluster_name = clusters[0]
                                    console.print(f"[green]Auto-detected single EKS cluster: {cluster_name}[/green]")
                                    updated_vars['TARGET_EKS_CLUSTER_NAME'] = cluster_name
                                else:
                                    console.print("Available clusters:")
                                    for i, cluster in enumerate(clusters, 1):
                                        console.print(f"  {i}. {cluster}")
                                    choice = Prompt.ask("Select cluster for TARGET_EKS_CLUSTER_NAME", 
                                                      choices=[str(i) for i in range(1, len(clusters) + 1)], default="1")
                                    cluster_idx = int(choice) - 1
                                    updated_vars['TARGET_EKS_CLUSTER_NAME'] = clusters[cluster_idx]
                    except Exception as e:
                        console.print(f"[yellow]Could not auto-detect EKS cluster: {e}[/yellow]")
                        # Prompt user to enter cluster name manually
                        console.print("[cyan]Please enter your EKS cluster name manually:[/cyan]")
                        cluster_name = Prompt.ask("TARGET_EKS_CLUSTER_NAME")
                        if cluster_name:
                            updated_vars['TARGET_EKS_CLUSTER_NAME'] = cluster_name
                        else:
                            console.print("[yellow]TARGET_EKS_CLUSTER_NAME will not be set. You may need to set it manually later.[/yellow]")
        
        elif self.platform == 'gcp':
            if 'CLOUDSDK_CORE_PROJECT' not in updated_vars:
                auto_project = self.get_gcp_project_from_config()
                if auto_project:
                    console.print(f"[green]Auto-detected GCP project: {auto_project}[/green]")
                    updated_vars['CLOUDSDK_CORE_PROJECT'] = auto_project
            
            if 'TARGET_GKE_CLUSTER_NAME' not in updated_vars:
                auto_cluster = self.get_cluster_name_from_kubectl()
                if auto_cluster:
                    console.print(f"[green]Auto-detected GKE cluster: {auto_cluster}[/green]")
                    updated_vars['TARGET_GKE_CLUSTER_NAME'] = auto_cluster
        
        # Configure missing required variables
        for var_name in missing_required:
            if var_name in updated_vars:
                continue  # Already auto-detected
                
            config = required_vars[var_name]
            
            # Special handling for PROVIDER - show as a choice menu
            if var_name == "PROVIDER":
                console.print(f"\n[cyan]LLM Provider Selection[/cyan]")
                console.print("Which LLM provider would you like to use?")
                console.print("  1. Anthropic (Claude)")
                console.print("  2. Google (Gemini)")
                
                choice = Prompt.ask("Choose provider", choices=["1", "2"], default="1")
                if choice == "1":
                    updated_vars["PROVIDER"] = "anthropic"
                    console.print("[green]Selected: Anthropic (Claude)[/green]")
                else:
                    updated_vars["PROVIDER"] = "google"
                    console.print("[green]Selected: Google (Gemini)[/green]")
                continue
            
            console.print(f"\n[cyan]{var_name}[/cyan] ({config['description']})")
            
            # Provide defaults for some variables
            default_value = ""
            if var_name == "MODEL":
                if updated_vars.get("PROVIDER") == "anthropic":
                    default_value = "claude-3-5-sonnet-20241022"
                elif updated_vars.get("PROVIDER") == "google":
                    default_value = "gemini-1.5-pro"
            elif var_name == "MAX_TOKENS":
                default_value = "4000"
            elif var_name == "PROJECT_ROOT":
                default_value = "src" if self.minimal else "."
            elif var_name == "GITHUB_ORGANISATION" and self.minimal:
                default_value = "fuzzylabs"
            elif var_name == "GITHUB_REPO_NAME" and self.minimal:
                default_value = "microservices-demo"
            elif var_name == "DEV_BEARER_TOKEN":
                default_value = "dev_token_" + str(hash("sre-agent"))[:8]
            
            value = Prompt.ask(f"Enter {var_name}", default=default_value)
            if value:
                updated_vars[var_name] = value
            elif config['required']:
                # For required variables, empty values are not allowed
                console.print(f"[red]❌ {var_name} is required and cannot be empty[/red]")
                return False
        
        # Now handle the API key based on selected provider
        selected_provider = updated_vars.get("PROVIDER")
        if selected_provider:
            api_key_var = f"{selected_provider.upper()}_API_KEY"
            if selected_provider == "google":
                api_key_var = "GEMINI_API_KEY"
            
            if api_key_var not in updated_vars or not updated_vars[api_key_var]:
                console.print(f"\n[cyan]{api_key_var}[/cyan] (Required for {selected_provider} provider)")
                if selected_provider == "anthropic":
                    console.print("Get your API key from: https://console.anthropic.com/")
                elif selected_provider == "google":
                    console.print("Get your API key from: https://aistudio.google.com/app/apikey")
                
                api_key = Prompt.ask(f"Enter {api_key_var}")
                if api_key:
                    updated_vars[api_key_var] = api_key
                else:
                    console.print(f"[red]❌ {api_key_var} is required for the selected provider[/red]")
                    return False
        
        # Ask about optional variables (skip API keys and Slack vars)
        optional_vars_to_configure = [
            var for var in missing_optional
            if var not in ['ANTHROPIC_API_KEY', 'GEMINI_API_KEY', 'SLACK_BOT_TOKEN', 'SLACK_SIGNING_SECRET', 'SLACK_TEAM_ID', 'SLACK_CHANNEL_ID']
        ]
        
        if optional_vars_to_configure:
            console.print(f"\n[dim]Optional variables (you can skip these for now):[/dim]")
            for var_name in optional_vars_to_configure:
                config = required_vars[var_name]
                if Confirm.ask(f"Configure {var_name}? ({config['description']})", default=False):
                    value = Prompt.ask(f"Enter {var_name}")
                    if value:
                        updated_vars[var_name] = value
        
        # Set Slack variables to null silently (hidden from prompts)
        updated_vars["SLACK_BOT_TOKEN"] = "null"
        updated_vars["SLACK_TEAM_ID"] = "null"
        updated_vars["SLACK_SIGNING_SECRET"] = "null"
        updated_vars["SLACK_CHANNEL_ID"] = "null"
        
        # Add default values for Docker Compose required variables (minimal setup)
        if self.minimal:
            required_vars = self.get_required_env_vars()
            for var_name, config in required_vars.items():
                if var_name not in updated_vars and 'default' in config:
                    updated_vars[var_name] = config['default']
            
            # Add AWS region if not set
            if self.platform == 'aws' and 'AWS_REGION' not in updated_vars:
                auto_region = self.get_aws_region_from_config()
                if auto_region:
                    updated_vars['AWS_REGION'] = auto_region
                else:
                    updated_vars['AWS_REGION'] = 'eu-west-2'  # Default region
            
            # Ensure unused API key is empty (not missing)
            selected_provider = updated_vars.get("PROVIDER")
            if selected_provider == "anthropic" and "GEMINI_API_KEY" not in updated_vars:
                updated_vars["GEMINI_API_KEY"] = ""
            elif selected_provider == "google" and "ANTHROPIC_API_KEY" not in updated_vars:
                updated_vars["ANTHROPIC_API_KEY"] = ""

        # Save to .env file
        try:
            self.save_env_file(updated_vars)
            console.print(f"\n[green]✅ Environment variables saved to {self.env_file}[/green]")
            return True
        except Exception as e:
            console.print(f"[red]❌ Failed to save .env file: {e}[/red]")
            return False
    
    def save_env_file(self, env_vars: Dict[str, str]) -> None:
        """Save environment variables to .env file."""
        with open(self.env_file, 'w') as f:
            f.write("# SRE Agent Environment Variables\n")
            f.write("# Generated by sre-agent CLI\n\n")
            
            # Group by category for better organization
            required_vars = self.get_required_env_vars()
            categories = {}
            
            for var_name, value in env_vars.items():
                if var_name in required_vars:
                    category = required_vars[var_name]['category']
                    if category not in categories:
                        categories[category] = []
                    categories[category].append((var_name, value))
                else:
                    # Unknown variable, put in misc
                    if 'Misc' not in categories:
                        categories['Misc'] = []
                    categories['Misc'].append((var_name, value))
            
            for category, vars_list in categories.items():
                f.write(f"# {category} Configuration\n")
                for var_name, value in vars_list:
                    f.write(f"{var_name}={value}\n")
                f.write("\n")