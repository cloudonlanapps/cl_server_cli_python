"""Shared test fixtures for CLI tests."""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cl_client.models import JobResponse
from cl_client.store_models import (
    Entity,
    EntityListResponse,
    EntityPagination,
    EntityVersion,
    StorePref,
    AuditReport,
    CleanupReport,
)
from cl_client.intelligence_models import EntityIntelligenceData

import asyncio
import json
from typing import Type, TypeVar
import httpx
from click.testing import CliRunner, Result
from pydantic import BaseModel
from cl_client import SessionManager, ServerPref

# Type variable for Pydantic models
T = TypeVar('T', bound=BaseModel)


# ============================================================================
# PYTEST CLI OPTIONS
# ============================================================================


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add CLI options for all tests.

    Values come from: CLI options > config file > defaults.
    Environment variables are NOT supported to avoid undefined behavior.
    """
    parser.addoption(
        "--auth-url",
        action="store",
        default=None,
        help="Auth service URL (or use config file)",
    )
    parser.addoption(
        "--compute-url",
        action="store",
        default=None,
        help="Compute service URL (or use config file)",
    )
    parser.addoption(
        "--store-url",
        action="store",
        default=None,
        help="Store service URL (or use config file)",
    )
    parser.addoption(
        "--mqtt-url",
        action="store",
        default=None,
        help="MQTT broker URL (or use config file)",
    )
    parser.addoption(
        "--username",
        action="store",
        default=None,
        help="Username for authenticated tests (or use config file)",
    )
    parser.addoption(
        "--password",
        action="store",
        default=None,
        help="Password for authenticated tests",
    )


@pytest.fixture(scope="session")
def auth_url(request: pytest.FixtureRequest) -> str:
    """Get auth URL from CLI option, env var, config file, or default to localhost."""
    val = request.config.getoption("--auth-url")
    if val:
        return str(val)

    # Try to load from config file
    from pathlib import Path
    config_path = Path.home() / ".cl_client_config.json"
    if config_path.exists():
        try:
            from cl_client_cli.common.config import CLIConfig
            config = CLIConfig.from_file(config_path)
            if config.server_pref.auth_url:
                return config.server_pref.auth_url
        except Exception:
            pass

    return "http://localhost:8010"


@pytest.fixture(scope="session")
def compute_url(request: pytest.FixtureRequest) -> str:
    """Get compute URL from CLI option, env var, config file, or default to localhost."""
    val = request.config.getoption("--compute-url")
    if val:
        return str(val)

    # Try to load from config file
    from pathlib import Path
    config_path = Path.home() / ".cl_client_config.json"
    if config_path.exists():
        try:
            from cl_client_cli.common.config import CLIConfig
            config = CLIConfig.from_file(config_path)
            if config.server_pref.compute_url:
                return config.server_pref.compute_url
        except Exception:
            pass

    return "http://localhost:8012"


@pytest.fixture(scope="session")
def store_url(request: pytest.FixtureRequest) -> str:
    """Get store URL from CLI option, env var, config file, or default to localhost."""
    val = request.config.getoption("--store-url")
    if val:
        return str(val)

    # Try to load from config file
    from pathlib import Path
    config_path = Path.home() / ".cl_client_config.json"
    if config_path.exists():
        try:
            from cl_client_cli.common.config import CLIConfig
            config = CLIConfig.from_file(config_path)
            if config.server_pref.store_url:
                return config.server_pref.store_url
        except Exception:
            pass

    return "http://localhost:8011"


@pytest.fixture(scope="session")
def mqtt_url(request: pytest.FixtureRequest) -> str:
    """Get MQTT URL from CLI option, env var, config file, or default from config."""
    val = request.config.getoption("--mqtt-url")
    if val:
        return str(val)

    # Try to load from config file
    from pathlib import Path
    config_path = Path.home() / ".cl_client_config.json"
    if config_path.exists():
        try:
            from cl_client_cli.common.config import CLIConfig
            config = CLIConfig.from_file(config_path)
            if config.server_pref.mqtt_url:
                return config.server_pref.mqtt_url
        except Exception:
            pass

    # Default fallback - but should always be set via config file for integration tests
    # Using localhost as last resort for unit tests only
    return "mqtt://localhost:1883"


@pytest.fixture(scope="session")
def username(request: pytest.FixtureRequest) -> str | None:
    """Get username from CLI option, env var, or config file."""
    val = request.config.getoption("--username")
    if val:
        return val

    # Try to load from config file
    from pathlib import Path
    config_path = Path.home() / ".cl_client_config.json"
    if config_path.exists():
        try:
            from cl_client_cli.common.config import CLIConfig
            config = CLIConfig.from_file(config_path)
            if config.username:
                return config.username
        except Exception:
            pass

    return None


@pytest.fixture(scope="session")
def password(request: pytest.FixtureRequest) -> str | None:
    """Get password from CLI option or env var."""
    return request.config.getoption("--password")


@pytest.fixture(scope="session")
def mandatory_args(auth_url, compute_url, store_url, mqtt_url, username, password) -> list[str]:
    """Get mandatory CLI arguments for all commands."""
    args = [
        "--auth-url",
        auth_url,
        "--compute-url",
        compute_url,
        "--store-url",
        store_url,
        "--mqtt-url",
        mqtt_url,
    ]

    # Add username and password if provided (for integration tests)
    if username:
        args.extend(["--username", username])
    if password:
        args.extend(["--password", password])

    return args

# ============================================================================
# TEST ARTIFACT DIRECTORY
# ============================================================================

TEST_ARTIFACT_DIR = Path(os.getenv("TEST_ARTIFACT_DIR", "/tmp/cl_server_test_artifacts")) / "cli_python"
TEST_ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# CLI JSON PARSING HELPERS
# ============================================================================


def _compact_output(output: str) -> str:
    """Compact output for single-line error messages."""
    try:
        # Try to parse and re-dump as compact JSON
        data = json.loads(output)
        return json.dumps(data, separators=(',', ':'))
    except Exception:
        # Fallback to simple newline replacement
        return output.replace('\n', ' ').strip()


def parse_cli_json(result: Result, sdk_model: Type[T]) -> T:
    """Parse CLI JSON output using SDK Pydantic model."""
    assert result.exit_code == 0, f"CLI failed with exit code {result.exit_code}: {_compact_output(result.output)}"

    try:
        data = json.loads(result.output)
        return sdk_model(**data)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Invalid JSON from CLI: {e} Output: {_compact_output(result.output)}")
    except Exception as e:
        raise AssertionError(f"JSON validation failed: {e} Output: {_compact_output(result.output)}")


def parse_cli_json_list(result: Result, item_model: Type[T]) -> list[T]:
    """Parse CLI JSON output as list of SDK models."""
    assert result.exit_code == 0, f"CLI failed with exit code {result.exit_code}: {_compact_output(result.output)}"

    try:
        data = json.loads(result.output)
        if not isinstance(data, list):
            raise AssertionError(f"Expected list, got {type(data)}")
        return [item_model(**item) for item in data]
    except json.JSONDecodeError as e:
        raise AssertionError(f"Invalid JSON from CLI: {e} Output: {_compact_output(result.output)}")
    except Exception as e:
        raise AssertionError(f"JSON validation failed: {e} Output: {_compact_output(result.output)}")


def assert_cli_success(result: Result, expected_message: str | None = None) -> dict:
    """Assert CLI returned success response."""
    assert result.exit_code == 0, f"CLI should have succeeded: {_compact_output(result.output)}"

    try:
        data = json.loads(result.output)
        assert "status" in data, f"Missing status in output: {_compact_output(result.output)}"
        assert data["status"] == "success", f"Expected success status: {_compact_output(result.output)}"

        if expected_message:
            assert "message" in data, f"Missing message in output: {_compact_output(result.output)}"
            assert expected_message in data["message"], \
                f"Expected '{expected_message}' in message: {data['message']}"

        return data
    except json.JSONDecodeError as e:
        raise AssertionError(f"Invalid JSON from CLI: {e} Output: {_compact_output(result.output)}")


def assert_cli_error(result: Result, error_substring: str | None = None) -> dict:
    """Assert CLI returned error response."""
    assert result.exit_code != 0, f"CLI should have failed: {_compact_output(result.output)}"

    try:
        data = json.loads(result.output)
        assert "error" in data, f"Missing error in output: {_compact_output(result.output)}"
        assert "status" in data, f"Missing status in output: {_compact_output(result.output)}"
        assert data["status"] == "failed", f"Expected failed status: {_compact_output(result.output)}"

        if error_substring:
            assert error_substring.lower() in data["error"].lower(), \
                f"Expected '{error_substring}' in error: {data['error']}"

        return data
    except json.JSONDecodeError as e:
        raise AssertionError(f"Invalid JSON from CLI: {e} Output: {_compact_output(result.output)}")


# ============================================================================
# TEST HELPERS
# ============================================================================


class SyncTestHelper:
    """Synchronous helper for setting up test data in integration tests."""

    def __init__(
        self,
        auth_url: str,
        compute_url: str,
        store_url: str,
        mqtt_url: str,
        username: str,
        password: str,
    ):
        self.auth_url = auth_url
        self.compute_url = compute_url
        self.store_url = store_url
        self.mqtt_url = mqtt_url
        self.username = username
        self.password = password
        self._config = ServerPref(
            auth_url=self.auth_url,
            compute_url=self.compute_url,
            store_url=self.store_url,
            mqtt_url=self.mqtt_url,
        )

    async def _get_manager_and_client(self, session: SessionManager):
        await session.login(self.username, self.password)
        manager = session.create_store_manager()
        await manager.__aenter__()
        compute_client = session.create_compute_client()
        return manager, compute_client

    def create_test_entity(self, label: str, image_path: Path):
        """Create a test entity synchronously."""

        async def _create():
            session = SessionManager(server_pref=self._config)
            try:
                manager, _ = await self._get_manager_and_client(session)
                result = await manager.create_entity(label=label, image_path=image_path)
                await manager.__aexit__(None, None, None)
                return result.data.id if result.is_success and result.data else None
            finally:
                await session.close()

        return asyncio.run(_create())

    def wait_for_faces(self, entity_id: int, max_wait: int = 120):
        """Wait for face detection and embedding to complete and return first face_id."""

        async def _wait():
            session = SessionManager(server_pref=self._config)
            try:
                manager, compute_client = await self._get_manager_and_client(session)

                # Step 1: Poll to find the face detection job
                face_job = None
                for _ in range(15):  # Try for 15 seconds
                    await asyncio.sleep(1.0)
                    jobs = await manager.store_client.get_entity_jobs(entity_id)
                    face_detection_jobs = [j for j in jobs if j.task_type == "face_detection"]
                    if face_detection_jobs:
                        face_job = face_detection_jobs[0]
                        break

                if face_job is None:
                    return None

                # Step 2: Wait for detection job completion
                await compute_client.wait_for_job(job_id=face_job.job_id, timeout=60.0)

                # Step 3: Wait for face embedding jobs
                found_embedding = False
                for _ in range(60):  # Wait up to 120 seconds
                    await asyncio.sleep(2.0)
                    jobs = await manager.store_client.get_entity_jobs(entity_id)
                    embedding_jobs = [j for j in jobs if j.task_type == "face_embedding"]
                    if not embedding_jobs:
                        continue

                    statuses = [j.status for j in embedding_jobs]
                    if all(s == "completed" for s in statuses):
                        found_embedding = True
                        break
                    if any(s == "failed" for s in statuses):
                        break

                if found_embedding:
                    await asyncio.sleep(2.0)  # Indexing time

                # Step 4: Poll for faces to appear in database
                face_id = None
                for _ in range(10):  # Try for 10 seconds
                    await asyncio.sleep(1.0)
                    faces = await manager.store_client.get_entity_faces(entity_id=entity_id)
                    if faces:
                        face_id = faces[0].id
                        break

                return face_id
            finally:
                await manager.__aexit__(None, None, None)
                await compute_client.close()
                await session.close()

        return asyncio.run(_wait())

    def wait_for_person(self, entity_id: int, max_wait: int = 60):
        """Wait for person creation and return person_id."""

        async def _wait():
            session = SessionManager(server_pref=self._config)
            await session.login(self.username, self.password)

            manager = session.create_store_manager()
            await manager.__aenter__()

            compute_client = session.create_compute_client()

            try:
                # Step 1: Wait for face detection job
                face_job = None
                for _ in range(10):
                    await asyncio.sleep(1.0)
                    jobs = await manager.store_client.get_entity_jobs(entity_id)
                    face_detection_jobs = [j for j in jobs if j.task_type == "face_detection"]
                    if face_detection_jobs:
                        face_job = face_detection_jobs[0]
                        break

                if face_job is None:
                    return None

                await compute_client.wait_for_job(job_id=face_job.job_id, timeout=30.0)

                # Step 2: Wait for face embedding jobs
                for _ in range(45):  # Try for 90 seconds
                    await asyncio.sleep(2.0)
                    jobs = await manager.store_client.get_entity_jobs(entity_id)
                    face_embedding_jobs = [j for j in jobs if j.task_type == "face_embedding"]

                    # Check if all embedding jobs are completed
                    if face_embedding_jobs and all(j.status == "completed" for j in face_embedding_jobs):
                        break

                # Step 3: Poll for person_id to appear
                person_id = None
                for _ in range(30):  # Try for 30 seconds
                    await asyncio.sleep(1.0)
                    faces = await manager.store_client.get_entity_faces(entity_id=entity_id)
                    if len(faces) > 0 and faces[0].known_person_id is not None:
                        person_id = faces[0].known_person_id
                        break

                return person_id
            finally:
                await compute_client.close()
                await manager.__aexit__(None, None, None)
                await session.close()

        return asyncio.run(_wait())

    def wait_for_clip_embedding(self, entity_id: int, max_wait: int = 60):
        """Wait for CLIP embedding to be generated."""

        async def _wait():
            session = SessionManager(server_pref=self._config)
            await session.login(self.username, self.password)

            manager = session.create_store_manager()
            await manager.__aenter__()

            compute_client = session.create_compute_client()

            try:
                # Step 1: Poll to find the CLIP embedding job
                clip_job = None
                for _ in range(10):
                    await asyncio.sleep(1.0)
                    jobs = await manager.store_client.get_entity_jobs(entity_id)
                    clip_jobs = [j for j in jobs if j.task_type == "clip_embedding"]
                    if clip_jobs:
                        clip_job = clip_jobs[0]
                        break

                if clip_job is None:
                    return False

                # Step 2: Wait for job completion
                final_job = await compute_client.wait_for_job(
                    job_id=clip_job.job_id,
                    timeout=max_wait,
                )

                return final_job.status == "completed"
            finally:
                await compute_client.close()
                await manager.__aexit__(None, None, None)
                await session.close()

        return asyncio.run(_wait())


@pytest.fixture
def test_helper(
    auth_url, compute_url, store_url, mqtt_url, username, password
) -> SyncTestHelper:
    """Synchronous test helper for integration tests."""
    return SyncTestHelper(auth_url, compute_url, store_url, mqtt_url, username, password)


@pytest.fixture
def cli_runner():
    """Create CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def cli_env():
    """Environment variables for CLI commands.

    Empty dict - all configuration is passed via CLI arguments or config file.
    Environment variables are NOT supported to avoid undefined behavior.
    """
    return {}


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================


