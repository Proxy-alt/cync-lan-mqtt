# Releasing

This repository ships one artifact: the `cync-lan-mqtt` Docker/MQTT add-on.

| Artifact | Branch | Version lives in | Changelog | Distribution | Tag prefix |
|---|---|---|---|---|---|
| `cync-lan-mqtt` add-on | `main` | `pyproject.toml`'s `version` | `CHANGELOG.md` | PyPI, via Trusted Publishing; ghcr.io container; consumed by `hass-addons`' Docker build | `cync-lan-mqtt-vX.Y.Z` |

It depends on the `cync-lan` core protocol library as a normal PyPI
dependency (`pyproject.toml`), released separately from
[`Proxy-alt/cync-lan-lib`](https://github.com/Proxy-alt/cync-lan-lib).
Bumping core doesn't require bumping this, and vice versa. Nothing is
vendored. The Home Assistant `cync_lan` custom_component is a third,
independent artifact, in
[`Proxy-alt/cync-lan`](https://github.com/Proxy-alt/cync-lan).

## Releasing

1. Bump `pyproject.toml`'s `version` (semver).
2. If the change also requires a newer core version, bump the
   `cync-lan>=X.Y.Z` line in `dependencies` too.
3. Add a matching entry at the top of `CHANGELOG.md`, **using that exact
   version string as the `### ` heading** - the release workflow parses this
   heading out verbatim.
4. Commit and push to `main`.

Tagging, the GitHub release, the PyPI publish, and the container build are
automated from there.

## Release vs prerelease

Decided from the version string alone, by the workflow's "Classify the
version" step. There is no flag or manual toggle:

| Version   | Result                          |
|-----------|---------------------------------|
| `0.2.3`   | full release                    |
| `0.2.3b1` | prerelease (a beta)             |
| anything else | **the run fails**           |

Anything matching neither shape is a hard error, so a typo like `0.2.O` or
`0.2` fails loudly instead of quietly shipping as the wrong kind.

- **`bN` means digits.** This is not a style preference: the package
  uploads to PyPI, so its version must be valid PEP 440, and PEP 440's
  pre-release segment is `b` followed by a *number*. A commit sha is
  rejected - `packaging.version.Version("0.2.3b2aad577")` raises
  `InvalidVersion`, and the upload would fail *after* the tag and GitHub
  release already existed. (`0.2.3+2aad577` parses, but PyPI refuses local
  versions on upload, so that is no escape hatch either.) The same rule
  applies in the other two repositories - one rule beats an exception
  nobody remembers.
- **Betas do not need a CHANGELOG entry**; full releases still do. Betas
  get a generated stub instead.
- A beta never moves the container's `latest` tag - someone pulling
  `:latest` should never land on a prerelease.

## What the workflows do

`.github/workflows/publish_pypi_addon.yml`, on a push to `main` that changes
`pyproject.toml`:

1. Reads the new version out of `pyproject.toml`.
2. Checks whether a tag for that version already exists (`git ls-remote
   --tags`) - if so, does nothing.
3. Extracts that version's own section out of `CHANGELOG.md` (the `###
   <version>` heading must match the version file *exactly*, or this step
   fails loudly rather than silently publishing an empty or wrong release).
   Betas are exempt, per above.
4. Tags the current commit and creates a GitHub Release from it via `gh
   release create`, passing `--latest` or `--prerelease` per the table
   above.
5. Builds and publishes to PyPI via Trusted Publishing (no stored API token
   - PyPI trusts this specific GitHub Actions workflow directly).

The publish step gates on PyPI's own state rather than on the tag check, so
a `workflow_dispatch` re-run can retry a failed upload alone without needing
a new version.

`.github/workflows/container-package-publish.yml` then builds and pushes the
multi-arch image to ghcr.io (and Docker Hub, if `DOCKER_HUB_KEY` is set).

Note its `workflow_run` trigger, which is not redundant with `release:
published`: GitHub deliberately raises no events for anything created with
`GITHUB_TOKEN`, to stop workflows triggering themselves, so an *automated*
release fires no `release` event at all. That is why ghcr once sat on a
stale image while PyPI moved - the publish simply never ran. `workflow_run`
is raised by the run finishing rather than by the token, so it fires. It
also checks `conclusion == 'success'` explicitly, because `workflow_run`
fires whatever the outcome and a release that failed its tests should not
publish an image.

### Trusted Publishing setup

This requires a PyPI "pending publisher" configured once, in PyPI's web UI
(Account Settings -> Publishing):

| Field | Value |
|---|---|
| Repository | `Proxy-alt/cync-lan-mqtt` |
| Workflow filename | `publish_pypi_addon.yml` |
| Environment | `pypi-mqtt` |

**This changed when the add-on moved out of `Proxy-alt/cync-lan`.** The old
publisher pointed at that repository; a publisher naming the wrong repo does
not fail at tag time, it fails at the upload step, *after* the tag and
GitHub release already exist. If a release tags cleanly but never lands on
PyPI, check this first.

## Why this add-on has its own repository

It used to live on a `python` branch of `Proxy-alt/cync-lan`, alongside the
core library (`core`) and the HA integration
(`feature/ha-custom-component`) - three separately-versioned artifacts
sharing one GitHub release list.

That broke HACS. HACS does not read the "Latest" flag: it calls the
`/releases` **list** endpoint and takes the first non-draft, non-prerelease
entry in list order, which GitHub returns newest-first by date. So whenever
a `cync-lan-mqtt-v*` or `cync-lan-v*` release happened to be the most
recent, HACS advertised *that* tag as the integration's update - and those
tags point at trees with no `custom_components/` directory, so the download
failed and the update was uninstallable.

Marking the integration's releases `--latest` did not help, because the flag
is never consulted. Cutting the other two with `--latest=false`, which is
what the workflows used to do, was addressing a mechanism that does not
exist. The only lever HACS actually honours is *what is in the release list
at all* - and `hacs.json` has no tag filter. One artifact per repository is
what fixes it, permanently.

Tags are invisible to HACS (it needs published releases), so the historical
`cync-lan-mqtt-v*` tags left behind in `Proxy-alt/cync-lan` are harmless.

## Keeping `hass-addons` in sync

`hass-addons/cync-lan/` (the Home Assistant *App*/add-on packaging, distinct
from all three artifacts above) installs `cync-lan-mqtt` from PyPI in its
`Dockerfile`, and separately vendors this repository in via `git subtree`
under `cync-lan/upstream/` for docs/changelog reference - refreshed
automatically by a scheduled GitHub Actions workflow in that repository, not
the actual runtime install path.

**That workflow points at the old location** (`Proxy-alt/cync-lan`, branch
`python`) and needs repointing at this repository's `main`. Its
`CHANGELOG.md` and `README.md` device-support claims should track whatever
this repository's `CHANGELOG.md` and `docs/known_devices.md` say - if you
find them out of sync, check whether that workflow has been failing before
manually reconciling the two.
