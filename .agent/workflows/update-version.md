---
description: How to update the integration version
---

# Update Integration Version

Use this workflow whenever you make changes to the integration that should result in a new version. There is no version script — the agent (or human) updates the version files directly.

## Steps

1. **Make your code changes**
   - Edit files in `custom_components/winbot_mini/`
   - Test your changes

2. **Bump the version** (follow [Semantic Versioning](https://semver.org/))
   - **Patch** (1.0.3 → 1.0.4): bug fixes
   - **Minor** (1.0.3 → 1.1.0): new features, backwards compatible
   - **Major** (1.0.3 → 2.0.0): breaking changes

   Update all of these to the same version string:
   - `.version` — single source of truth (one line, e.g. `1.0.4`)
   - `custom_components/winbot_mini/manifest.json` — `"version"` field
   - `custom_components/winbot_mini/const.py` — `VERSION` constant
   - `README.md` — `**Version:** X.Y.Z` at the top

3. **Update the changelog**
   - Edit `VERSION.md`
   - Add your changes under a new version section
   - Follow the existing Keep a Changelog format

4. **Verify**
   - Confirm `.version`, `manifest.json`, `const.py`, and `README.md` all match
   - Review the changelog entry

5. **Commit** (when the user asks)
   ```bash
   git add .
   git commit -m "Release version X.Y.Z"
   git tag vX.Y.Z
   git push && git push --tags
   ```
