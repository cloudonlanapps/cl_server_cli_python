"""Unit tests for store utils module."""

from unittest.mock import AsyncMock, MagicMock, patch
import click
from click.testing import CliRunner
from cl_client import ServerPref, StoreManager
from cl_client_cli.common.context import CLIContext
from cl_client_cli.common.config import CLIConfig
from cl_client_cli.store.utils import get_store_manager
import pytest


@pytest.mark.asyncio
async def test_get_store_manager_no_auth_flag():
    """Test get_store_manager with --no-auth flag."""
    config = CLIConfig(
        server_pref=ServerPref(
            store_url="http://localhost:8011",
        ),
        username=None,
        password=None,
        no_auth=True,
        output_json=False,
    )
    context = CLIContext(config=config)

    ctx = MagicMock(spec=click.Context)
    ctx.obj = context

    with patch("cl_client_cli.store.utils.StoreManager.guest") as mock_guest:
        mock_manager = MagicMock(spec=StoreManager)
        mock_guest.return_value = mock_manager

        manager = await get_store_manager(ctx)

        # Verify guest mode was used
        mock_guest.assert_called_once_with(base_url="http://localhost:8011")
        assert manager == mock_manager


@pytest.mark.asyncio
async def test_get_store_manager_no_credentials():
    """Test get_store_manager with no credentials."""
    config = CLIConfig(
        server_pref=ServerPref(
            store_url="http://localhost:8011",
        ),
        username=None,
        password=None,
        no_auth=False,
        output_json=False,
    )
    context = CLIContext(config=config)

    ctx = MagicMock(spec=click.Context)
    ctx.obj = context

    with patch("cl_client_cli.store.utils.StoreManager.guest") as mock_guest:
        mock_manager = MagicMock(spec=StoreManager)
        mock_guest.return_value = mock_manager

        manager = await get_store_manager(ctx)

        # Should use guest mode when no credentials provided
        mock_guest.assert_called_once_with(base_url="http://localhost:8011")
        assert manager == mock_manager


@pytest.mark.asyncio
async def test_get_store_manager_username_no_password_json_mode():
    """Test get_store_manager with username but no password in JSON mode."""
    config = CLIConfig(
        server_pref=ServerPref(
            store_url="http://localhost:8011",
        ),
        username="testuser",
        password=None,
        no_auth=False,
        output_json=True,
    )
    context = CLIContext(config=config)

    ctx = MagicMock(spec=click.Context)
    ctx.obj = context

    with patch("cl_client_cli.store.utils.StoreManager.guest") as mock_guest:
        mock_manager = MagicMock(spec=StoreManager)
        mock_guest.return_value = mock_manager

        manager = await get_store_manager(ctx)

        # Should fall back to guest mode in JSON mode
        mock_guest.assert_called_once_with(base_url="http://localhost:8011")
        assert manager == mock_manager


@pytest.mark.asyncio
async def test_get_store_manager_with_credentials_success():
    """Test get_store_manager with valid credentials."""
    config = CLIConfig(
        server_pref=ServerPref(
            auth_url="http://localhost:8010",
            store_url="http://localhost:8011",
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
    mock_store_manager = MagicMock(spec=StoreManager)
    mock_session.create_store_manager = MagicMock(return_value=mock_store_manager)

    with patch("cl_client_cli.store.utils.SessionManager", return_value=mock_session):
        with patch("cl_client_cli.store.utils.save_password_to_cache") as mock_save:
            manager = await get_store_manager(ctx)

            # Verify login was called
            mock_session.login.assert_called_once_with("testuser", "testpass")

            # Verify password was cached
            mock_save.assert_called_once_with("testuser", "testpass")

            # Verify session stored in context
            assert context.session == mock_session

            # Verify manager returned
            assert manager == mock_store_manager


@pytest.mark.asyncio
async def test_get_store_manager_with_credentials_auth_failure():
    """Test get_store_manager with authentication failure."""
    config = CLIConfig(
        server_pref=ServerPref(
            auth_url="http://localhost:8010",
            store_url="http://localhost:8011",
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

    with patch("cl_client_cli.store.utils.SessionManager", return_value=mock_session):
        with patch("cl_client_cli.store.utils.clear_password_cache") as mock_clear:
            with patch("cl_client_cli.store.utils.output_error") as mock_error:
                await get_store_manager(ctx)

                # Verify session was closed
                mock_session.close.assert_called_once()

                # Verify cache was cleared
                mock_clear.assert_called_once()

                # Verify error was output
                mock_error.assert_called_once()
                assert "Authentication failed" in str(mock_error.call_args[0][1])


