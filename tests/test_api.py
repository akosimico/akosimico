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


def response(status, payload=None, headers=None):
    if payload is None:
        body = b""
    else:
        body = json.dumps(payload).encode("utf-8")
    return HttpResponse(status=status, headers=headers or {}, body=body)


class GitHubClientTests(unittest.TestCase):
    def client(self, responses, **overrides):
        transport = SequenceTransport(responses)
        client = GitHubClient(
            token="not-a-real-token",
            transport=transport,
            rest_base_url="https://api.test",
            graphql_url="https://graphql.test",
            max_attempts=overrides.pop("max_attempts", 1),
            stats_max_attempts=overrides.pop("stats_max_attempts", 3),
            sleep=overrides.pop("sleep", lambda _: None),
            **overrides,
        )
        return client, transport

    def test_repository_listing_traverses_every_page(self):
        first_page = [{"id": index} for index in range(100)]
        second_page = [{"id": 100}, {"id": 101}]
        client, transport = self.client([response(200, first_page), response(200, second_page)])

        repositories = client.list_repositories("owner")

        self.assertEqual(len(repositories), 102)
        self.assertIn("affiliation=owner", transport.calls[0][1])
        self.assertIn("page=2", transport.calls[1][1])

    def test_transient_server_error_is_retried(self):
        sleeps = []
        client, transport = self.client(
            [response(502, {"message": "temporary"}), response(200, {"login": "itsmfknlucy"})],
            max_attempts=2,
            sleep=sleeps.append,
        )

        user = client.get_authenticated_user()

        self.assertEqual(user["login"], "itsmfknlucy")
        self.assertEqual(len(transport.calls), 2)
        self.assertEqual(sleeps, [1.0])

    def test_repository_activity_counts_commits_and_authored_lines(self):
        link = '<https://api.test/repos/Org/Repo/commits?per_page=1&page=123>; rel="last"'
        contributors = [
            {
                "author": {"login": "itsmfknlucy"},
                "total": 120,
                "weeks": [
                    {"w": 1, "a": 1000, "d": 250, "c": 2},
                    {"w": 2, "a": 500, "d": 100, "c": 1},
                ],
            }
        ]
        client, transport = self.client([
            response(200, [{"sha": "abc"}], headers={"Link": link}),
            response(200, contributors),
        ])

        commits, additions, deletions = client.repository_activity("Org/Repo", "itsmfknlucy")

        self.assertEqual((commits, additions, deletions), (123, 1500, 350))
        self.assertIn("/repos/Org/Repo/commits?", transport.calls[0][1])
        self.assertNotIn("author=", transport.calls[0][1])
        self.assertTrue(transport.calls[1][1].endswith("/repos/Org/Repo/stats/contributors"))

    def test_repository_activity_polls_accepted_contributor_statistics(self):
        sleeps = []
        client, _ = self.client(
            [
                response(200, [{"sha": "abc"}]),
                response(202, {"message": "processing"}),
                response(200, [{"author": {"login": "itsmfknlucy"}, "total": 1, "weeks": []}]),
            ],
            stats_max_attempts=2,
            sleep=sleeps.append,
        )

        self.assertEqual(client.repository_activity("Org/Repo", "itsmfknlucy"), (1, 0, 0))
        self.assertEqual(sleeps, [1.0])

    def test_empty_repository_has_zero_activity(self):
        client, _ = self.client([response(409, {"message": "empty"}), response(204)])
        self.assertEqual(client.repository_activity("Org/Empty", "itsmfknlucy"), (0, 0, 0))

    def test_missing_contributor_statistics_produce_zero_authored_lines(self):
        client, _ = self.client([
            response(200, [{"sha": "abc"}]),
            response(200, [{"author": {"login": "someone-else"}, "total": 1, "weeks": []}]),
        ])
        self.assertEqual(client.repository_activity("Org/Repo", "itsmfknlucy"), (1, 0, 0))

    def test_contribution_counts_include_visible_and_restricted_activity(self):
        collection = {
            "totalCommitContributions": 100,
            "totalIssueContributions": 3,
            "totalPullRequestContributions": 4,
            "totalPullRequestReviewContributions": 5,
            "totalRepositoryContributions": 2,
            "restrictedContributionsCount": 50,
        }
        client, transport = self.client([
            response(200, {"data": {"viewer": {"contributionsCollection": collection}}}),
        ])

        self.assertEqual(
            client.contribution_counts("2026-01-01T00:00:00Z", "2026-12-31T23:59:59Z"),
            (114, 50),
        )
        request = json.loads(transport.calls[0][3].decode("utf-8"))
        self.assertIn("totalPullRequestReviewContributions", request["query"])

    def test_authentication_error_does_not_echo_response_body(self):
        client, _ = self.client([
            response(401, {"message": "token rejected for private/repository-name"}),
        ])

        with self.assertRaises(ApiError) as raised:
            client.get_authenticated_user()

        message = str(raised.exception)
        self.assertIn("401", message)
        self.assertNotIn("private/repository-name", message)
        self.assertNotIn("not-a-real-token", message)

    def test_graphql_errors_fail_even_with_http_200(self):
        client, _ = self.client([
            response(200, {"errors": [{"message": "private/repository-name"}]}),
        ])

        with self.assertRaisesRegex(ApiError, "GraphQL") as raised:
            client.contribution_counts("2026-01-01T00:00:00Z", "2026-08-03T00:00:00Z")

        self.assertNotIn("private/repository-name", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