# Test media directory
TEST_MEDIA_DIR = Path(
    os.getenv("TEST_VECTORS_DIR", str(Path.home() / "cl_server_test_media"))
)


@pytest.fixture
def test_image() -> Path:
    """Get test image with single face."""
    image_path = TEST_MEDIA_DIR / "images" / "test_face_single.jpg"
    if not image_path.exists():
        pytest.skip(f"Test image not found: {image_path}")
    return image_path


@pytest.fixture
def test_image_multiple_faces() -> Path:
    """Get test image with multiple faces."""
    image_path = TEST_MEDIA_DIR / "images" / "test_face_multiple.jpg"
    if not image_path.exists():
        pytest.skip(f"Test image not found: {image_path}")
    return image_path


# ============================================================================
# CLEANUP FIXTURES
# ============================================================================


@pytest.fixture(scope="module", autouse=True)
def cleanup_test_entities(store_url: str, username: str, password: str, auth_url: str):
    """Clean up test entities before and after module runs."""

    def cleanup():
        async def _cleanup():
            try:
                async with httpx.AsyncClient() as client:
                    # Login
                    token_resp = await client.post(
                        f"{auth_url}/auth/token",
                        data={"username": username, "password": password},
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        timeout=5.0,
                    )

                    if token_resp.status_code != 200:
                        return

                    token = token_resp.json()["access_token"]

                    # Try bulk delete first (fastest, requires admin)
                    bulk_resp = await client.delete(
                        f"{store_url}/entities",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=10.0,
                    )

                    if bulk_resp.status_code == 403:
                        # Fallback for non-admin: list and delete individually
                        resp = await client.get(
                            f"{store_url}/entities?page=1&page_size=100",
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=5.0,
                        )

                        if resp.status_code == 200:
                            entities = resp.json().get("items", [])
                            for entity in entities:
                                await client.delete(
                                    f"{store_url}/entities/{entity['id']}",
                                    headers={"Authorization": f"Bearer {token}"},
                                    timeout=5.0,
                                )
            except Exception:
                # Non-fatal cleanup failure
                pass

        asyncio.run(_cleanup())

    # Cleanup before tests
    cleanup()

    yield

    # Cleanup after tests
    cleanup()


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def temp_image_file(tmp_path: Path) -> Path:
    """Create a temporary image file for testing."""
    image_file = tmp_path / "test_image.jpg"
    image_file.write_bytes(b"fake image data")
    return image_file


