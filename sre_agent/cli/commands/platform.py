"""Platform detection and setup for SRE Agent CLI."""

import shutil
import subprocess
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()


class PlatformDetector:
    """Detect and configure cloud platforms and Kubernetes clusters."""

    def __init__(self):
        """Initialise the platform detector."""
        self.detected_platforms = []
        self.available_clusters = []

    def detect_platforms(self) -> list[str]:
        """Detect available cloud platforms."""
        platforms = []

        # Check for AWS CLI - just check if it's installed
        if shutil.which("aws"):
            platforms.append("aws")

        # Check for GCP CLI - just check if it's installed
        if shutil.which("gcloud"):
            platforms.append("gcp")

        # Note: Azure CLI detection removed for simplicity
        # Most users only need AWS or GCP for Kubernetes clusters

        # Check for kubectl - just check if it's installed
        if shutil.which("kubectl"):
            platforms.append("kubernetes")

        self.detected_platforms = platforms
        return platforms

    def check_platform_configured(self, platform: str) -> bool:
        """Check if a platform is configured with credentials."""
        try:
            if platform == "aws":
                result = subprocess.run(
                    ["aws", "sts", "get-caller-identity"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                return result.returncode == 0

            elif platform == "gcp":
                result = subprocess.run(
                    ["gcloud", "auth", "list", "--filter=status:ACTIVE"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                return result.returncode == 0 and "ACTIVE" in result.stdout

            # Azure support removed for simplicity

            elif platform == "kubernetes":
                result = subprocess.run(
                    ["kubectl", "config", "current-context"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                return result.returncode == 0

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return False

    def _get_aws_region(self) -> str:
        """Get AWS region from user input with common regions as suggestions."""
        console.print("[cyan]Which AWS region are your EKS clusters in?[/cyan]")

        # Get current region as default
        region_result = subprocess.run(
            ["aws", "configure", "get", "region"],
            capture_output=True,
            text=True,
            check=False,
        )
        default_region = (
            region_result.stdout.strip() if region_result.returncode == 0 else "eu-west-2"
        )

        # Common AWS regions for easy selection
        common_regions = [
            "eu-west-2",
            "eu-west-1",
            "eu-central-1",
            "us-east-1",
            "us-east-2",
            "us-west-1",
            "us-west-2",
            "ap-southeast-1",
            "ap-southeast-2",
            "ap-northeast-1",
        ]

        console.print(f"[dim]Common regions: {', '.join(common_regions)}[/dim]")
        return Prompt.ask("AWS region", default=default_region)

    def _list_eks_clusters(self, region: str) -> list[dict[str, str]]:
        """List EKS clusters in the specified AWS region."""
        clusters = []
        console.print(f"[dim]Checking for EKS clusters in {region}...[/dim]")

        # First try with default profile
        result = subprocess.run(
            ["aws", "eks", "list-clusters", "--region", region],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        # If default fails, try to find and use an available profile
        if result.returncode != 0 and "Unable to locate credentials" in result.stderr:
            console.print(
                "[yellow]Default AWS credentials not found, "
                "checking for available profiles...[/yellow]"
            )
            profile = self._find_available_aws_profile()
            if profile:
                console.print(f"[cyan]Using profile: {profile}[/cyan]")
                result = subprocess.run(
                    [
                        "aws",
                        "eks",
                        "list-clusters",
                        "--region",
                        region,
                        "--profile",
                        profile,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )

        if result.returncode == 0:
            import json

            data = json.loads(result.stdout)
            cluster_names = data.get("clusters", [])

            if cluster_names:
                console.print(
                    f"[green]Found {len(cluster_names)} EKS cluster(s) in {region}[/green]"
                )
                for cluster_name in cluster_names:
                    clusters.append(
                        {
                            "name": cluster_name,
                            "platform": "aws",
                            "region": region,
                            "type": "EKS",
                        }
                    )
            else:
                console.print(f"[yellow]No EKS clusters found in {region}[/yellow]")
        else:
            self._handle_eks_listing_error(result, region)

        return clusters

    def _handle_eks_listing_error(self, result: subprocess.CompletedProcess, region: str) -> None:
        """Handle errors when listing EKS clusters."""
        console.print(
            f"[red]Failed to list EKS clusters in {region}: {result.stderr.strip()}[/red]"
        )

        if "AccessDenied" in result.stderr:
            console.print("[yellow]💡 Your AWS credentials might not have EKS permissions[/yellow]")
        elif "InvalidRegion" in result.stderr:
            console.print(f"[yellow]💡 '{region}' might not be a valid AWS region[/yellow]")

    def _list_gke_clusters(self) -> list[dict[str, str]]:
        """List GKE clusters in GCP."""
        clusters = []

        result = subprocess.run(
            ["gcloud", "container", "clusters", "list", "--format=json"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if result.returncode == 0:
            import json

            data = json.loads(result.stdout)
            for cluster in data:
                clusters.append(
                    {
                        "name": cluster.get("name"),
                        "platform": "gcp",
                        "region": cluster.get("zone") or cluster.get("location"),
                        "type": "GKE",
                    }
                )

        return clusters

    def _list_kubectl_contexts(self) -> list[dict[str, str]]:
        """List available kubectl contexts."""
        clusters = []

        result = subprocess.run(
            ["kubectl", "config", "get-contexts", "-o", "name"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        if result.returncode == 0:
            for context in result.stdout.strip().split("\n"):
                if context.strip():
                    clusters.append(
                        {
                            "name": context.strip(),
                            "platform": "kubernetes",
                            "region": "unknown",
                            "type": "Generic",
                        }
                    )

        return clusters

    def get_kubernetes_clusters(self, platform: str) -> list[dict[str, str]]:
        """Get available Kubernetes clusters for a platform."""
        clusters = []

        try:
            if platform == "aws":
                region = self._get_aws_region()
                clusters = self._list_eks_clusters(region)

            elif platform == "gcp":
                clusters = self._list_gke_clusters()

            elif platform == "kubernetes":
                clusters = self._list_kubectl_contexts()

        except Exception as e:
            console.print(
                f"[yellow]Warning: Could not retrieve clusters for {platform}: {e}[/yellow]"
            )

        return clusters

    def setup_aws_credentials(self) -> bool:
        """Setup AWS credentials."""
        console.print(
            Panel(
                "[bold cyan]AWS Credentials Setup[/bold cyan]\n\n"
                "I'll help you configure AWS credentials for EKS access.",
                border_style="cyan",
            )
        )

        console.print("\n[yellow]AWS credentials not found or not working.[/yellow]")
        console.print("\n[bold cyan]📋 Temporary AWS Credentials Setup[/bold cyan]")
        console.print()
        console.print("1. Go to the [bold]AWS access portal[/bold]")
        console.print("2. Select '[bold]Access keys[/bold]'")
        console.print(
            "3. Choose '[bold]Option 2: Add a profile to your AWS credentials file[/bold]'"
        )
        console.print("4. Copy the credentials block (looks like this):")
        console.print()
        console.print("[dim]Example:[/dim]")
        console.print("[dim][554043692091_AdministratorAccess][/dim]")
        console.print("[dim]aws_access_key_id=ASIAYB74T2Q5ZTVKYCB3[/dim]")
        console.print("[dim]aws_secret_access_key=OAiR5jId8NvjQqZRm/Vo/...[/dim]")
        console.print("[dim]aws_session_token=IQoJb3JpZ2luX2VjECEaCWV1...[/dim]")
        console.print()

        if Confirm.ask("Do you have your AWS credentials ready to paste?", default=True):
            return self._setup_aws_credentials_file()
        else:
            console.print(
                "[yellow]Please get your credentials first, then run setup again.[/yellow]"
            )
            return False

    def _find_available_aws_profile(self) -> Optional[str]:
        """Find an available AWS profile that has working credentials."""
        from pathlib import Path

        credentials_file = Path.home() / ".aws" / "credentials"
        if not credentials_file.exists():
            return None

        try:
            profiles = []
            with open(credentials_file) as f:
                for line in f:
                    line = line.strip()  # noqa: PLW2901
                    if line.startswith("[") and line.endswith("]"):
                        profile_name = line[1:-1]
                        if profile_name != "default":  # Skip default since we already tried it
                            profiles.append(profile_name)

            # Test each profile to see if it works
            for profile in profiles:
                try:
                    result = subprocess.run(
                        ["aws", "sts", "get-caller-identity", "--profile", profile],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        check=False,
                    )
                    if result.returncode == 0:
                        return profile
                except Exception:
                    continue

        except Exception:
            pass

        return None

    def _collect_credentials_input(self) -> list[str]:
        """Collect multiline AWS credentials input from user."""
        console.print("\n[bold cyan]📝 Add AWS Credentials[/bold cyan]")
        console.print("Paste your AWS credentials block below:")
        console.print("[dim]Paste all lines, then press Enter on an empty line when done[/dim]")
        console.print()

        credentials_lines = []
        while True:
            try:
                line = input()
                if not line.strip():
                    # Empty line means done
                    break
                else:
                    credentials_lines.append(line)
            except KeyboardInterrupt:
                console.print("\n[red]❌ Setup cancelled[/red]")
                return []

        return credentials_lines

    def _validate_credentials_format(self, credentials_lines: list[str]) -> bool:
        """Validate that the credentials input has the required format."""
        if not credentials_lines:
            console.print("[red]❌ No credentials provided[/red]")
            import sys

            sys.exit(1)

        credentials_content = "\n".join(credentials_lines)
        required_fields = ["aws_access_key_id", "aws_secret_access_key"]

        if not all(field in credentials_content.lower() for field in required_fields):
            console.print("[red]❌ Invalid credentials format. Missing required fields.[/red]")
            console.print("Expected format:")
            console.print("[dim][profile_name][/dim]")
            console.print("[dim]aws_access_key_id=...[/dim]")
            console.print("[dim]aws_secret_access_key=...[/dim]")
            return False

        return True

    def _extract_profile_name(self, credentials_lines: list[str]) -> Optional[str]:
        """Extract the profile name from the credentials input."""
        for line in credentials_lines:
            if line.strip().startswith("[") and line.strip().endswith("]"):
                return line.strip()[1:-1]

        console.print(
            "[red]❌ Could not find profile name in credentials "
            "(should start with [profile_name])[/red]"
        )
        return None

    def _read_existing_profiles(
        self, credentials_file: Path, new_profile_name: str
    ) -> dict[str, list[str]]:
        """Read existing credentials file and exclude the new profile if it exists."""
        existing_profiles = {}

        if credentials_file.exists():
            try:
                with open(credentials_file) as f:
                    current_profile = None
                    for line in f:
                        line = line.strip()  # noqa: PLW2901
                        if line.startswith("[") and line.endswith("]"):
                            current_profile = line[1:-1]
                            if current_profile != new_profile_name:  # Keep other profiles
                                existing_profiles[current_profile] = []
                        elif current_profile and current_profile != new_profile_name:
                            existing_profiles[current_profile].append(line)
            except Exception:
                # If file is corrupted, start fresh
                existing_profiles = {}

        return existing_profiles

    def _write_credentials_file(
        self,
        credentials_file: Path,
        existing_profiles: dict,
        new_profile_name: str,
        credentials_lines: list[str],
    ) -> None:
        """Write the credentials file with existing profiles and new profile."""
        with open(credentials_file, "w") as f:
            # Write existing profiles first
            for profile_name, profile_lines in existing_profiles.items():
                f.write(f"[{profile_name}]\n")
                for line in profile_lines:
                    if line:  # Skip empty lines
                        f.write(f"{line}\n")
                f.write("\n")

            # Write the new profile
            f.write(f"[{new_profile_name}]\n")
            for line in credentials_lines[1:]:  # Skip the [profile_name] line
                if line.strip():  # Skip empty lines
                    f.write(f"{line.strip()}\n")
            f.write("\n")

    def _test_credentials(self, profile_name: str) -> bool:
        """Test the newly added AWS credentials."""
        console.print(f"[cyan]Testing credentials with profile: {profile_name}[/cyan]")

        result = subprocess.run(
            [
                "aws",
                "sts",
                "get-caller-identity",
                "--profile",
                profile_name,
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        if result.returncode == 0:
            console.print("[green]✅ Credentials are working![/green]")
            return True
        else:
            console.print(
                f"[yellow]⚠️  Credentials added but test failed: {result.stderr.strip()}[/yellow]"
            )
            console.print(
                "This might be normal if the credentials are temporary and not yet active."
            )
            return False

    def _setup_aws_credentials_file(self) -> bool:
        """Setup AWS credentials by adding to ~/.aws/credentials file."""
        import os
        from pathlib import Path

        aws_dir = Path.home() / ".aws"
        credentials_file = aws_dir / "credentials"

        # Create .aws directory if it doesn't exist
        aws_dir.mkdir(exist_ok=True)

        # Collect credentials input
        credentials_lines = self._collect_credentials_input()

        # Validate format
        if not self._validate_credentials_format(credentials_lines):
            return False

        try:
            # Extract profile name
            new_profile_name = self._extract_profile_name(credentials_lines)
            if not new_profile_name:
                return False

            # Read existing profiles
            existing_profiles = self._read_existing_profiles(credentials_file, new_profile_name)

            # Write credentials file
            self._write_credentials_file(
                credentials_file, existing_profiles, new_profile_name, credentials_lines
            )

            # Set proper permissions (readable only by user)
            os.chmod(credentials_file, 0o600)

            console.print(f"[green]✅ Credentials added to {credentials_file}[/green]")

            # Test the credentials
            if new_profile_name and self._test_credentials(new_profile_name):
                # Set as default profile if user wants
                if Confirm.ask(
                    f"Set {new_profile_name} as your default AWS profile?",
                    default=True,
                ):
                    self._set_default_aws_profile(new_profile_name)
                return True

            console.print("[green]✅ Credentials added successfully[/green]")
            return True

        except Exception as e:
            console.print(f"[red]❌ Failed to save credentials: {e}[/red]")
            return False

    def _read_profile_credentials(
        self, credentials_file: Path, profile_name: str
    ) -> dict[str, str]:
        """Read credentials for a specific profile from the credentials file."""
        profile_creds = {}

        if credentials_file.exists():
            with open(credentials_file) as f:
                current_profile = None
                for line in f:
                    line = line.strip()  # noqa: PLW2901
                    if line.startswith("[") and line.endswith("]"):
                        current_profile = line[1:-1]
                    elif current_profile == profile_name and "=" in line:
                        key, value = line.split("=", 1)
                        profile_creds[key.strip()] = value.strip()

        return profile_creds

    def _read_existing_profiles_excluding_default(
        self, credentials_file: Path
    ) -> dict[str, list[str]]:
        """Read existing profiles from credentials file, excluding the default profile."""
        existing_profiles = {}

        if credentials_file.exists():
            with open(credentials_file) as f:
                current_profile = None
                for line in f:
                    line = line.strip()  # noqa: PLW2901
                    if line.startswith("[") and line.endswith("]"):
                        current_profile = line[1:-1]
                        if current_profile != "default":  # Keep non-default profiles
                            existing_profiles[current_profile] = []
                    elif current_profile and current_profile != "default":
                        existing_profiles[current_profile].append(line)

        return existing_profiles

    def _write_credentials_with_default_profile(
        self,
        credentials_file: Path,
        profile_creds: dict[str, str],
        existing_profiles: dict[str, list[str]],
    ) -> None:
        """Write credentials file with default profile first, then other profiles."""
        with open(credentials_file, "w") as f:
            # Write default section first
            f.write("[default]\n")
            for key, value in profile_creds.items():
                f.write(f"{key}={value}\n")
            f.write("\n")

            # Write other profiles
            for profile, lines in existing_profiles.items():
                f.write(f"[{profile}]\n")
                for line in lines:
                    if line.strip():
                        f.write(f"{line}\n")
                f.write("\n")

    def _set_default_aws_profile(self, profile_name: str) -> None:
        """Set the default AWS profile in ~/.aws/config."""
        aws_dir = Path.home() / ".aws"
        credentials_file = aws_dir / "credentials"

        try:
            # Read the profile credentials
            profile_creds = self._read_profile_credentials(credentials_file, profile_name)

            if not profile_creds:
                console.print(
                    f"[yellow]⚠️  Could not find credentials for profile {profile_name}[/yellow]"
                )
                return

            # Read existing profiles (excluding default)
            existing_profiles = self._read_existing_profiles_excluding_default(credentials_file)

            # Write credentials file with default section
            self._write_credentials_with_default_profile(
                credentials_file, profile_creds, existing_profiles
            )

            # Set proper permissions
            import os

            os.chmod(credentials_file, 0o600)

            console.print(f"[green]✅ Set {profile_name} as default profile[/green]")

        except Exception as e:
            console.print(f"[yellow]⚠️  Could not set default profile: {e}[/yellow]")

    def setup_gcp_credentials(self) -> bool:
        """Setup GCP credentials."""
        console.print(
            Panel(
                "[bold cyan]GCP Credentials Setup[/bold cyan]\n\n"
                "I'll help you configure GCP credentials for GKE access.",
                border_style="cyan",
            )
        )

        # Check if gcloud is authenticated
        try:
            result = subprocess.run(
                ["gcloud", "auth", "list", "--filter=status:ACTIVE"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode == 0 and "ACTIVE" in result.stdout:
                console.print("[green]✅ GCP credentials are already configured![/green]")
                return True
        except Exception:
            pass

        console.print("\n[yellow]GCP authentication required.[/yellow]")
        console.print("\nSteps:")
        console.print("1. Authenticate: [cyan]gcloud auth login[/cyan]")

        project_id = Prompt.ask("GCP Project ID (optional)", default="")
        if project_id:
            console.print(f"2. Set project: [cyan]gcloud config set project {project_id}[/cyan]")
        else:
            console.print("2. Set project: [cyan]gcloud config set project YOUR_PROJECT_ID[/cyan]")

        console.print("3. Get credentials: [cyan]gcloud auth application-default login[/cyan]")

        return Confirm.ask("Have you completed the GCP setup?")

    def _configure_eks_access(self, cluster_name: str, region: str) -> bool:
        """Configure kubectl access for AWS EKS cluster."""
        cmd = ["aws", "eks", "update-kubeconfig", "--name", cluster_name]
        if region:
            cmd.extend(["--region", region])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)

        if result.returncode == 0:
            console.print(f"[green]✅ Configured kubectl for EKS cluster: {cluster_name}[/green]")
            return True
        else:
            console.print(f"[red]❌ Failed to configure kubectl: {result.stderr}[/red]")
            return False

    def _configure_gke_access(self, cluster_name: str, region: str) -> bool:
        """Configure kubectl access for GCP GKE cluster."""
        cmd = [
            "gcloud",
            "container",
            "clusters",
            "get-credentials",
            cluster_name,
        ]

        if region:
            if "/" in region:  # zone format
                cmd.extend(["--zone", region])
            else:  # region format
                cmd.extend(["--region", region])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)

        if result.returncode == 0:
            console.print(f"[green]✅ Configured kubectl for GKE cluster: {cluster_name}[/green]")
            return True
        else:
            console.print(f"[red]❌ Failed to configure kubectl: {result.stderr}[/red]")
            return False

    def _configure_kubectl_context(self, cluster_name: str) -> bool:
        """Switch kubectl context for generic Kubernetes cluster."""
        result = subprocess.run(
            ["kubectl", "config", "use-context", cluster_name],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        if result.returncode == 0:
            console.print(f"[green]✅ Switched to kubectl context: {cluster_name}[/green]")
            return True
        else:
            console.print(f"[red]❌ Failed to switch context: {result.stderr}[/red]")
            return False

    def configure_kubectl_access(self, cluster: dict[str, str]) -> bool:
        """Configure kubectl access for a cluster."""
        platform = cluster["platform"]
        cluster_name = cluster["name"]
        region = cluster.get("region", "")

        console.print(f"\n[cyan]Configuring kubectl access for {cluster_name}...[/cyan]")

        try:
            if platform == "aws":
                return self._configure_eks_access(cluster_name, region)
            elif platform == "gcp":
                return self._configure_gke_access(cluster_name, region)
            elif platform == "kubernetes":
                return self._configure_kubectl_context(cluster_name)
            else:
                console.print(f"[red]❌ Unsupported platform: {platform}[/red]")
                return False

        except Exception as e:
            console.print(f"[red]❌ Error configuring kubectl: {e}[/red]")
            return False


def _show_platform_setup_header() -> None:
    """Show the platform setup header panel."""
    console.print(
        Panel(
            "[bold cyan]🔍 Platform Detection & Configuration[/bold cyan]\n\n"
            "Let me help you set up your cloud platforms and Kubernetes clusters.",
            border_style="cyan",
            title="Platform Setup",
        )
    )


def _show_no_platforms_detected() -> None:
    """Show message when no platforms are detected."""
    console.print("[yellow]⚠️  No cloud platforms or kubectl detected.[/yellow]")
    console.print("\nPlease install:")
    console.print("• AWS CLI: [cyan]https://aws.amazon.com/cli/[/cyan]")
    console.print("• GCP CLI: [cyan]https://cloud.google.com/sdk/gcloud[/cyan]")
    console.print("• kubectl: [cyan]https://kubernetes.io/docs/tasks/tools/[/cyan]")


def _create_platform_status_table(detector: PlatformDetector, detected: list[str]) -> Table:
    """Create and populate platform status table."""
    platform_table = Table(show_header=True, header_style="bold cyan")
    platform_table.add_column("Platform", style="cyan")
    platform_table.add_column("CLI Installed", justify="center")
    platform_table.add_column("Configured", justify="center")
    platform_table.add_column("CLI Tool")

    for p in ["aws", "gcp", "kubernetes"]:
        if p in detected:
            # Check if configured
            configured = detector.check_platform_configured(p)
            configured_status = "[green]✅ Yes[/green]" if configured else "[yellow]⚠️ No[/yellow]"

            platform_table.add_row(
                p.upper(),
                "[green]✅ Yes[/green]",
                configured_status,
                f"{p} CLI" if p != "kubernetes" else "kubectl",
            )
        else:
            platform_table.add_row(
                p.upper(),
                "[red]❌ No[/red]",
                "[dim]N/A[/dim]",
                f"{p} CLI" if p != "kubernetes" else "kubectl",
            )

    return platform_table


def _filter_platforms_by_request(platform: Optional[str], detected: list[str]) -> list[str]:
    """Filter platforms based on user request."""
    if platform:
        if platform not in detected:
            console.print(f"[red]❌ {platform.upper()} not available or not configured.[/red]")
            return []
        return [platform]
    return detected


def _setup_platform_credentials(detector: PlatformDetector, platform_name: str) -> bool:
    """Setup credentials for a specific platform."""
    configured = detector.check_platform_configured(platform_name)

    if platform_name == "aws":
        if not configured:
            if not detector.setup_aws_credentials():
                return False
        else:
            console.print("[green]✅ AWS credentials already configured![/green]")
    elif platform_name == "gcp":
        if not configured:
            if not detector.setup_gcp_credentials():
                return False
        else:
            console.print("[green]✅ GCP credentials already configured![/green]")
    elif platform_name == "kubernetes":
        if not configured:
            console.print(
                "[yellow]⚠️ No kubectl context set. "
                "We'll help you configure cluster access.[/yellow]"
            )
        else:
            console.print("[green]✅ kubectl context already configured![/green]")

    return True


def _show_clusters_table(clusters: list[dict[str, str]]) -> None:
    """Display clusters in a formatted table."""
    cluster_table = Table(show_header=True, header_style="bold cyan")
    cluster_table.add_column("Cluster Name", style="cyan")
    cluster_table.add_column("Type")
    cluster_table.add_column("Region/Zone")

    for c in clusters:
        cluster_table.add_row(c["name"], c["type"], c["region"])

    console.print(cluster_table)


def _configure_cluster_access(
    detector: PlatformDetector,
    clusters: list[dict[str, str]],
    cluster: Optional[str],
    platform_name: str,
) -> None:
    """Configure kubectl access for clusters."""
    if cluster:
        # Find specific cluster
        target_cluster = next((c for c in clusters if c["name"] == cluster), None)
        if target_cluster:
            detector.configure_kubectl_access(target_cluster)
        else:
            console.print(f"[red]Cluster '{cluster}' not found in {platform_name.upper()}[/red]")

    elif Confirm.ask(f"Configure kubectl access for {platform_name.upper()} clusters?"):
        # Ask user to select clusters
        for c in clusters:
            if Confirm.ask(f"Configure access to {c['name']}?"):
                detector.configure_kubectl_access(c)


def _show_next_steps() -> None:
    """Show next steps after platform configuration."""
    console.print("\n[green]🎉 Platform configuration complete![/green]")
    console.print("\n[cyan]Next steps:[/cyan]")
    console.print(
        "1. Start SRE Agent services: [dim]docker compose -f compose.aws.yaml up -d[/dim]"
    )
    console.print("2. Configure CLI: [dim]sre-agent config setup[/dim]")
    console.print("3. Test diagnosis: [dim]sre-agent diagnose --service myapp[/dim]")


@click.command()
@click.option(
    "--platform",
    type=click.Choice(["aws", "gcp", "kubernetes"]),
    help="Specify platform to configure",
)
@click.option("--cluster", help="Specify cluster name to configure")
def platform(platform: Optional[str], cluster: Optional[str]):
    """Detect and configure cloud platforms and Kubernetes clusters.

    This command helps you:
    - Detect available cloud platforms (AWS, GCP)
    - Find Kubernetes clusters (EKS, GKE, etc.)
    - Configure credentials and kubectl access
    - Set up the SRE Agent for your environment

    Examples:
      # Auto-detect platforms and clusters
      sre-agent platform

      # Configure specific platform
      sre-agent platform --platform aws

      # Configure specific cluster
      sre-agent platform --cluster my-prod-cluster
    """
    detector = PlatformDetector()

    # Show header
    _show_platform_setup_header()

    # Detect platforms
    console.print("\n[cyan]Detecting available platforms...[/cyan]")
    detected = detector.detect_platforms()

    if not detected:
        _show_no_platforms_detected()
        return

    # Show platform status table
    platform_table = _create_platform_status_table(detector, detected)
    console.print(platform_table)

    # Filter platforms based on user request
    platforms_to_configure = _filter_platforms_by_request(platform, detected)
    if not platforms_to_configure:
        return

    # Configure each platform
    for p in platforms_to_configure:
        console.print(f"\n[bold]Configuring {p.upper()}...[/bold]")

        # Setup credentials if needed
        if not _setup_platform_credentials(detector, p):
            continue

        # Get clusters
        console.print(f"\n[cyan]Finding {p.upper()} clusters...[/cyan]")
        clusters = detector.get_kubernetes_clusters(p)

        if not clusters:
            console.print(f"[yellow]No clusters found for {p.upper()}[/yellow]")
            continue

        # Show clusters
        _show_clusters_table(clusters)

        # Configure kubectl for clusters
        _configure_cluster_access(detector, clusters, cluster, p)

    # Show next steps
    _show_next_steps()
