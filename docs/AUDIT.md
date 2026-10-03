# Portfolio audit — October 2, 2026

## Provenance and scope
All 12 existing files were read. All five reachable commit trees were inventoried; their 11 unique blobs are identical to current content. The entire four-CSV dataset regenerates from seed 42 and matches every value. No client names, contact fields, tokens, or credentials were found in source or CSVs.

Source, fixtures, docs, and reachable existing history were reviewed for credentials, client information, and network destinations. Existing history was preserved. New content uses independent professional attribution.

## Validation
5 local tests passed. Demo artifacts use synthetic fixtures. No production integrations or deployments were exercised. GitHub Actions is configured with pinned action revisions and read-only contents permissions. MIT was retained for existing repositories and applied to the new toolkit under the user's request for a license decision.

## Administration and publication
Published publicly after the source, history, synthetic-data, and validation audit passed. Description and topics were applied through authenticated repository settings. Dependency graph, Dependabot alerts and security updates, private vulnerability reporting, secret scanning, and push protection were enabled. Main has an active ruleset blocking deletion and force pushes. Actions tokens are read-only, and external contributor workflow runs require approval. See REPOSITORY_SETTINGS.md and GitHub settings for current controls. Review results do not guarantee arbitrary future additions are safe.

Streamlit interface smoke test passed for all regions, North only, and empty selection. The browser blocked localhost, so demo assets include a reproducible SVG chart rather than a UI screenshot.
