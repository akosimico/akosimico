import json
import unittest

from profile_generator.api import ApiError, GitHubClient, HttpResponse


class SequenceTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, method, url, headers, body, timeout):
        self.calls.append((method, url, headers, body, timeout))
        if not self.responses:
            raise AssertionError("unexpected transport call")
        return self.responses.pop(0)


def response(status, payload, headers=None):
    return HttpResponse(
        status=status,
        headers=headers or {},
        body=json.dumps(payload).encode("utf-8"),
    )


class GitHubClientTests(unittest.TestCase):
    def test_repository_listing_traverses_every_page(self):
        first_page = [{"id": index} for index in range(100)]
        second_page = [{"id": 100}, {"id": 101}]
        transport = SequenceTransport([
            response(200, first_page),
            response(200, second_page),
        ])
        client = GitHubClient(
            token="not-a-real-token",
            transport=transport,
            rest_base_url="https://api.test",
            max_attempts=1,
        )

        repositories = client.list_repositories("owner")

        self.assertEqual(len(repositories), 102)
        self.assertIn("affiliation=owner", transport.calls[0][1])
        self.assertIn("page=1", transport.calls[0][1])
        self.assertIn("page=2", transport.calls[1][1])

    def test_transient_server_error_is_retried(self):
        transport = SequenceTransport([
            response(502, {"message": "temporary"}),
            response(200, {"login": "itsmfknlucy"}),
        ])
        sleeps = []
        client = GitHubClient(
            token="not-a-real-token",
            transport=transport,
            rest_base_url="https://api.test",
            max_attempts=2,
            sleep=sleeps.append,
        )

        user = client.get_authenticated_user()

        self.assertEqual(user["login"], "itsmfknlucy")
        self.assertEqual(len(transport.calls), 2)
        self.assertEqual(sleeps, [1.0])


    def test_secondary_rate_limit_with_retry_after_is_retried(self):
        transport = SequenceTransport([
            response(403, {"message": "secondary rate limit"}, headers={"Retry-After": "0"}),
            response(200, {"login": "itsmfknlucy"}),
        ])
        sleeps = []
        client = GitHubClient(
            token="not-a-real-token",
            transport=transport,
            rest_base_url="https://api.test",
            max_attempts=2,
            sleep=sleeps.append,
        )

        user = client.get_authenticated_user()

        self.assertEqual(user["login"], "itsmfknlucy")
        self.assertEqual(len(transport.calls), 2)
        self.assertEqual(sleeps, [0.0])

    def test_authentication_error_does_not_echo_response_body(self):
        transport = SequenceTransport([
            response(401, {"message": "token rejected for private/repository-name"}),
        ])
        client = GitHubClient(
            token="not-a-real-token",
            transport=transport,
            rest_base_url="https://api.test",
            max_attempts=1,
        )

        with self.assertRaises(ApiError) as raised:
            client.get_authenticated_user()

        message = str(raised.exception)
        self.assertIn("401", message)
        self.assertNotIn("private/repository-name", message)
        self.assertNotIn("not-a-real-token", message)

    def test_graphql_errors_fail_even_with_http_200(self):
        transport = SequenceTransport([
            response(200, {"errors": [{"message": "private/repository-name"}]}),
        ])
        client = GitHubClient(
            token="not-a-real-token",
            transport=transport,
            graphql_url="https://graphql.test",
            max_attempts=1,
        )

        with self.assertRaisesRegex(ApiError, "GraphQL") as raised:
            client.commit_contributions(
                "2026-01-01T00:00:00Z",
                "2026-08-03T00:00:00Z",
            )

        self.assertNotIn("private/repository-name", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
