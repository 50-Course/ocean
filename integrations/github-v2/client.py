from port_ocean.utils import http_async_client
from .exceptions import GitHubNotModified, GitHubRateLimitError
from typing import Literal, Optional, Any
import logging
from .utils import retry_with_backoff, paginate

logger = logging.getLogger(__name__)


class GitHubClient:
    BASE_URL = "https://api.github.com"

    def __init__(
        self,
        token: str,
        headers: Optional[dict] = None,
        max_retries: int = 3,
    ) -> None:
        self._token = token
        self._client = http_async_client
        self._headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github.v3+json",
            **(headers or {}),
        }
        self._etag_cache = {}

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
        cache_key: Optional[str] = None,
    ) -> dict:
        url = f"{self.BASE_URL}{endpoint}"
        headers = dict(self._headers)

        if cache_key and cache_key in self._etag_cache:
            headers["If-None-Match"] = self._etag_cache[cache_key]

        response = await self._client.request(
            method=method,
            url=url,
            headers=headers,
            params=params or {},
            json=json_data,
        )

        if (
            response.status_code == 403
            and response.headers.get("X-RateLimit-Remaining") == "0"
        ):
            logger.warning("GitHub API rate limit exceeded")

            reset_ts = int(response.headers.get("X-RateLimit-Reset", 0))
            raise GitHubRateLimitError("GitHub API rate limit exceeded", reset_ts)

        if response.status_code == 304:
            raise GitHubNotModified("Resource not modified")

        response.raise_for_status()

        if cache_key and (etag := response.headers.get("ETag")):
            self._etag_cache[cache_key] = etag

        return await response.json()

    async def list_repositories(self, org: str) -> list[dict[str, Any]]:
        """Fetch repositories for an organization."""

        async def fetch_page(per_page: int, page: int):
            return await retry_with_backoff(
                self._request,
                "GET",
                f"/orgs/{org}/repos",
                params={"per_page": per_page, "page": page},
                cache_key=f"repos:{org}:{page}",
            )

        return [repo async for repo in paginate(fetch_page)]

    async def list_pull_requests(
        self, owner: str, repo: str, state: Literal["open", "closed"] = "open"
    ) -> list[dict[str, Any]]:
        """Fetch pull requests with optional filtering."""

        async def fetch_page(per_page: int, page: int):
            return await retry_with_backoff(
                self._request,
                "GET",
                f"/repos/{owner}/{repo}/pulls",
                params={"state": state, "per_page": per_page, "page": page},
                cache_key=f"prs:{owner}/{repo}:{state}:{page}",
            )

        return [pr async for pr in paginate(fetch_page)]

    async def list_issues(
        self, owner: str, repo: str, state: Literal["open", "closed", "all"] = "open"
    ) -> list[dict[str, Any]]:
        """Fetch issues for a repo (open/closed/all)."""

        async def fetch_page(per_page: int, page: int):
            params = {"state": state, "per_page": per_page, "page": page}
            return await retry_with_backoff(
                self._request,
                "GET",
                f"/repos/{owner}/{repo}/issues",
                params=params,
                cache_key=f"issues:{owner}/{repo}:{state}:{page}",
            )

        return [issue async for issue in paginate(fetch_page)]

    async def fetch_file(
        self, owner: str, repo: str, path: str, ref: str = "main"
    ) -> dict[str, Any]:
        """Fetch a single file (YAML, JSON, MD, etc.) from a repo branch."""
        params = {"ref": ref}
        return await retry_with_backoff(
            self._request,
            "GET",
            f"/repos/{owner}/{repo}/contents/{path}",
            params=params,
            cache_key=f"file:{owner}/{repo}:{path}:{ref}",
        )
