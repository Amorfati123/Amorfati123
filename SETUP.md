# Setup for `Amorfati123/Amorfati123`

This package recreates the terminal-style profile README used by `Vikbg/Vikbg`, customized for Shikhar Shukla.

## 1. Replace the files in your profile repository

Your GitHub profile README repository must be named exactly:

`Amorfati123/Amorfati123`

Copy all files and folders from this package into that repository and push to the `main` branch.

## 2. Enable GitHub Actions write access

In the repository:

**Settings -> Actions -> General -> Workflow permissions -> Read and write permissions**

Save the setting.

## 3. Add an access token for complete statistics

The generator calculates repository, star, follower, commit, and code-change statistics. For the full commit/LOC calculation across your public repositories, add a GitHub personal access token as a repository secret.

Go to:

**Settings -> Secrets and variables -> Actions -> New repository secret**

Create:

- Name: `ACCESS_TOKEN`
- Value: a GitHub personal access token that can read your public repositories

`USER_NAME` is optional because the workflow automatically uses the repository owner. If added, set it to `Amorfati123`.

Do not place the token directly in any file.

## 4. Run it once

Open:

**Actions -> README build -> Run workflow**

The workflow updates `dark_mode.svg` and `light_mode.svg`, commits the new statistics, and will run automatically each day.

## 5. Profile photo

The large circular photo on the left side of GitHub is your normal GitHub avatar. This package does not replace it.

The portrait inside the terminal card is ASCII art generated from your current GitHub avatar. To regenerate it from a different photo, replace the ASCII `<tspan>` lines near the top of both SVG files.

## Files

- `README.md` - displays the correct SVG automatically for GitHub light/dark mode
- `dark_mode.svg` - dark terminal card
- `light_mode.svg` - light terminal card
- `today.py` - computes GitHub statistics
- `generate_readme.py` - GitHub Actions-safe generator entry point
- `.github/workflows/build.yaml` - daily automation
- `cache/requirements.txt` - Python dependencies
- `LICENSE` / `NOTICE` - Apache 2.0 license and required upstream attribution

## Custom profile content currently shown

- Biomedical Data Scientist
- Clinical AI, ML, Public Health
- EHR, voice biomarkers, causal inference
- Python, R, SQL
- PyTorch, XGBoost, LightGBM
- Pandas, PySpark, Palantir
- Perioperative AI, explainable ML, deep learning, transformers, LLMs
- Portfolio, LinkedIn, ORCID, and GitHub links
