"""Integration test configuration for CLI database features.

These tests require running services and use the CLI to test database operations.
Run with:
    pytest tests/test_integration/ --auth-url=http://localhost:8000 --compute-url=http://localhost:8002 --store-url=http://localhost:8001 --username=admin --password=admin
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Type, TypeVar

import httpx
import pytest
from click.testing import CliRunner, Result
from pydantic import BaseModel

from cl_client import SessionManager, ServerConfig

# Type variable for Pydantic models
T = TypeVar('T', bound=BaseModel)


# ============================================================================
# CLI OPTIONS
# ============================================================================


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add CLI options for integration tests."""
    parser.addoption(
        "--auth-url",
        action="store",
        default="http://localhost:8010",
        help="Auth service URL (default: http://localhost:8010)",
    )
    parser.addoption(
        "--compute-url",
        action="store",
        default="http://localhost:8012",
        help="Compute service URL (default: http://localhost:8012)",
    )
    parser.addoption(
        "--store-url",
        action="store",
        default="http://localhost:8011",
        help="Store service URL (default: http://localhost:8011)",
    )
    parser.addoption(
        "--username",
        action="store",
        default=None,
        help="Username for authenticated integration tests",
    )
    parser.addoption(
        "--password",
        action="store",
        default=None,
        help="Password for authenticated integration tests",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers",
        "integration: integration test requiring live services",
    )


# ============================================================================
# CLI JSON PARSING HELPERS
# ============================================================================


def parse_cli_json(result: Result, sdk_model: Type[T]) -> T:
    """Parse CLI JSON output using SDK Pydantic model.

    Args:
        result: Click test result from CLI invocation
        sdk_model: SDK Pydantic model class (e.g., EntityListResult, JobResponse)

    Returns:
        Validated SDK model instance

    Raises:
        AssertionError: If CLI failed or JSON is invalid

    Example:
        result = cli_runner.invoke(cli, ["--json", "store", "list"])
        data = parse_cli_json(result, EntityListResult)
        assert data.pagination.page == 1
    """
    assert result.exit_code == 0, f"CLI failed with exit code {result.exit_code}: {result.output}"

    try:
        data = json.loads(result.output)
        return sdk_model(**data)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Invalid JSON from CLI: {e}\nOutput: {result.output}")
    except Exception as e:
        raise AssertionError(f"JSON validation failed: {e}\nOutput: {result.output}")


def parse_cli_json_list(result: Result, item_model: Type[T]) -> list[T]:
    """Parse CLI JSON output as list of SDK models.

    Args:
        result: Click test result from CLI invocation
        item_model: SDK Pydantic model class for list items

    Returns:
        List of validated SDK model instances

    Example:
        result = cli_runner.invoke(cli, ["--json", "faces", "list", "123"])
        faces = parse_cli_json_list(result, Face)
        assert len(faces) > 0
    """
    assert result.exit_code == 0, f"CLI failed with exit code {result.exit_code}: {result.output}"

    try:
        data = json.loads(result.output)
        if not isinstance(data, list):
            raise AssertionError(f"Expected list, got {type(data)}")
        return [item_model(**item) for item in data]
    except json.JSONDecodeError as e:
        raise AssertionError(f"Invalid JSON from CLI: {e}\nOutput: {result.output}")
    except Exception as e:
        raise AssertionError(f"JSON validation failed: {e}\nOutput: {result.output}")


def assert_cli_success(result: Result, expected_message: str | None = None) -> dict:
    """Assert CLI returned success response.

    Args:
        result: Click test result
        expected_message: Optional substring to check in success message

    Returns:
        Parsed JSON dict

    Example:
        result = cli_runner.invoke(cli, ["--json", "store", "delete", "123", "--yes"])
        assert_cli_success(result, "Deleted entity")
    """
    assert result.exit_code == 0, f"CLI should have succeeded: {result.output}"

    try:
        data = json.loads(result.output)
        assert "status" in data, f"Missing status in output: {result.output}"
        assert data["status"] == "success", f"Expected success status: {result.output}"

        if expected_message:
            assert "message" in data, f"Missing message in output: {result.output}"
            assert expected_message in data["message"], \
                f"Expected '{expected_message}' in message: {data['message']}"

        return data
    except json.JSONDecodeError as e:
        raise AssertionError(f"Invalid JSON from CLI: {e}\nOutput: {result.output}")


