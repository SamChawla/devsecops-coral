"""GitHub REST API — create PRs and issues for CVE remediation."""

from __future__ import annotations

import base64
import re
from typing import Any

import httpx

from devsecops_coral.config import GITHUB_OWNER, GITHUB_REPO, GITHUB_TOKEN

_API = "https://api.github.com"


class GitHubError(Exception):
    """Raised when a GitHub API call fails."""


def _headers() -> dict[str, str]:
    """Build GitHub API request headers.

    Raises:
        GitHubError: If GITHUB_TOKEN is not configured.
    """
    if not GITHUB_TOKEN:
        raise GitHubError("GITHUB_TOKEN is not set in .env")
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _default_branch_sha() -> tuple[str, str]:
    """Return ``(default_branch_name, head_commit_sha)``."""
    r = httpx.get(f"{_API}/repos/{GITHUB_OWNER}/{GITHUB_REPO}", headers=_headers(), timeout=20.0)
    if r.status_code >= 400:
        raise GitHubError(f"Could not fetch repo: {r.status_code}")
    branch = r.json().get("default_branch", "main")
    r2 = httpx.get(
        f"{_API}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/git/ref/heads/{branch}",
        headers=_headers(),
        timeout=20.0,
    )
    if r2.status_code >= 400:
        raise GitHubError(f"Could not fetch branch ref: {r2.status_code}")
    return branch, r2.json()["object"]["sha"]


def _get_requirements(branch: str) -> tuple[str, str]:
    """Fetch ``requirements.txt`` content and its blob SHA from the given branch."""
    r = httpx.get(
        f"{_API}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/requirements.txt",
        headers=_headers(),
        params={"ref": branch},
        timeout=20.0,
    )
    if r.status_code == 404:
        return "", ""
    if r.status_code >= 400:
        raise GitHubError(f"Could not fetch requirements.txt: {r.status_code}")
    data = r.json()
    return base64.b64decode(data["content"]).decode("utf-8"), data["sha"]


def _bump_version(content: str, package: str, fixed_version: str | None) -> str:
    """Replace or append the package pin in requirements.txt."""
    pattern = re.compile(rf"^{re.escape(package)}[>=!<\s].*$", re.MULTILINE | re.IGNORECASE)
    if fixed_version:
        replacement = f"{package}>={fixed_version}"
    else:
        replacement = f"{package}  # TODO: upgrade to latest patched version"
    if pattern.search(content):
        return pattern.sub(replacement, content)
    return content.rstrip("\n") + f"\n{replacement}\n"


def create_pull_request(
    *,
    title: str,
    body: str,
    package: str,
    cve: str | None = None,
    fixed_version: str | None = None,
) -> dict[str, Any]:
    """Create a security upgrade PR that bumps ``requirements.txt``.

    Workflow: create branch → update requirements.txt → open PR.

    Args:
        title: PR title shown in GitHub.
        body: PR description with CVE context.
        package: Package name to upgrade.
        cve: CVE identifier used in branch name.
        fixed_version: Target version (e.g. ``10.3.0``). Omit to add a TODO comment.

    Returns:
        Dict with keys ``number``, ``url``, and ``branch``.

    Raises:
        GitHubError: If credentials are missing or any API step fails.
    """
    if not GITHUB_OWNER or not GITHUB_REPO:
        raise GitHubError("GITHUB_OWNER and GITHUB_REPO must be set in .env")

    slug = re.sub(r"[^a-z0-9-]", "-", (cve or package).lower())[:24].strip("-")
    branch = f"security/upgrade-{package.lower()}-{slug}"
    base_branch, head_sha = _default_branch_sha()

    # Create branch (ignore 422 = already exists)
    r = httpx.post(
        f"{_API}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/git/refs",
        headers=_headers(),
        json={"ref": f"refs/heads/{branch}", "sha": head_sha},
        timeout=20.0,
    )
    if r.status_code not in (201, 422):
        raise GitHubError(f"Failed to create branch: {r.status_code} {r.text[:200]}")

    # Commit updated requirements.txt if the file exists
    req_content, req_sha = _get_requirements(base_branch)
    if req_content:
        new_content = _bump_version(req_content, package, fixed_version)
        if new_content != req_content:
            r2 = httpx.put(
                f"{_API}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/requirements.txt",
                headers=_headers(),
                json={
                    "message": f"security: upgrade {package} ({cve or 'CVE'})",
                    "content": base64.b64encode(new_content.encode()).decode(),
                    "sha": req_sha,
                    "branch": branch,
                },
                timeout=20.0,
            )
            if r2.status_code >= 400:
                raise GitHubError(f"Failed to commit requirements.txt: {r2.status_code}")

    # Open the PR
    r3 = httpx.post(
        f"{_API}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/pulls",
        headers=_headers(),
        json={"title": title, "head": branch, "base": base_branch, "body": body},
        timeout=20.0,
    )
    if r3.status_code >= 400:
        raise GitHubError(f"Failed to create PR: {r3.status_code} {r3.text[:200]}")

    pr = r3.json()
    return {"number": pr.get("number"), "url": pr.get("html_url", ""), "branch": branch}


def create_issue(
    *,
    title: str,
    body: str,
    labels: list[str] | None = None,
) -> dict[str, Any]:
    """Create a GitHub issue for CVE visibility tracking.

    Args:
        title: Issue title.
        body: Issue description.
        labels: Labels to apply (``security`` and ``vulnerability`` added by default).

    Returns:
        Dict with keys ``number`` and ``url``.

    Raises:
        GitHubError: If credentials are missing or the API call fails.
    """
    if not GITHUB_OWNER or not GITHUB_REPO:
        raise GitHubError("GITHUB_OWNER and GITHUB_REPO must be set in .env")

    r = httpx.post(
        f"{_API}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/issues",
        headers=_headers(),
        json={
            "title": title,
            "body": body,
            "labels": list({*(labels or []), "security", "vulnerability"}),
        },
        timeout=20.0,
    )
    if r.status_code >= 400:
        raise GitHubError(f"Failed to create issue: {r.status_code} {r.text[:200]}")
    data = r.json()
    return {"number": data.get("number"), "url": data.get("html_url", "")}
