import asyncio
from pathlib import Path
import click
from . import common
from .common.config import CLIConfig
from cl_client import ServerPref


@click.command("login")
@click.option("--username", "-u", help="Username for authentication")
@click.option("--password", "-p", help="Password for authentication")
@click.option("--auth-url", help="Auth service URL")
@click.option("--compute-url", help="Compute service URL")
@click.option("--store-url", help="Store service URL")
@click.option("--mqtt-url", help="MQTT broker URL")
@click.option("--no-auth", is_flag=True, help="Use no-auth/guest mode")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def login_command(
    username: str | None,
    password: str | None,
    auth_url: str | None,
    compute_url: str | None,
    store_url: str | None,
    mqtt_url: str | None,
    no_auth: bool,
    output_json: bool,
):
    """Login and save configuration for subsequent commands.

    Examples:
        cl-client login -u admin -p pass123 --auth-url http://localhost:8010
        cl-client login --no-auth
    """

    async def run():
        try:
            # Load base config from file if exists, or use defaults
            try:
                config_file = Path.home() / ".cl_client_config.json"
                if config_file.exists():
                    base_config = CLIConfig.from_file(config_file)
                else:
                    base_config = CLIConfig(server_pref=ServerPref())
            except Exception:
                base_config = CLIConfig(server_pref=ServerPref())

            # Apply CLI overrides
            if auth_url:
                base_config.server_pref.auth_url = auth_url
            if compute_url:
                base_config.server_pref.compute_url = compute_url
            if store_url:
                base_config.server_pref.store_url = store_url
            if mqtt_url:
                base_config.server_pref.mqtt_url = mqtt_url
            if username:
                base_config.username = username
            if password:
                base_config.password = password
            base_config.no_auth = no_auth
            base_config.output_json = output_json

            # Prompt for missing credentials if not in no-auth mode and not JSON mode
            if not no_auth and not output_json:
                if not base_config.username:
                    base_config.username = click.prompt("Username", type=str)
                if not base_config.password:
                    base_config.password = click.prompt("Password", hide_input=True, type=str)

            # Validate by attempting to create session (if credentials provided)
            if base_config.username and base_config.password and not no_auth:
                from cl_client import SessionManager
                server_pref = base_config.to_server_pref()
                session = SessionManager(server_pref=server_pref)
                try:
                    await session.login(base_config.username, base_config.password)
                    await session.close()
                except Exception as e:
                    if output_json:
                        click.echo(f'{{"status": "error", "message": "Authentication failed: {str(e)}"}}')
                    else:
                        click.echo(f"Error: Authentication failed: {e}", err=True)
                    raise SystemExit(1)

            # Save config to cache
            common.save_config_to_cache(base_config)

            # Output success
            if output_json:
                click.echo('{"status": "success", "message": "Logged in successfully"}')
            else:
                click.echo(f"✓ Logged in as {base_config.username or 'guest'}", err=True)
                click.echo(f"  Config cached at ~/.cl_client_cache", err=True)

        except SystemExit:
            raise
        except Exception as e:
            if output_json:
                click.echo(f'{{"status": "error", "message": "{str(e)}"}}')
            else:
                click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)

    asyncio.run(run())
