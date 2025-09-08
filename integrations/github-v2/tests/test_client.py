import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

from integrations.github_v2.client import GitHubClient
from integrations.github_v2.exceptions import (
    GitHubRateLimitError,
    GitHubNotModified,
)


@pytest_asyncio.fixture
async def client():
    return GitHubClient(token="fake-token")


@pytest.mark.asyncio
async def test_list_repositories_success(client):
    """
    GIVEN a GitHub client
    WHEN list_repositories is called
    THEN it should return repositories from the API
    """
    fake_repos = [{"id": 1, "name": "repo1"}, {"id": 2, "name": "repo2"}]

    with patch.object(client, "_request", AsyncMock(return_value=fake_repos)):
        repos = await client.list_repositories("my-org")
        assert repos == fake_repos


@pytest.mark.asyncio
async def test_rate_limit_raises_error(client):
    """
    GIVEN GitHub responds with a rate limit error
    WHEN a request is made
    THEN GitHubRateLimitError should be raised
    """
    with patch.object(
        client,
        "_request",
        AsyncMock(side_effect=GitHubRateLimitError("Rate limit exceeded", 10)),
    ):
        with pytest.raises(GitHubRateLimitError) as exc_info:
            await client.list_repositories("my-org")
        assert "Rate limit" in str(exc_info.value)


@pytest.mark.asyncio
async def test_not_modified_is_handled(client):
    """
    GIVEN GitHub responds with 304 Not Modified
    WHEN a file is fetched
    THEN GitHubNotModified should be raised
    """
    with patch.object(
        client, "_request", AsyncMock(side_effect=GitHubNotModified("Not modified"))
    ):
        with pytest.raises(GitHubNotModified):
            await client.fetch_file("me", "repo", "README.md")


@pytest.mark.asyncio
async def test_list_pull_requests_success(client):
    """
    GIVEN a GitHub client
    WHEN list_pull_requests is called with a repo
    THEN it should return pull requests
    """
    fake_prs = [{"id": 101, "title": "Fix bug"}]

    with patch.object(client, "_request", AsyncMock(return_value=fake_prs)):
        prs = await client.list_pull_requests("me", "repo")
        assert prs == fake_prs


@pytest.mark.asyncio
async def test_list_issues_success(client):
    """
    GIVEN a GitHub client
    WHEN list_issues is called
    THEN it should return issues
    """
    fake_issues = [{"id": 201, "title": "Issue 1"}]

    with patch.object(client, "_request", AsyncMock(return_value=fake_issues)):
        issues = await client.list_issues("me", "repo")
        assert issues == fake_issues
