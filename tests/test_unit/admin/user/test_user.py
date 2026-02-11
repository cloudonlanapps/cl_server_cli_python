"""Unit tests for admin user management commands."""

from unittest.mock import AsyncMock, patch, MagicMock
from click.testing import CliRunner
from cl_client_cli.main import cli
from cl_client.auth_models import UserResponse
from datetime import datetime

@patch("cl_client_cli.admin.user.create.common.get_session_manager")
def test_user_create(mock_get_session, mandatory_args):
    """Test admin user create command."""
    # Mock session and auth_client with proper SDK model
    mock_user = UserResponse(
        id=1,
        username="newuser",
        is_admin=False,
        permissions=["read:jobs"],
        created_at=datetime.now()
    )

    mock_session = AsyncMock()
    mock_session.close = AsyncMock()
    mock_session.auth_client = MagicMock()
    mock_session.auth_client.create_user = AsyncMock(return_value=mock_user)
    mock_get_session.return_value = mock_session

    runner = CliRunner()
    result = runner.invoke(
        cli,
        mandatory_args + ["--username", "admin", "--password", "admin", "admin", "user", "create", "newuser", "pass123"]
    )

    assert result.exit_code == 0
    assert "newuser" in result.output

@patch("cl_client_cli.admin.user.list.common.get_session_manager")
def test_user_list(mock_get_session, mandatory_args):
    """Test admin user list command."""
    mock_users = [
        UserResponse(id=1, username="user1", is_admin=False, permissions=[], created_at=datetime.now()),
        UserResponse(id=2, username="user2", is_admin=True, permissions=[], created_at=datetime.now())
    ]

    mock_session = AsyncMock()
    mock_session.close = AsyncMock()
    mock_session.auth_client = MagicMock()
    mock_session.auth_client.list_users = AsyncMock(return_value=mock_users)
    mock_get_session.return_value = mock_session

    runner = CliRunner()
    result = runner.invoke(
        cli,
        mandatory_args + ["--username", "admin", "--password", "admin", "admin", "user", "list"]
    )

    assert result.exit_code == 0

@patch("cl_client_cli.admin.user.get.common.get_session_manager")
def test_user_get(mock_get_session, mandatory_args):
    """Test admin user get command."""
    mock_user = UserResponse(
        id=1,
        username="testuser",
        is_admin=False,
        permissions=["read:jobs"],
        created_at=datetime.now()
    )

    mock_session = AsyncMock()
    mock_session.close = AsyncMock()
    mock_session.auth_client = MagicMock()
    mock_session.auth_client.get_user = AsyncMock(return_value=mock_user)
    mock_get_session.return_value = mock_session

    runner = CliRunner()
    result = runner.invoke(
        cli,
        mandatory_args + ["--username", "admin", "--password", "admin", "admin", "user", "get", "1"]
    )

    assert result.exit_code == 0
    assert "testuser" in result.output

@patch("cl_client_cli.admin.user.update.common.get_session_manager")
def test_user_update(mock_get_session, mandatory_args):
    """Test admin user update command."""
    mock_user = UserResponse(
        id=1,
        username="testuser",
        is_admin=True,
        permissions=["read:jobs", "write:jobs"],
        created_at=datetime.now()
    )

    mock_session = AsyncMock()
    mock_session.close = AsyncMock()
    mock_session.auth_client = MagicMock()
    mock_session.auth_client.update_user = AsyncMock(return_value=mock_user)
    mock_get_session.return_value = mock_session

    runner = CliRunner()
    result = runner.invoke(
        cli,
        mandatory_args + ["--username", "admin", "--password", "admin", "admin", "user", "update", "1", "--admin"]
    )

    assert result.exit_code == 0

@patch("cl_client_cli.admin.user.delete.common.get_session_manager")
def test_user_delete(mock_get_session, mandatory_args):
    """Test admin user delete command."""
    mock_user = UserResponse(
        id=1,
        username="testuser",
        is_admin=False,
        permissions=[],
        created_at=datetime.now()
    )

    mock_session = AsyncMock()
    mock_session.close = AsyncMock()
    mock_session.auth_client = MagicMock()
    mock_session.auth_client.get_user = AsyncMock(return_value=mock_user)
    mock_session.auth_client.delete_user = AsyncMock()
    mock_get_session.return_value = mock_session

    runner = CliRunner()
    result = runner.invoke(
        cli,
        mandatory_args + ["--username", "admin", "--password", "admin", "admin", "user", "delete", "1", "--yes"]
    )

    assert result.exit_code == 0
