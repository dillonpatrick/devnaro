# Automated validation

DevNaro uses the GitHub Actions workflow in `.github/workflows/devnaro-validation.yml` to validate changes targeting `main`.

The workflow runs three jobs:

- **Python tests:** installs the locked project and development dependencies with the pinned `uv` version, then runs the test suite.
- **Repository validation:** checks host and container shell syntax, validates the DevNaro help output, compiles the container-side Python entry point, and verifies the Docker Compose configuration.
- **Docker image build and smoke tests:** builds the DevNaro image, starts a disposable container from that image, and checks the container CLI, expected development tools, Python version, host bridge binaries, and workspace mount.

The workflow runs automatically on pushes to `main`; use `devnaro ci` to validate feature branches locally before merging. The smoke tests exercise the built container image; they do not replace manual checks of host integration, VS Code GUI behavior, or the host-side bridge connection.
