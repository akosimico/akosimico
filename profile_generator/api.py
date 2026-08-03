"""Minimal resilient GitHub REST and GraphQL client."""

from __future__ import annotations

import json
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

    def __init__(
        self,
        token: str,
        *,
        transport: Transport = urllib_transport,
        rest_base_url: str = "https://api.github.com",
        graphql_url: str = "https://api.github.com/graphql",
        timeout: float = 20.0,
        max_attempts: int = 3,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not token or not token.strip():
            raise ValueError("token must not be empty")
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self._token = token.strip()
        self._transport = transport
        self._rest_base_url = rest_base_url.rstrip("/")
        self._graphql_url = graphql_url
        self._timeout = timeout
        self._max_attempts = max_attempts
        self._sleep = sleep

    def get_authenticated_user(self) -> dict[str, Any]:
        payload = self._request_json("GET", f"{self._rest_base_url}/user", operation="authenticated user lookup")
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

    def commit_contributions(self, from_iso: str, to_iso: str) -> tuple[int, int]:
        query = """
        query ProfileCommitContributions($from: DateTime!, $to: DateTime!) {
          viewer {
            contributionsCollection(from: $from, to: $to) {
              totalCommitContributions
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
            total = collection["totalCommitContributions"]
            restricted = collection["restrictedContributionsCount"]
        except (KeyError, TypeError) as exc:
            raise ApiError("GraphQL contribution lookup returned an invalid payload") from exc
        if not isinstance(total, int) or isinstance(total, bool) or total < 0:
            raise ApiError("GraphQL contribution lookup returned an invalid commit count")
        if not isinstance(restricted, int) or isinstance(restricted, bool) or restricted < 0:
            raise ApiError("GraphQL contribution lookup returned an invalid restricted count")
        return total, restricted

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        payload: Mapping[str, Any] | None = None,
        operation: str,
    ) -> Any:
        body = None
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self._token}",
            "User-Agent": "lucy-profile-generator/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if payload is not None:
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"

        last_status: int | None = None
        for attempt in range(1, self._max_attempts + 1):
            response = self._transport(method, url, headers, body, self._timeout)
            last_status = response.status
            if 200 <= response.status < 300:
                try:
                    return json.loads(response.body.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise ApiError(f"{operation} returned invalid JSON") from exc

            if self._is_transient(response) and attempt < self._max_attempts:
                self._sleep(self._retry_delay(response, attempt))
                continue
            raise ApiError(f"{operation} failed with HTTP {response.status}")

        raise ApiError(f"{operation} failed with HTTP {last_status or 'unknown'}")

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