def assert_cli_error(result: Result, error_substring: str | None = None) -> dict:
    """Assert CLI returned error response.

    Args:
        result: Click test result
        error_substring: Optional substring to check in error message

    Returns:
        Parsed JSON dict

    Example:
        result = cli_runner.invoke(cli, ["--json", "store", "get", "99999"])
        assert_cli_error(result, "not found")
    """
    assert result.exit_code != 0, f"CLI should have failed: {result.output}"

    try:
        data = json.loads(result.output)
        assert "error" in data, f"Missing error in output: {result.output}"
        assert "status" in data, f"Missing status in output: {result.output}"
        assert data["status"] == "failed", f"Expected failed status: {result.output}"

        if error_substring:
            assert error_substring.lower() in data["error"].lower(), \
                f"Expected '{error_substring}' in error: {data['error']}"

        return data
    except json.JSONDecodeError as e:
        raise AssertionError(f"Invalid JSON from CLI: {e}\nOutput: {result.output}")


# ============================================================================
# SESSION FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def auth_url(request: pytest.FixtureRequest) -> str:
    """Get auth service URL from CLI args."""
    url = request.config.getoption("--auth-url")
    if not url:
        pytest.skip("Integration tests require --auth-url")
    return str(url)


@pytest.fixture(scope="session")
def compute_url(request: pytest.FixtureRequest) -> str:
    """Get compute service URL from CLI args."""
    url = request.config.getoption("--compute-url")
    if not url:
        pytest.skip("Integration tests require --compute-url")
    return str(url)


@pytest.fixture(scope="session")
def store_url(request: pytest.FixtureRequest) -> str:
    """Get store service URL from CLI args."""
    url = request.config.getoption("--store-url")
    if not url:
        pytest.skip("Integration tests require --store-url")
    return str(url)


@pytest.fixture(scope="session")
def username(request: pytest.FixtureRequest) -> str:
    """Get username from CLI args."""
    user = request.config.getoption("--username")
    if not user:
        pytest.skip("Integration tests require --username")
    return str(user)


@pytest.fixture(scope="session")
def password(request: pytest.FixtureRequest) -> str:
    """Get password from CLI args."""
    pwd = request.config.getoption("--password")
    if not pwd:
        pytest.skip("Integration tests require --password")
    return str(pwd)


# ============================================================================
# TEST CLIENT FIXTURES
# ============================================================================


