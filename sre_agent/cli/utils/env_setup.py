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
                "HF_TOKEN": {
                    "description": "Hugging Face token for Llama Guard (required for security)",
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
                
                # GitHub Configuration (MINIMAL - for prompt server)
                "GITHUB_ORGANISATION": {
                    "description": "GitHub Organization name (default: fuzzylabs)",
                    "required": False,
                    "sensitive": False,
                    "category": "GitHub"
                },
                "GITHUB_REPO_NAME": {
                    "description": "GitHub Repository name (default: microservices-demo)",
                    "required": False,
                    "sensitive": False,
                    "category": "GitHub"
                },
                "PROJECT_ROOT": {
                    "description": "Project root directory (default: src)",
                    "required": False,
                    "sensitive": False,
                    "category": "GitHub"
                },
            }
            return essential_vars
        
        # Full configuration - all variables for complete functionality
        common_vars = {
            # Slack Configuration (OPTIONAL - for future sre-agent alert slack)
            "SLACK_BOT_TOKEN": {
                "description": "Slack Bot Token for the SRE Agent",
                "required": False,
                "sensitive": True,
                "category": "Slack"
            },
            "SLACK_SIGNING_SECRET": {
                "description": "Slack App Signing Secret",
                "required": False,
                "sensitive": True,
                "category": "Slack"
            },
            "SLACK_TEAM_ID": {
                "description": "Slack Team ID",
                "required": False,
                "sensitive": False,
                "category": "Slack"
            },
            "SLACK_CHANNEL_ID": {
                "description": "Slack Channel ID for responses",
                "required": False,
                "sensitive": False,
                "category": "Slack"
            },
            
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
            "HF_TOKEN": {
                "description": "Hugging Face token for Llama Guard",
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
        
        for var_name, config in required_vars.items():
            if var_name not in existing_vars or not existing_vars[var_name]:
                if config['required']:
                    missing_required.append(var_name)
                else:
                    missing_optional.append(var_name)
                    
        return missing_required, missing_optional
    
    def display_env_status(self) -> bool:
        """Display current environment variable status. Returns True if all required vars are set."""
        required_vars = self.get_required_env_vars()
        existing_vars = self.load_existing_env()
        missing_required, missing_optional = self.check_missing_env_vars()
        
        # Group by category
        categories = {}
        for var_name, config in required_vars.items():
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
            
            categories[category].append({
                'name': var_name,
                'status': status,
                'value': value,
                'required': config['required']
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
        
        if missing_optional:
            console.print(f"[dim]Missing {len(missing_optional)} optional variables:[/dim]")
            for var in missing_optional:
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
            console.print(f"\n[cyan]{var_name}[/cyan] ({config['description']})")
            
            # Provide defaults for some variables
            default_value = ""
            if var_name == "PROVIDER":
                default_value = "anthropic"
            elif var_name == "MODEL":
                if updated_vars.get("PROVIDER") == "anthropic" or not updated_vars.get("PROVIDER"):
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
        
        # Ask about optional variables
        if missing_optional:
            console.print(f"\n[dim]Optional variables (you can skip these for now):[/dim]")
            for var_name in missing_optional:
                config = required_vars[var_name]
                if Confirm.ask(f"Configure {var_name}? ({config['description']})", default=False):
                    value = Prompt.ask(f"Enter {var_name}")
                    if value:
                        updated_vars[var_name] = value
        
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