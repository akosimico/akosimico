# Security

## Credential Handling

GitHub access tokens are secrets. They must never be committed, pasted into issues or pull requests, placed in workflow YAML, printed by scripts, or accepted as ordinary workflow inputs.

The profile generator reads credentials only from encrypted GitHub Actions secrets exposed as `PROFILE_STATS_TOKEN` or `PROFILE_STATS_TOKENS`. Token values are excluded from dataclass representations, generated JSON, SVG output, and normal logs.

## Exposed Token Response

Treat any token exposed in chat, screenshots, shell history, logs, commits, or other plaintext as compromised:

1. Revoke it immediately in GitHub settings.
2. Create a replacement with the least read-only access required.
3. Authorize the replacement for each required organization or SSO boundary.
4. Replace the affected Actions secret.
5. Review account and organization audit activity for unexpected use.
6. Re-run the profile workflow and verify required-owner coverage.

Deleting the visible message or commit is not sufficient; revocation is required.

## Generated Data Boundary

Only aggregate account statistics are public. Repository names, owner names, repository IDs, URLs, descriptions, branches, commit messages, language data, and per-repository metrics must not be written to generated assets or caches.

A collection or validation failure must preserve the previous verified output rather than publish partial totals.
