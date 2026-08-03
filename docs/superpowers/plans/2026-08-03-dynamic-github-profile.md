# Dynamic GitHub Profile Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and deploy a privacy-preserving GitHub profile generator that accounts for every repository accessible to the authenticated account across owner, collaborator, and organization-member affiliations and renders a light/dark SVG identity card.

**Architecture:** A dependency-free Python package inventories repositories through one or more authenticated GitHub REST clients, merges and deduplicates all visible repositories, collects yearly commit-contribution totals through the primary token, validates aggregate completeness, renders XML-safe SVG assets, and atomically replaces public aggregate outputs. A GitHub Actions workflow runs tests, generates assets, validates them, and commits only changed generated files.

**Tech Stack:** Python 3.13 standard library, GitHub REST API, GitHub GraphQL API, SVG/XML, GitHub Actions, `unittest`.

## Global Constraints

- Never commit, print, serialize, or accept any account token as a CLI argument.
- Count all repositories returned by every supplied token for `owner`, `collaborator`, and `organization_member` with `visibility=all`.
- Deduplicate repositories by immutable numeric repository ID.
- Publish aggregate statistics only; never publish repository or private organization identifiers.
- Preserve the Lucifer Rodstark, Ph.D. persona and omit legal identity and personal contact fields.
- Do not traverse repository commit histories or publish additions-minus-deletions as LOC.
- Abort before replacing existing generated assets whenever collection or validation is incomplete.
- Use current Node 24-compatible official GitHub Actions majors and Python 3.13.

---

### Task 1: Domain Models and Aggregate Invariants

**Files:**
- Create: `tests/test_models.py`
- Create: `profile_generator/models.py`
- Create: `profile_generator/__init__.py`

**Interfaces:**
- Produces: `InventoryStats.validate() -> None`, `ProfileStats.to_public_dict() -> dict[str, object]`.

- [ ] **Step 1: Write failing model tests** for valid totals, visibility mismatches, affiliation mismatches, and JSON-safe public serialization with no repository identifiers.
- [ ] **Step 2: Run** `python -m unittest tests.test_models -v` and verify import/implementation failure.
- [ ] **Step 3: Implement immutable dataclasses** with explicit fields and invariant validation.
- [ ] **Step 4: Re-run the model tests** and verify PASS.
- [ ] **Step 5: Commit** `test: define profile aggregate invariants`.

### Task 2: Authenticated GitHub API Client

**Files:**
- Create: `tests/test_api.py`
- Create: `profile_generator/api.py`

**Interfaces:**
- Produces: `GitHubClient.get_authenticated_user()`, `GitHubClient.list_repositories(affiliation)`, `GitHubClient.commit_contributions(from_iso, to_iso)`.

- [ ] **Step 1: Write failing tests** for page traversal, 5xx retry, 401/403 redaction, and GraphQL `errors` returned with HTTP 200.
- [ ] **Step 2: Run** `python -m unittest tests.test_api -v` and verify the client is missing.
- [ ] **Step 3: Implement** an injected transport abstraction plus the production `urllib.request` transport, bounded retry, JSON parsing, and page iteration using `per_page=100&page=N` until the returned page is shorter than 100.
- [ ] **Step 4: Re-run tests** and verify PASS without network access.
- [ ] **Step 5: Commit** `feat: add resilient authenticated GitHub client`.

### Task 3: Repository Inventory and Contribution Collection

**Files:**
- Create: `tests/test_collector.py`
- Create: `profile_generator/collector.py`

**Interfaces:**
- Consumes: API client methods from Task 2 and models from Task 1.
- Produces: `collect_profile_stats(clients, expected_login, required_owners, now) -> ProfileStats`, `year_windows(created_at, now) -> list[tuple[str, str]]`.

- [ ] **Step 1: Write failing tests** for duplicate repository IDs across affiliations and tokens, token-login mismatch, account-metadata mismatch, affiliation precedence, visibility/state counts, organization-owner count, owned-star sum, repository-size sum, required-owner failure, and leap-year-safe annual windows.
- [ ] **Step 2: Run** `python -m unittest tests.test_collector -v` and verify failure because the collector is absent.
- [ ] **Step 3: Implement** three affiliation queries per client, cross-token ID-based merging, aggregate-only normalization, required-owner validation, primary-token yearly GraphQL collection, and invariant validation.
- [ ] **Step 4: Re-run tests** and verify PASS.
- [ ] **Step 5: Commit** `feat: collect complete aggregate repository inventory`.

### Task 4: SVG Renderer and Portrait ASCII

**Files:**
- Create: `tests/test_render.py`
- Create: `profile_generator/render.py`

**Interfaces:**
- Consumes: `ProfileStats`.
- Produces: `render_svg(stats, theme) -> str`, `render_all(stats) -> dict[str, str]`.

