# Profile Generator

## Purpose

This repository implements an Andrew6rant-style generated profile card without copying the fragile all-history LOC scanner. It inventories every repository visible to the supplied account credentials, deduplicates repositories by immutable GitHub repository ID, produces aggregate-only telemetry, renders dark/light SVG assets, and commits changed generated files back to the `production` branch.

## What Is Counted

The collector requests all three authenticated repository affiliations with `visibility=all` and complete pagination:

- `owner`
- `collaborator`
- `organization_member`

A repository returned through more than one token or affiliation is counted once. The public output includes only aggregate totals for affiliation, visibility, state, accessible owners, GitHub-reported repository size, owned-repository stars, followers, and profile commit contributions.

The generated files never include repository names, numeric repository IDs, owner names, descriptions, URLs, branch names, commit messages, language distributions, or per-repository values.

## Credential Model

A fine-grained personal access token is restricted to the single **resource owner** selected when the token is created. Therefore, one fine-grained token for the personal account cannot also enumerate private repositories owned by several organizations.

The workflow supports either authentication model:

### One broad token

Set `PROFILE_STATS_TOKEN` to a personal access token that can read the personal account and every required organization. For a classic PAT, this normally means the least scopes necessary to read private repositories and organization membership, plus SSO authorization wherever required.

### Multiple fine-grained tokens

Create one read-only fine-grained token per resource owner. Store the personal-account token as the primary secret and provide organization tokens through either the named convenience secrets or one multiline bundle:

```text
PROFILE_STATS_TOKEN                  # primary personal-account token
PROFILE_STATS_TOKENS                 # optional multiline bundle of additional tokens
PROFILE_STATS_TOKEN_RODSTARK         # optional named organization token
PROFILE_STATS_TOKEN_NEXGEN_LAVA      # optional named organization token
PROFILE_STATS_TOKEN_FROSTBYTE        # optional named organization token
PROFILE_STATS_TOKEN_EXTERNAL_1       # optional external-owner token
PROFILE_STATS_TOKEN_EXTERNAL_2       # optional external-owner token
```

The first token is the **primary identity token**. Every supplied token must authenticate as `itsmfknlucy`. Repository inventories from all tokens are merged and deduplicated. The primary token is used for account-level follower and contribution signals; repository coverage is determined independently from the merged inventory and required-owner validation.

Fine-grained tokens need read access to repository metadata and must be configured for **All repositories** under their selected resource owner. A token limited to selected repositories cannot establish complete owner coverage. Organization approval or SSO authorization may also be required by organization policy.

GitHub does not expose a universal count of repositories hidden from a restricted token. Required-owner validation detects a completely missing owner, but it cannot detect omitted repositories within an owner that is only partially selected. Full-account accuracy therefore depends on using a broad token or selecting **All repositories** for every per-owner token.

## Required Owners

The workflow currently requires these resource owners to appear in the merged inventory:

```text
itsmfknlucy
Rodstark-Global-Solutions-Inc
NexGen-LAVA-Inc
FrostByte-Constructs-LLC
```

They are configured through `PROFILE_REQUIRED_OWNERS`. The workflow uses the encrypted `PROFILE_REQUIRED_OWNERS` secret first, then the `PROFILE_REQUIRED_OWNERS` repository variable, then its checked-in default. Add every additional organization or user owner whose repositories must be guaranteed. Missing-owner errors report only the number of absent owners, never their names, so private owner identities cannot leak through public Actions logs.

The authenticated installation audit performed on 2026-08-03 found **18 unique accessible repositories** across the four required resource owners. The workflow therefore sets `PROFILE_MIN_REPOSITORIES` to `18` by default. This second gate detects a token that can see every required owner but only a selected subset of repositories within one of them. Override the floor with the `PROFILE_MIN_REPOSITORIES` repository variable whenever the verified account inventory legitimately changes. A generated inventory below the floor fails before contribution queries and preserves the last verified SVG files.

