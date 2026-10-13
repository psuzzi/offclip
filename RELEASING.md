# Releasing offclip

A tag push builds, tests and publishes everything (`.github/workflows/release.yml`). Nothing is built locally.

1. **Version**: set `__version__` in `offclip/__init__.py` to `X.Y.Z`.
2. **Changelog**: add a `## X.Y.Z — YYYY-MM-DD` section at the top of `CHANGELOG.md`. It becomes the release's
   *What's new*; the download table and the fixed paragraphs (`scripts/release-notes-tail.md`) are added around it.
3. **Commit and push** to `main`, wait for the `test` workflow to pass.
4. **Tag and push the tag**: `git tag vX.Y.Z && git push origin vX.Y.Z`. The `release` workflow checks the tag against
   `__version__` and the CHANGELOG, builds the four ZIPs, the `.deb`/`.rpm` (installed and run on Ubuntu and Fedora) and
   `offclip-setup.exe` (silent install, run, uninstall on Windows), writes `SHA256SUMS`, and creates the release marked
   latest. If any job fails there is no release.

If a run fails: fix on `main`, then delete the tag (`git push origin :vX.Y.Z && git tag -d vX.Y.Z`) and any draft
release it left (`gh release delete vX.Y.Z`), and tag again. Never edit or delete earlier releases.

`packages.yml` alone (Actions ▸ packages ▸ Run workflow) builds and tests the packages for any tag without releasing.
`scripts/release-check.sh vX.Y.Z` and `scripts/release-notes.sh vX.Y.Z` run the same checks and notes locally.
