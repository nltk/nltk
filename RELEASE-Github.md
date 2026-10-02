# RELEASE-Github.md: Automated Release Workflow

This document details the operation of the NLTK GitHub Actions release workflow, defined in `.github/workflows/release.yml`. This workflow automates the creation of GitHub releases and supports optional PyPI integration for official distribution.

### Workflow Trigger

The workflow is **event-driven**. It is automatically initiated upon pushing a git tag that follows the `v` prefix naming convention to the repository.

* **Trigger Action:** `git push origin v3.10.x-rc`
* **Requirement:** The workflow file must be present on the target branch. **Crucially, the release tag must point to a commit located within `origin/develop` to ensure the release is built from the authorized development head.**

### Prerequisites & Permissions

Successful execution of this workflow requires specific repository configurations:

* **Write Permissions:** Pushing a release tag requires **write** access to the repository, and the workflow needs `contents: write` (via `GITHUB_TOKEN`) to create the draft GitHub release.
* **Fork Execution:** If executing within a fork, ensure the repository settings under **Actions > General > Workflow permissions** are set to "Read and write permissions" to allow the workflow to create release objects.
* **Secrets:** No additional repository secrets are required; the workflow uses the automatically provisioned `GITHUB_TOKEN` to query CI and create the draft release.

### Release Strategy: GitHub vs. PyPI

The workflow maintains a clear separation between testing and production release artifacts:

| Stage | Platform | Purpose |
| --- | --- | --- |
| **Release Candidate** | GitHub Releases | Early community feedback and environment validation. |
| **Official Release** | PyPI | Production distribution via `pip` and package repository indexing. |

> **Integration:** While the workflow primarily stages artifacts on GitHub, it is capable of handling **PyPI integration**. If configured, the workflow will automatically publish the build artifacts to PyPI upon successful validation of the release tag.

### Execution & Verification

1. **Initiate Release:** Trigger the workflow by pushing the appropriate tag to the remote:
   ```bash
   git tag v3.10.0-rc1
   git push origin v3.10.0-rc1
   ```

2. **CI Validation:** As implemented in **[#3506](https://github.com/nltk/nltk/pull/3506)**, the workflow performs an automated check to verify that Continuous Integration (CI) has successfully passed on the specific commit to which the release tag points.
3. **Monitor Logs:** Follow the execution progress in the repository’s **Actions** tab.
4. **Audit:** If the workflow fails to push to PyPI or draft a release, inspect the logs for:
   * **CI Failures:** Verify the commit status matches the requirements set forth in PR #3506.
   * **Branch Validation:** Ensure the tagged commit is reachable via `origin/develop`.
   * **Authentication errors:** Verify that the `PYPI_API_TOKEN` is active and has the correct scope.
   * **Permission errors:** Confirm that the `GITHUB_TOKEN` has been granted the necessary write access.
   * **Version conflicts:** Ensure the tag is not already associated with an existing release.