Required-owner validation and the repository floor prevent expired, unapproved, SSO-blocked, completely missing, or partially selected credentials from silently publishing lower totals. They complement—but do not replace—the **All repositories** token setting.

## Secret Setup

1. Revoke any token that has appeared in chat, terminal output, screenshots, issues, commits, workflow YAML, or logs.
2. Create replacement read-only token(s) using one of the credential models above.
3. Open the profile repository's **Settings → Secrets and variables → Actions** page.
4. Set every fine-grained token's repository access to **All repositories** for its selected resource owner.
5. Add the appropriate repository secrets. Put the primary personal-account token first; use `PROFILE_STATS_TOKENS` for an unlimited newline-separated set of additional tokens when the named slots are insufficient.
6. In **Settings → Secrets and variables → Actions → Variables**, set `PROFILE_MIN_REPOSITORIES` to the latest independently verified unique repository count. The checked-in default is `18`.
7. Add `PROFILE_REQUIRED_OWNERS` as either an encrypted secret or repository variable when the required owner list differs from the checked-in default.
8. Open **Actions → Profile telemetry → Run workflow**.
9. Confirm the workflow completed and changed `assets/profile-dark.svg`, `assets/profile-light.svg`, and `generated/profile-stats.json`.

Never place a token in a tracked file or workflow input. The generator accepts credentials only through environment variables populated from encrypted repository secrets.

Until either `PROFILE_STATS_TOKEN` or `PROFILE_STATS_TOKENS` is installed, the workflow still runs its unit tests and compilation checks, then exits without touching the bootstrap SVG or JSON assets. Scheduled and post-merge runs therefore remain green while the repository is waiting for replacement credentials. Named organization-token secrets supplement the primary credential; they do not activate generation by themselves.

## Local Verification

Unit tests and compilation require no network access:

```bash
python -m unittest discover -s tests -v
python -m compileall -q profile_generator tests
```

Authenticated generation requires an environment secret:

```bash
export PROFILE_LOGIN="itsmfknlucy"
export PROFILE_REQUIRED_OWNERS="itsmfknlucy,Rodstark-Global-Solutions-Inc,NexGen-LAVA-Inc,FrostByte-Constructs-LLC"
export PROFILE_MIN_REPOSITORIES="18"
export PROFILE_STATS_TOKENS="<primary-token>\n<organization-token>"
python -m profile_generator
```

Do not place real tokens in shell history. Prefer an ephemeral secret manager or the GitHub Actions workflow.

## Failure Guarantees

The generator collects and validates all API data before opening output files. It fails without replacing published assets when:

- no token is configured;
- any token authenticates as the wrong user;
- any REST or GraphQL request fails;
- pagination returns malformed data;
- duplicate repository IDs contain conflicting owner metadata;
- a required resource owner is missing;
- the unique repository count is below `PROFILE_MIN_REPOSITORIES`;
- affiliation or visibility totals do not reconcile;
- generated SVG content is not valid XML.

Each destination file is written to a temporary file in the same directory and replaced atomically only after validation.

## Metric Semantics

- **Repositories** — unique repositories returned by all supplied credentials and affiliations.
- **Owned** — repositories returned through `owner`; this classification has highest precedence.
- **Organization member** — repositories returned through `organization_member` and not already classified as owned.
- **Collaborator** — repositories returned through `collaborator` and not classified above.
- **Visibility** — GitHub's `public`, `private`, or `internal` repository visibility.
- **Repo size** — the sum of GitHub's repository `size` field. It is not source-code LOC.
- **Contributions** — GitHub profile commit contributions visible to the primary identity token. This metric is not used to establish repository coverage.
- **Coverage: COMPLETE** — all configured token calls succeeded, aggregate invariants passed, every required resource owner was represented, and the repository count met the configured floor.

## Why LOC Is Not Published

Cumulative commit additions minus deletions is not the current number of source lines. Calculating it requires traversing every authored commit in every default branch, becomes impractical for very large histories, and can be dominated by generated or synthetic repositories. This project reports explicit GitHub repository size instead of relabeling commit churn as LOC.