class SyncTestHelper:
    """Synchronous helper for setting up test data in integration tests.

    This helper runs async operations in a new event loop to avoid conflicts
    with the CLI's asyncio.run() calls.
    """

    def __init__(
        self,
        auth_url: str,
        compute_url: str,
        store_url: str,
        username: str,
        password: str,
    ):
        self.auth_url = auth_url
        self.compute_url = compute_url
        self.store_url = store_url
        self.username = username
        self.password = password

    def create_test_entity(self, label: str, image_path: Path):
        """Create a test entity synchronously."""

        async def _create():
            config = ServerConfig(
                auth_url=self.auth_url,
                compute_url=self.compute_url,
                store_url=self.store_url,
            )
            session = SessionManager(server_config=config)
            await session.login(self.username, self.password)

            manager = session.create_store_manager()
            await manager.__aenter__()

            result = await manager.create_entity(label=label, image_path=image_path)

            await manager.__aexit__(None, None, None)
            await session.close()

            return result.data.id if result.is_success and result.data else None

        return asyncio.run(_create())

    def wait_for_faces(self, entity_id: int, max_wait: int = 30):
        """Wait for face detection to complete and return first face_id.

        Uses pysdk's wait_for_job() to wait for job completion, then polls
        for results in the database.
        """

        async def _wait():
            config = ServerConfig(
                auth_url=self.auth_url,
                compute_url=self.compute_url,
                store_url=self.store_url,
            )
            session = SessionManager(server_config=config)
            await session.login(self.username, self.password)

            manager = session.create_store_manager()
            await manager.__aenter__()

            compute_client = session.create_compute_client()

            try:
                # Step 1: Poll to find the face detection job
                face_job = None
                for _ in range(10):  # Try for 10 seconds
                    await asyncio.sleep(1.0)
                    jobs = await manager.store_client.get_entity_jobs(entity_id)
                    face_detection_jobs = [
                        j for j in jobs if j.task_type == "face_detection"
                    ]
                    if face_detection_jobs:
                        face_job = face_detection_jobs[0]
                        break

                if face_job is None:
                    return None  # No job found

                # Step 2: Wait for job completion using pysdk's wait_for_job
                await compute_client.wait_for_job(
                    job_id=face_job.job_id,
                    timeout=30.0,
                )

                # Step 3: Poll for faces to appear in database
                face_id = None
                for _ in range(10):  # Try for 10 seconds
                    await asyncio.sleep(1.0)
                    faces = await manager.store_client.get_entity_faces(
                        entity_id=entity_id
                    )
                    if len(faces) > 0:
                        face_id = faces[0].id
                        break

                return face_id
            finally:
                await compute_client.close()
                await manager.__aexit__(None, None, None)
                await session.close()

        return asyncio.run(_wait())

    def wait_for_person(self, entity_id: int, max_wait: int = 60):
        """Wait for person creation and return person_id.

        Waits for face detection, then face embedding, then person creation.
        """

        async def _wait():
            config = ServerConfig(
                auth_url=self.auth_url,
                compute_url=self.compute_url,
                store_url=self.store_url,
            )
            session = SessionManager(server_config=config)
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
                    face_detection_jobs = [
                        j for j in jobs if j.task_type == "face_detection"
                    ]
                    if face_detection_jobs:
                        face_job = face_detection_jobs[0]
                        break

                if face_job is None:
                    return None

                await compute_client.wait_for_job(job_id=face_job.job_id, timeout=30.0)

                # Step 2: Wait for face embedding jobs
                for _ in range(20):  # Try for 40 seconds
                    await asyncio.sleep(2.0)
                    jobs = await manager.store_client.get_entity_jobs(entity_id)
                    face_embedding_jobs = [
                        j for j in jobs if j.task_type == "face_embedding"
                    ]

                    # Check if all embedding jobs are completed
                    if face_embedding_jobs and all(
                        j.status == "completed" for j in face_embedding_jobs
                    ):
                        break

                # Step 3: Poll for person_id to appear
                person_id = None
                for _ in range(10):  # Try for 10 seconds
                    await asyncio.sleep(1.0)
                    faces = await manager.store_client.get_entity_faces(
                        entity_id=entity_id
                    )
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
        """Wait for CLIP embedding to be generated.

        Returns True if embedding is ready, False otherwise.
        """

        async def _wait():
            config = ServerConfig(
                auth_url=self.auth_url,
                compute_url=self.compute_url,
                store_url=self.store_url,
            )
            session = SessionManager(server_config=config)
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
    auth_url: str, compute_url: str, store_url: str, username: str, password: str
) -> SyncTestHelper:
    """Synchronous test helper for integration tests."""
    return SyncTestHelper(auth_url, compute_url, store_url, username, password)


# ============================================================================
# CLI RUNNER FIXTURES
# ============================================================================


@pytest.fixture
def cli_runner():
    """Create CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def cli_env(
    auth_url: str, compute_url: str, store_url: str, username: str, password: str
):
    """Environment variables for CLI commands."""
    return {
        "CL_AUTH_URL": auth_url,
        "CL_COMPUTE_URL": compute_url,
        "CL_STORE_URL": store_url,
        "CL_USERNAME": username,
        "CL_PASSWORD": password,
    }


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================


# Test media directory
TEST_MEDIA_DIR = Path(
    os.getenv("TEST_VECTORS_DIR", "/Users/anandasarangaram/Work/cl_server_test_media")
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

                    # Fetch entities
                    resp = await client.get(
                        f"{store_url}/entities?page=1&page_size=1000",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=5.0,
                    )

                    if resp.status_code != 200:
                        return

                    entities = resp.json().get("items", [])

                    # Delete all test entities
                    for entity in entities:
                        if entity.get("label", "").startswith("test_"):
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
