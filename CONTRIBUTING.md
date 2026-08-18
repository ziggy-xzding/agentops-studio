# Contributing to AgentOps Studio

Thanks for helping improve AgentOps Studio. Keep changes focused, reproducible, and safe to publish in a public repository.

## Development setup

1. Fork or clone the repository.
2. Follow the local setup in [README.md](README.md).
3. Create a branch from `main` for the change.
4. Add or update tests in proportion to the behavior being changed.
5. Run the checks below before opening a pull request.

Backend checks:

```bash
cd backend
ruff check app tests
pytest
```

Frontend checks:

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm test
pnpm build
```

Repository configuration:

```bash
docker compose config --quiet
```

## Pull requests

- Explain the user-visible behavior and the reason for the change.
- Keep unrelated formatting or refactoring out of the pull request.
- Include tests for new paths and regressions.
- Update English and Chinese documentation together when behavior changes.
- Call out database, API, environment, or deployment changes explicitly.
- Confirm that no secrets, private data, or generated local artifacts are included.

## Agent additions

New Agents should implement the existing adapter contract, register through the Agent registry, return structured outputs, and reuse the shared lifecycle rather than bypassing it. Document whether token and cost values are measured, estimated, synthetic, or zero.

An Agent that can create a durable side effect must validate the required inputs before proposing it and must keep the human review step visible. Add unit tests for its rules and integration tests for approval, rejection, retry, and any safety gate it introduces.

## Data policy

Use synthetic prompts, locations, outputs, and evaluation data only. Do not contribute credentials, employer code, internal documents, real customer or citizen information, or proprietary datasets.

## Reporting security issues

Do not disclose vulnerabilities in a public issue. Follow [SECURITY.md](SECURITY.md) instead.
