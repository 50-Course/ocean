class GitHubClientError(Exception):
    """Base class for GitHub client errors."""


class GitHubRateLimitError(GitHubClientError):
    """Raised when GitHub API rate limits are exceeded."""

    def __init__(self, message: str, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class GitHubNotModified(GitHubClientError):
    """Raised when GitHub responds with 304 (no content changes)"""


class GitHubServerError(GitHubClientError):
    """Raised for 5xx errors returned by GitHub API"""


class GitHubNetworkError(GitHubClientError):
    """Raised for network-related errors (timeouts, connection issues)"""