@pytest.fixture
def temp_video_file(tmp_path: Path) -> Path:
    """Create a temporary video file for testing."""
    video_file = tmp_path / "test_video.mp4"
    video_file.write_bytes(b"fake video data")
    return video_file


@pytest.fixture(autouse=True)
def mock_config(request):
    """Mock CLIConfig.from_file to return empty config during tests.

    Skip this mock for integration tests to allow real config loading.
    """
    # Skip mocking for integration tests - let them use real config file
    if 'integration' in request.keywords:
        yield None
        return

    from cl_client import ServerPref
    from cl_client_cli.common.config import CLIConfig

    with patch("cl_client_cli.common.config.CLIConfig.from_file") as mock:
        mock.return_value = CLIConfig(
            server_pref=ServerPref(),
            username=None,
            password=None,
            no_auth=False,
            output_json=False
        )
        yield mock


@pytest.fixture
def mock_compute_client():
    """Create a mock ComputeClient for CLI testing."""
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.close = AsyncMock(return_value=None)
    mock_client.download_job_file = AsyncMock(return_value=None)

    # Mock plugin clients
    mock_client.clip_embedding = MagicMock()
    mock_client.dino_embedding = MagicMock()
    mock_client.exif = MagicMock()
    mock_client.face_detection = MagicMock()
    mock_client.face_embedding = MagicMock()
    mock_client.hash = MagicMock()
    mock_client.hls_streaming = MagicMock()
    mock_client.image_conversion = MagicMock()
    mock_client.media_thumbnail = MagicMock()

    # Configure the async getter to return our mock instance
    async def mock_get_client_func(ctx):
        return mock_client

    # Patch get_compute_client in all compute submodules where it's used
    # Each module imports it, so we need to patch it in each module's namespace
    patches = [
        patch("cl_client_cli.compute.clip_embedding.get_compute_client", side_effect=mock_get_client_func),
        patch("cl_client_cli.compute.dino_embedding.get_compute_client", side_effect=mock_get_client_func),
        patch("cl_client_cli.compute.exif.get_compute_client", side_effect=mock_get_client_func),
        patch("cl_client_cli.compute.face_detection.get_compute_client", side_effect=mock_get_client_func),
        patch("cl_client_cli.compute.face_embedding.get_compute_client", side_effect=mock_get_client_func),
        patch("cl_client_cli.compute.hash.get_compute_client", side_effect=mock_get_client_func),
        patch("cl_client_cli.compute.hls_streaming.get_compute_client", side_effect=mock_get_client_func),
        patch("cl_client_cli.compute.image_conversion.get_compute_client", side_effect=mock_get_client_func),
        patch("cl_client_cli.compute.media_thumbnail.get_compute_client", side_effect=mock_get_client_func),
    ]

    # Start all patches
    for p in patches:
        p.start()

    yield mock_client

    # Stop all patches
    for p in patches:
        p.stop()


