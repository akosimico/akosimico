"""Minimal resilient GitHub REST and GraphQL client."""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping


class ApiError(RuntimeError):
    """Raised when GitHub data cannot be collected safely and completely."""


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes


Transport = Callable[[str, str, Mapping[str, str], bytes | None, float], HttpResponse]


def urllib_transport(
    method: str,
    url: str,
    headers: Mapping[str, str],
    body: bytes | None,
    timeout: float,
) -> HttpResponse:
    """Execute one HTTP request while normalizing HTTP error responses."""

    request = urllib.request.Request(url=url, data=body, headers=dict(headers), method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed GitHub endpoints
            return HttpResponse(
                status=int(response.status),
                headers=dict(response.headers.items()),
                body=response.read(),
            )
    except urllib.error.HTTPError as exc:
        return HttpResponse(
            status=int(exc.code),
            headers=dict(exc.headers.items()) if exc.headers else {},
            body=exc.read(),
        )
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ApiError("GitHub API transport failed") from exc


class GitHubClient:
    """Authenticated GitHub API client with aggregate-safe error messages."""

    _AFFILIATIONS = {"owner", "collaborator", "organization_member"}
    _TRANSIENT_STATUSES = {429, 500, 502, 503, 504}
    _LAST_PAGE = re.compile(r"[?&]page=(\d+)[^>]*>;\s*rel=\"last\"")

    def __init__(
        self,
        token: str,
        *,
        transport: Transport = urllib_transport,
        rest_base_url: str = "https://api.github.com",
        graphql_url: str = "https://api.github.com/graphql",
        timeout: float = 20.0,
        max_attempts: int = 3,
        stats_max_attempts: int = 5,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not token or not token.strip():
            raise ValueError("token must not be empty")
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if stats_max_attempts < 1:
            raise ValueError("stats_max_attempts must be at least 1")
        self._token = token.strip()
        self._transport = transport
        self._rest_base_url = rest_base_url.rstrip("/")
        self._graphql_url = graphql_url
        self._timeout = timeout
        self._max_attempts = max_attempts
        self._stats_max_attempts = stats_max_attempts
        self._sleep = sleep

    def get_authenticated_user(self) -> dict[str, Any]:
        payload = self._request_json(
            "GET",
            f"{self._rest_base_url}/user",
            operation="authenticated user lookup",
        )
        if not isinstance(payload, dict):
            raise ApiError("authenticated user lookup returned an invalid payload")
        return payload

    def list_repositories(self, affiliation: str) -> list[dict[str, Any]]:
        if affiliation not in self._AFFILIATIONS:
            raise ValueError(f"unsupported repository affiliation: {affiliation}")

        repositories: list[dict[str, Any]] = []
        page = 1
        while True:
            query = urllib.parse.urlencode(
                {
                    "affiliation": affiliation,
                    "direction": "asc",
                    "page": page,
                    "per_page": 100,
                    "sort": "full_name",
                    "visibility": "all",
                }
            )
            payload = self._request_json(
                "GET",
                f"{self._rest_base_url}/user/repos?{query}",
                operation=f"repository inventory ({affiliation})",
            )
            if not isinstance(payload, list) or any(not isinstance(item, dict) for item in payload):
                raise ApiError(f"repository inventory ({affiliation}) returned an invalid payload")
            repositories.extend(payload)
            if len(payload) < 100:
                break
            page += 1
        return repositories

    def contribution_counts(self, from_iso: str, to_iso: str) -> tuple[int, int]:
        """Return visible and restricted contribution counts for one time window."""

        query = """
        query ProfileContributions($from: DateTime!, $to: DateTime!) {
          viewer {
            contributionsCollection(from: $from, to: $to) {
              totalCommitContributions
              totalIssueContributions
              totalPullRequestContributions
              totalPullRequestReviewContributions
              totalRepositoryContributions
              restrictedContributionsCount
            }
          }
        }
        """
        payload = self._request_json(
            "POST",
            self._graphql_url,
            payload={"query": query, "variables": {"from": from_iso, "to": to_iso}},
            operation="GraphQL contribution lookup",
        )
        if not isinstance(payload, dict):
            raise ApiError("GraphQL contribution lookup returned an invalid payload")
        if payload.get("errors"):
            raise ApiError("GraphQL contribution lookup returned errors")
        try:
            collection = payload["data"]["viewer"]["contributionsCollection"]
        except (KeyError, TypeError) as exc:
            raise ApiError("GraphQL contribution lookup returned an invalid payload") from exc
        if not isinstance(collection, dict):
            raise ApiError("GraphQL contribution lookup returned an invalid payload")

        visible = sum(
            self._non_negative_int(collection.get(field), f"GraphQL {field}")
            for field in (
                "totalCommitContributions",
                "totalIssueContributions",
                "totalPullRequestContributions",
                "totalPullRequestReviewContributions",
                "totalRepositoryContributions",
            )
        )
        restricted = self._non_negative_int(
            collection.get("restrictedContributionsCount"),
            "GraphQL restrictedContributionsCount",
        )
        return visible, restricted

    def repository_activity(self, full_name: str, login: str) -> tuple[int, int, int]:
        """Return all default-branch commits plus this user's authored line changes."""

        repository_path = self._repository_path(full_name)
        author = login.strip()
        if not author:
            raise ValueError("login must not be empty")

        commit_count = self._repository_commit_count(repository_path)
        additions, deletions = self._repository_authored_lines(repository_path, author)
        return commit_count, additions, deletions

    def _repository_commit_count(self, repository_path: str) -> int:
        query = urllib.parse.urlencode({"per_page": 1})
        response = self._request_response(
            "GET",
            f"{self._rest_base_url}/repos/{repository_path}/commits?{query}",
            operation="repository commit count",
            accepted_statuses={200, 409},
        )
        if response.status == 409:
            return 0
        payload = self._decode_json(response, "repository commit count")
        if not isinstance(payload, list) or any(not isinstance(item, dict) for item in payload):
            raise ApiError("repository commit count returned an invalid payload")
        if not payload:
            return 0
        link = self._header(response.headers, "link")
        if not link:
            return len(payload)
        match = self._LAST_PAGE.search(link)
        if not match:
            return len(payload)
        return int(match.group(1))

    def _repository_authored_lines(
        self,
        repository_path: str,
        login: str,
    ) -> tuple[int, int]:
        url = f"{self._rest_base_url}/repos/{repository_path}/stats/contributors"
        response: HttpResponse | None = None
        for attempt in range(1, self._stats_max_attempts + 1):
            response = self._request_response(
                "GET",
                url,
                operation="repository contributor statistics",
                accepted_statuses={200, 202, 204, 409},
            )
            if response.status != 202:
                break
            if attempt < self._stats_max_attempts:
                self._sleep(float(2 ** (attempt - 1)))
        if response is None or response.status == 202:
            raise ApiError("repository contributor statistics remained unavailable")
        if response.status in {204, 409}:
            return 0, 0

        payload = self._decode_json(response, "repository contributor statistics")
        if not isinstance(payload, list) or any(not isinstance(item, dict) for item in payload):
            raise ApiError("repository contributor statistics returned an invalid payload")

        target = login.casefold()
        for contributor in payload:
            author = contributor.get("author")
            if not isinstance(author, dict):
                continue
            author_login = author.get("login")
            if not isinstance(author_login, str) or author_login.casefold() != target:
                continue
            weeks = contributor.get("weeks")
            if not isinstance(weeks, list) or any(not isinstance(week, dict) for week in weeks):
                raise ApiError("repository contributor statistics returned invalid weekly data")
            additions = sum(
                self._non_negative_int(week.get("a"), "repository additions") for week in weeks
            )
            deletions = sum(
                self._non_negative_int(week.get("d"), "repository deletions") for week in weeks
            )
            return additions, deletions

        return 0, 0

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        payload: Mapping[str, Any] | None = None,
        operation: str,
    ) -> Any:
        response = self._request_response(
            method,
            url,
            payload=payload,
            operation=operation,
        )
        return self._decode_json(response, operation)

    def _request_response(
        self,
        method: str,
        url: str,
        *,
        payload: Mapping[str, Any] | None = None,
        operation: str,
        accepted_statuses: set[int] | None = None,
    ) -> HttpResponse:
        body = None
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self._token}",
            "User-Agent": "lucy-profile-generator/2.0",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if payload is not None:
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"

        accepted = accepted_statuses
        last_status: int | None = None
        for attempt in range(1, self._max_attempts + 1):
            response = self._transport(method, url, headers, body, self._timeout)
            last_status = response.status
            success = response.status in accepted if accepted is not None else 200 <= response.status < 300
            if success:
                return response
            if self._is_transient(response) and attempt < self._max_attempts:
                self._sleep(self._retry_delay(response, attempt))
                continue
            raise ApiError(f"{operation} failed with HTTP {response.status}")
        raise ApiError(f"{operation} failed with HTTP {last_status or 'unknown'}")

    @staticmethod
    def _decode_json(response: HttpResponse, operation: str) -> Any:
        try:
            return json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ApiError(f"{operation} returned invalid JSON") from exc

    @classmethod
    def _is_transient(cls, response: HttpResponse) -> bool:
        if response.status in cls._TRANSIENT_STATUSES:
            return True
        if response.status != 403:
            return False
        headers = {str(key).lower(): str(value) for key, value in response.headers.items()}
        return "retry-after" in headers or headers.get("x-ratelimit-remaining") == "0"

    @staticmethod
    def _retry_delay(response: HttpResponse, attempt: int) -> float:
        headers = {str(key).lower(): str(value) for key, value in response.headers.items()}
        retry_after = headers.get("retry-after")
        if retry_after:
            try:
                return max(0.0, min(float(retry_after), 60.0))
            except ValueError:
                pass
        reset = headers.get("x-ratelimit-reset")
        if reset:
            try:
                remaining = float(reset) - time.time()
                return max(0.0, min(remaining, 60.0))
            except ValueError:
                pass
        return float(2 ** (attempt - 1))

    @staticmethod
    def _header(headers: Mapping[str, str], name: str) -> str:
        target = name.casefold()
        for key, value in headers.items():
            if str(key).casefold() == target:
                return str(value)
        return ""

    @staticmethod
    def _repository_path(full_name: str) -> str:
        parts = full_name.strip().split("/")
        if len(parts) != 2 or not all(parts):
            raise ValueError("repository full name must use owner/name format")
        return "/".join(urllib.parse.quote(part, safe="") for part in parts)

    @staticmethod
    def _non_negative_int(value: Any, label: str) -> int:
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ApiError(f"{label} must be a non-negative integer")
        return value
