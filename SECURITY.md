# Security Policy

## Supported versions

AgentOps Studio is an actively developed demonstration project and does not currently publish versioned security releases. Security fixes are applied to the latest revision of `main`.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting feature for this repository. Include the affected component, reproduction steps, impact, and any suggested mitigation. Do not include credentials, tokens, personal data, or live-system records in the report.

Please do not open a public issue for an undisclosed vulnerability. If private vulnerability reporting is not available, contact the repository owner through a private channel listed on their GitHub profile before sharing technical details.

## Demo security boundary

The current project is intended for local development and evaluation. It does not implement authentication, authorization, tenant isolation, rate limiting, production secret management, or hardened public deployment defaults. The built-in database credentials in Docker Compose are local-development placeholders.

Do not expose this demo directly to the public internet without adding those controls and completing a deployment-specific security review.

## Data safety

Only synthetic data belongs in this repository and its demonstrations. Never commit `.env` files, API keys, private keys, certificates, employer source code, internal documents, real customer or citizen data, or proprietary evaluation sets.