@pytest.fixture
def completed_job() -> JobResponse:
    """Create a completed job response."""
    return JobResponse(
        job_id="test-job-123",
        task_type="clip_embedding",
        status="completed",
        progress=100,
        params={},
        task_output={"embedding": [0.1] * 512},
        error_message=None,
        priority=5,
        created_at=1234567890000,
        updated_at=1234567890000,
        started_at=1234567890000,
        completed_at=1234567891000,
    )


@pytest.fixture
def queued_job() -> JobResponse:
    """Create a queued job response."""
    return JobResponse(
        job_id="test-job-123",
        task_type="clip_embedding",
        status="queued",
        progress=0,
        params={},
        task_output=None,
        error_message=None,
        priority=5,
        created_at=1234567890000,
        updated_at=1234567890000,
        started_at=None,
        completed_at=None,
    )


@pytest.fixture
def failed_job() -> JobResponse:
    """Create a failed job response."""
    return JobResponse(
        job_id="test-job-123",
        task_type="clip_embedding",
        status="failed",
        progress=50,
        params={},
        task_output=None,
        error_message="Test error",
        priority=5,
        created_at=1234567890000,
        updated_at=1234567890000,
        started_at=1234567890000,
        completed_at=1234567891000,
    )


# Store-related fixtures


@pytest.fixture
def mock_store_manager():
    """Create a mock StoreManager for CLI testing."""
    # Create mock manager instance
    mock_manager = MagicMock()
    mock_manager.__aenter__ = AsyncMock(return_value=mock_manager)
    mock_manager.__aexit__ = AsyncMock(return_value=None)

    # Mock all StoreManager methods to return success results
    mock_manager.list_entities = AsyncMock()
    mock_manager.read_entity = AsyncMock()
    mock_manager.create_entity = AsyncMock()
    mock_manager.update_entity = AsyncMock()
    mock_manager.patch_entity = AsyncMock()
    mock_manager.delete_entity = AsyncMock()
    mock_manager.get_versions = AsyncMock()
    mock_manager.get_pref = AsyncMock()
    mock_manager.update_guest_mode = AsyncMock()
    mock_manager.delete_face = AsyncMock()
    mock_manager.get_entity_intelligence = AsyncMock()
    mock_manager.get_audit_report = AsyncMock()
    mock_manager.clear_orphans = AsyncMock()

    # Configure the async getter to return our mock instance
    async def mock_get_manager_func(ctx):
        return mock_manager

    # Patch get_store_manager in all store submodules where it's used
    patches = [
        patch("cl_client_cli.store.list.get_store_manager", side_effect=mock_get_manager_func),
        patch("cl_client_cli.store.create.get_store_manager", side_effect=mock_get_manager_func),
        patch("cl_client_cli.store.get.get_store_manager", side_effect=mock_get_manager_func),
        patch("cl_client_cli.store.update.get_store_manager", side_effect=mock_get_manager_func),
        patch("cl_client_cli.store.patch.get_store_manager", side_effect=mock_get_manager_func),
        patch("cl_client_cli.store.delete.get_store_manager", side_effect=mock_get_manager_func),
        patch("cl_client_cli.store.upload.get_store_manager", side_effect=mock_get_manager_func),
        patch("cl_client_cli.store.versions.get_store_manager", side_effect=mock_get_manager_func),
        patch("cl_client_cli.store.face.get_store_manager", side_effect=mock_get_manager_func),
        patch("cl_client_cli.store.intelligence.get_store_manager", side_effect=mock_get_manager_func),
        # Also patch admin/store modules that use get_store_manager
        patch("cl_client_cli.admin.store.audit.get_store_manager", side_effect=mock_get_manager_func),
        patch("cl_client_cli.admin.store.config.get_store_manager", side_effect=mock_get_manager_func),
        patch("cl_client_cli.admin.store.guest_mode.get_store_manager", side_effect=mock_get_manager_func),
        patch("cl_client_cli.admin.store.orphans.get_store_manager", side_effect=mock_get_manager_func),
    ]

    # Start all patches
    for p in patches:
        p.start()

    yield mock_manager

    # Stop all patches
    for p in patches:
        p.stop()


