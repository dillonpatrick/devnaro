# Local CI reporting

DevNaro can publish the outcome of a local `act` run as a GitHub Check Run on the commit being tested.

## What is published

- One Check Run named **DevNaro Local CI (act)**.
- The Check is marked `in_progress` before `act` starts.
- At completion, the Check is updated to `completed` with a `success` or `failure` conclusion.
- The summary includes the overall result and elapsed time.

The report is aggregate. It does not create a workflow run in the GitHub Actions tab, create a separate Check for every `act` job, or upload the full local logs. The complete `act` output remains in the terminal.

## Requirements

The GitHub Checks API endpoint used to create Check Runs requires a GitHub App installation token with the **Checks: write** repository permission.

1. Create or use a GitHub App.
2. Grant it the repository permission **Checks: write**.
3. Install the App on the repository where the Check should appear.
4. Generate an installation access token for that installation.
5. Pass the token to the local command:

```bash
DEVNARO_GITHUB_TOKEN="<github-app-installation-token>" devnaro ci
```

The token is read from `DEVNARO_GITHUB_TOKEN`. For convenience, `GH_TOKEN` and `GITHUB_TOKEN` are also accepted. Do not commit tokens to the repository or put them in tracked configuration files. Installation tokens are short-lived; generate a fresh token when needed.

## Repository detection

DevNaro reads the `origin` Git remote and supports HTTPS and SSH GitHub remotes. To explicitly select a repository, set:

```bash
DEVNARO_GITHUB_REPOSITORY=OWNER/REPOSITORY
```

The Check is attached to the current `HEAD` commit. Ensure that commit exists in the target GitHub repository.

## Failure behavior

Reporting is optional. If no token is configured, DevNaro runs `act` normally and skips GitHub reporting. If the Check cannot be created, DevNaro prints a warning and continues with the local CI run. A reporting failure when updating an already-created Check is also a warning and does not replace the actual `act` exit code.

The exit code from `act` remains the exit code of `devnaro ci`.
