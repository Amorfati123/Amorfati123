"""Keeps the research section of README.md up to date.

Recent publications get pulled from the public ORCID API on every run and written
between the publications marker comments.

If ORCID can't be reached, that block is left exactly as it was, so a flaky API
never wipes the README or fails the build.
"""
import re
from pathlib import Path

import requests

README_PATH = Path("README.md")
ORCID_ID = "0009-0003-8941-3396"
ORCID_WORKS_URL = "https://pub.orcid.org/v3.0/{orcid}/works"

MAX_PUBLICATIONS = 5


def orcid_value(data, *keys):
    for key in keys:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


# Turn one ORCID work summary into the few fields we actually show.
def parse_work(summary):
    title = orcid_value(summary, "title", "title", "value")
    if not title:
        return None
    # Journals like JMIR list the preprint as its own work next to the published paper, skip the copy.
    if title.strip().lower().endswith("(preprint)"):
        return None

    year = orcid_value(summary, "publication-date", "year", "value")
    month = orcid_value(summary, "publication-date", "month", "value")
    link = orcid_value(summary, "url", "value")
    for external_id in orcid_value(summary, "external-ids", "external-id") or []:
        if external_id.get("external-id-type") == "doi":
            link = f"https://doi.org/{external_id.get('external-id-value')}"
            break

    return {
        "title": " ".join(title.split()),
        "venue": orcid_value(summary, "journal-title", "value"),
        "year": year,
        "sort_key": (int(year or 0), int(month or 0)),
        "link": link,
    }


def fetch_publications(orcid=ORCID_ID, limit=MAX_PUBLICATIONS):
    response = requests.get(
        ORCID_WORKS_URL.format(orcid=orcid),
        headers={"Accept": "application/json"},
        timeout=30,
    )
    response.raise_for_status()

    works = []
    for group in response.json().get("group") or []:
        # ORCID groups duplicate records of the same work, the first one is the preferred version.
        summaries = group.get("work-summary") or []
        work = parse_work(summaries[0]) if summaries else None
        if work:
            works.append(work)

    works.sort(key=lambda work: work["sort_key"], reverse=True)
    return works[:limit]


# Keep titles and venues from breaking the markdown around them.
def clean_markdown(text):
    return re.sub(r"([\\`*_\[\]|<>])", r"\\\1", " ".join((text or "").split()))


def render_publications(works):
    if not works:
        return ""
    lines = ["### Recent publications", ""]
    for work in works:
        title = clean_markdown(work["title"])
        title = f"[{title}]({work['link']})" if work["link"] else title
        details = " · ".join(part for part in (clean_markdown(work["venue"]), work["year"]) if part)
        lines.append(f"- **{title}**" + (f"  \n  {details}" if details else ""))
    lines += ["", f"More on [ORCID](https://orcid.org/{ORCID_ID})."]
    return "\n".join(lines)


# Swap the text between <!-- name:start --> and <!-- name:end -->, adding the markers if they're missing.
def replace_block(readme, name, content):
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    block = f"{start}\n{content}\n{end}" if content else f"{start}\n{end}"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    if pattern.search(readme):
        return pattern.sub(lambda _: block, readme)
    return readme.rstrip("\n") + "\n\n" + block + "\n"


def update_readme(path=README_PATH):
    readme = path.read_text(encoding="utf-8")
    updated = readme

    try:
        updated = replace_block(updated, "publications", render_publications(fetch_publications()))
    except Exception as error:
        print(f"research: skipped publications this run, keeping the old ones ({error})")

    if updated != readme:
        path.write_text(updated, encoding="utf-8")
        print("research: README updated")
    else:
        print("research: README already up to date")