@pytest.fixture
def sample_entity() -> Entity:
    """Create a sample entity."""
    return Entity(
        id=1,
        label="Test Entity",
        description="Test description",
        is_collection=False,
        file_size=1024,
        mime_type="image/jpeg",
        file_path="/media/test.jpg",
    )


@pytest.fixture
def sample_collection() -> Entity:
    """Create a sample collection entity."""
    return Entity(
        id=2,
        label="Test Collection",
        description="Test collection",
        is_collection=True,
    )


@pytest.fixture
def sample_entity_list() -> EntityListResponse:
    """Create a sample entity list response."""
    return EntityListResponse(
        items=[
            Entity(id=1, label="Entity 1", is_collection=False),
            Entity(id=2, label="Entity 2", is_collection=True),
        ],
        pagination=EntityPagination(
            page=1,
            page_size=20,
            total_items=2,
            total_pages=1,
            has_next=False,
            has_prev=False,
        ),
    )


@pytest.fixture
def sample_versions() -> list[EntityVersion]:
    """Create sample entity versions."""
    return [
        EntityVersion(
            version=1,
            transaction_id=100,
            operation_type="INSERT",
            label="Version 1",
        ),
        EntityVersion(
            version=2,
            transaction_id=101,
            operation_type="UPDATE",
            label="Version 2",
        ),
    ]


@pytest.fixture
def sample_store_pref() -> StorePref:
    """Create a sample store preference."""
    return StorePref(
        guest_mode=False,
        updated_at=1704067200000,
        updated_by="admin",
    )


@pytest.fixture
def sample_audit_report() -> AuditReport:
    """Create a sample audit report."""
    return AuditReport(
        orphaned_files=[],
        orphaned_faces=[],
        orphaned_vectors=[],
        orphaned_mqtt=[],
    )


@pytest.fixture
def sample_cleanup_report() -> CleanupReport:
    """Create a sample cleanup report."""
    return CleanupReport(
        files_deleted=0,
        faces_deleted=0,
        vectors_deleted=0,
        mqtt_cleared=0,
    )


@pytest.fixture
def sample_entity_intelligence() -> EntityIntelligenceData:
    """Create sample intelligence data."""
    return EntityIntelligenceData(
        overall_status="completed",
        last_updated=1704067200000,
        active_jobs=[],
        job_history=[],
    )