- [ ] **Step 1: Write failing tests** that parse both themes as XML, assert stable element IDs, confirm escaping of `&`, `<`, and `>`, confirm the original image path/name is absent, and confirm private repository names cannot enter output through the public model.
- [ ] **Step 2: Run** `python -m unittest tests.test_render -v` and verify failure.
- [ ] **Step 3: Implement** a standard-SVG renderer with no script/foreignObject/external assets and embed the precomputed ASCII portrait as text spans.
- [ ] **Step 4: Re-run tests** and verify PASS.
- [ ] **Step 5: Commit** `feat: render Lucy identity card in light and dark SVG`.

### Task 5: Atomic CLI and Public Aggregate Output

**Files:**
- Create: `tests/test_cli.py`
- Create: `profile_generator/cli.py`
- Create: `profile_generator/__main__.py`
- Create: `generated/profile-stats.json`
- Create: `assets/profile-dark.svg`
- Create: `assets/profile-light.svg`

**Interfaces:**
- Consumes: collector and renderer.
- Produces: `python -m profile_generator` command.

- [ ] **Step 1: Write failing tests** for missing-secret rejection, single-token configuration, newline-separated multi-token normalization/deduplication, fail-before-write behavior, atomic replacement, and deterministic aggregate JSON formatting.
- [ ] **Step 2: Run** `python -m unittest tests.test_cli -v` and verify failure.
- [ ] **Step 3: Implement** environment-only single/multi-token configuration, one API client per token, collection-before-write orchestration, temporary-file XML validation, `os.replace`, and aggregate-only console output.
- [ ] **Step 4: Add a bootstrap aggregate** whose coverage state is `PENDING_AUTHENTICATED_SYNC`; render the initial SVG assets from it without claiming authenticated completeness.
- [ ] **Step 5: Run** `python -m unittest discover -s tests -v` and verify all tests PASS.
- [ ] **Step 6: Commit** `feat: add atomic profile generation command`.

### Task 6: README, Documentation, and Security Guidance

**Files:**
- Modify: `README.md`
- Create: `docs/profile-generator.md`
- Create: `SECURITY.md`
- Create: `.gitignore`

**Interfaces:**
- Consumes: generated SVG asset paths and secret names from Task 5.

- [ ] **Step 1: Replace the static banner** with a `<picture>` element selecting `assets/profile-dark.svg` and `assets/profile-light.svg`.
- [ ] **Step 2: Consolidate repetitive profile prose** into identity, systems, stack, operating model, and organizations while retaining the project persona.
- [ ] **Step 3: Document broad-token and one-token-per-resource-owner models, SSO/organization authorization, the `PROFILE_STATS_TOKEN` and `PROFILE_STATS_TOKENS` environment contract, exact Actions secret names, manual run procedure, aggregate semantics, and troubleshooting without including any token value.
- [ ] **Step 4: Add credential-incident guidance** instructing immediate revocation of any token exposed in chat, logs, issues, commits, or workflow YAML.
- [ ] **Step 5: Validate README asset paths** and commit `docs: integrate dynamic profile card and secure setup guide`.

### Task 7: GitHub Actions Automation

**Files:**
- Create: `.github/workflows/profile-stats.yml`

**Interfaces:**
- Executes: `python -m unittest discover -s tests -v`, `python -m profile_generator`.

- [ ] **Step 1: Add manual and daily triggers**, concurrency control, a 15-minute timeout, and `contents: write` permission.
- [ ] **Step 2: Use** `actions/checkout@v6` and `actions/setup-python@v6` with Python `3.13`.
- [ ] **Step 3: Run tests before generation**, preserve bootstrap assets when no primary secret exists, then generate with a newline-separated `PROFILE_STATS_TOKENS` value assembled from the primary and per-resource-owner encrypted secrets, plus `PROFILE_LOGIN` and required-owner configuration.
- [ ] **Step 4: Validate** XML parsing, aggregate JSON coverage, `git diff --check`, privacy contracts, and that no token-pattern value exists in tracked files.
- [ ] **Step 5: Commit only** `assets/profile-dark.svg`, `assets/profile-light.svg`, and `generated/profile-stats.json` when changed, using `github-actions[bot]`.
- [ ] **Step 6: Commit** `ci: automate authenticated profile regeneration`.

### Task 8: Full Verification and Pull Request

**Files:**
- Verify all files above.

**Interfaces:**
- Produces: reviewable pull request into `production`.

- [ ] **Step 1: Run** `python -m unittest discover -s tests -v` and require zero failures/errors.
- [ ] **Step 2: Run** `python -m compileall -q profile_generator tests`.
- [ ] **Step 3: Parse both SVG files** with `xml.etree.ElementTree`.
- [ ] **Step 4: Search tracked project files** for the exposed token prefix, generic PAT patterns, legal-name/contact strings, private repository names, and source portrait filename; require no matches outside explicit redacted documentation examples.
- [ ] **Step 5: Inspect the complete diff** for privacy, workflow permissions, and generated-output semantics.
- [ ] **Step 6: Open a pull request** targeting `production`, review its patch, and merge only when all local verification passes and the branch contains no credentials.
