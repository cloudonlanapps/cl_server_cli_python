"""Unit tests for compute utils module."""

from unittest.mock import AsyncMock, MagicMock, patch
import click
from click.testing import CliRunner
from cl_client import ServerPref, ComputeClient
from cl_client_cli.common.context import CLIContext
from cl_client_cli.common.config import CLIConfig
from cl_client_cli.compute.utils import get_compute_client
import pytest


@pytest.mark.asyncio
async def test_get_compute_client_no_auth_flag():
    """Test get_compute_client with --no-auth flag."""
    config = CLIConfig(
        server_pref=ServerPref(
            compute_url="http://localhost:8012",
        ),
        username=None,
        password=None,
        no_auth=True,
        output_json=False,
    )
    context = CLIContext(config=config)

    ctx = MagicMock(spec=click.Context)
    ctx.obj = context

    # Mock ComputeClient to avoid MQTT connection
    with patch("cl_client_cli.compute.utils.ComputeClient") as mock_client_class:
        mock_client = MagicMock(spec=ComputeClient)
        mock_client.base_url = "http://localhost:8012"
        mock_client_class.return_value = mock_client

        client = await get_compute_client(ctx)

        # Verify ComputeClient was created with no-auth
        mock_client_class.assert_called_once()
        assert client == mock_client


@pytest.mark.asyncio
async def test_get_compute_client_no_credentials():
    """Test get_compute_client with no credentials."""
    config = CLIConfig(
        server_pref=ServerPref(
            compute_url="http://localhost:8012",
        ),
        username=None,
        password=None,
        no_auth=False,
        output_json=False,
    )
    context = CLIContext(config=config)

    ctx = MagicMock(spec=click.Context)
    ctx.obj = context

    # Mock ComputeClient to avoid MQTT connection
    with patch("cl_client_cli.compute.utils.ComputeClient") as mock_client_class:
        mock_client = MagicMock(spec=ComputeClient)
        mock_client.base_url = "http://localhost:8012"
        mock_client_class.return_value = mock_client

        client = await get_compute_client(ctx)

        # Verify ComputeClient was created in no-auth mode
        mock_client_class.assert_called_once()
        assert client == mock_client


@pytest.mark.asyncio
async def test_get_compute_client_username_no_password_json_mode():
    """Test get_compute_client with username but no password in JSON mode."""
    config = CLIConfig(
        server_pref=ServerPref(
            compute_url="http://localhost:8012",
        ),
        username="testuser",
        password=None,
        no_auth=False,
        output_json=True,
    )
    context = CLIContext(config=config)

    ctx = MagicMock(spec=click.Context)
    ctx.obj = context

    # Mock ComputeClient to avoid MQTT connection
    with patch("cl_client_cli.compute.utils.ComputeClient") as mock_client_class:
        mock_client = MagicMock(spec=ComputeClient)
        mock_client.base_url = "http://localhost:8012"
        mock_client_class.return_value = mock_client

        client = await get_compute_client(ctx)

        # Should fall back to no-auth in JSON mode
        mock_client_class.assert_called_once()
        assert client == mock_client


@pytest.mark.asyncio
async def test_get_compute_client_with_credentials_success():
    """Test get_compute_client with valid credentials."""
    config = CLIConfig(
        server_pref=ServerPref(
            auth_url="http://localhost:8010",
            compute_url="http://localhost:8012",
        ),
        username="testuser",
        password="testpass",
        no_auth=False,
        output_json=False,
    )
    context = CLIContext(config=config)

    ctx = MagicMock(spec=click.Context)
    ctx.obj = context

    # Mock SessionManager
    mock_session = AsyncMock()
    mock_session.login = AsyncMock()
    mock_session.close = AsyncMock()
    mock_compute_client = MagicMock(spec=ComputeClient)
    mock_session.create_compute_client = MagicMock(return_value=mock_compute_client)

    with patch("cl_client_cli.compute.utils.SessionManager", return_value=mock_session):
        with patch("cl_client_cli.compute.utils.save_password_to_cache") as mock_save:
            client = await get_compute_client(ctx)

            # Verify login was called
            mock_session.login.assert_called_once_with("testuser", "testpass")

            # Verify password was cached
            mock_save.assert_called_once_with("testuser", "testpass")

            # Verify session stored in context
            assert context.session == mock_session

            # Verify client returned
            assert client == mock_compute_client


@pytest.mark.asyncio
async def test_get_compute_client_with_credentials_auth_failure():
    """Test get_compute_client with authentication failure."""
    config = CLIConfig(
        server_pref=ServerPref(
            auth_url="http://localhost:8010",
            compute_url="http://localhost:8012",
        ),
        username="testuser",
        password="wrongpass",
        no_auth=False,
        output_json=False,
    )
    context = CLIContext(config=config)

    ctx = MagicMock(spec=click.Context)
    ctx.obj = context

    # Mock SessionManager to raise exception on login
    mock_session = AsyncMock()
    mock_session.login = AsyncMock(side_effect=Exception("Invalid credentials"))
    mock_session.close = AsyncMock()

    with patch("cl_client_cli.compute.utils.SessionManager", return_value=mock_session):
        with patch("cl_client_cli.compute.utils.clear_password_cache") as mock_clear:
            with patch("cl_client_cli.compute.utils.output_error") as mock_error:
                await get_compute_client(ctx)

                # Verify session was closed
                mock_session.close.assert_called_once()

                # Verify cache was cleared
                mock_clear.assert_called_once()

                # Verify error was output
                mock_error.assert_called_once()
                assert "Authentication failed" in str(mock_error.call_args[0][1])


