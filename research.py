"""Keeps the research section of README.md up to date.

Two blocks get rebuilt on every run, each between its own pair of marker comments:
- recent publications, pulled from the public ORCID API
- featured projects, taken from the repos pinned on the GitHub profile

If a source can't be reached, that block is left exactly as it was, so a flaky API
never wipes the README or fails the build.
"""
import re
from pathlib import Path

import requests

import today

README_PATH = Path("README.md")
ORCID_ID = "0009-0003-8941-3396"
ORCID_WORKS_URL = "https://pub.orcid.org/v3.0/{orcid}/works"
PUBLIC_REPOS_URL = "https://api.github.com/users/{username}/repos"

MAX_PUBLICATIONS = 5
MAX_PROJECTS = 6

PINNED_QUERY = """
query ($login: String!) {
    user(login: $login) {
        pinnedItems(first: 6, types: REPOSITORY) {
            nodes {
                ... on Repository {
                    name
                    nameWithOwner
                    url
                    description
                    stargazerCount
                    primaryLanguage {
                        name
                    }
                }
            }
        }
    }
}"""


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


def fetch_pinned_projects():
    data = today.graphql_request("pinned_repos", PINNED_QUERY, {"login": today.USER_NAME})
    nodes = data["user"]["pinnedItems"]["nodes"]
    return [
        {
            "name": node["name"],
            "url": node["url"],
            "description": node.get("description"),
            "language": (node.get("primaryLanguage") or {}).get("name"),
            "stars": node.get("stargazerCount", 0),
        }
        for node in nodes
        if node
    ]


# Used when nothing is pinned: show my most starred, most recently active public repos instead.
def fetch_top_projects(limit=MAX_PROJECTS):
    response = requests.get(
        PUBLIC_REPOS_URL.format(username=today.USER_NAME),
        params={"type": "owner", "sort": "pushed", "per_page": 100},
        headers={"Accept": "application/vnd.github+json"},
        timeout=30,
    )
    response.raise_for_status()

    repos = [
        repo for repo in response.json()
        if not repo.get("fork") and repo["name"].lower() != today.USER_NAME.lower()
    ]
    # Sort is stable, so repos with the same star count stay in most recently pushed order.
    repos.sort(key=lambda repo: repo.get("stargazers_count", 0), reverse=True)
    return [
        {
            "name": repo["name"],
            "url": repo["html_url"],
            "description": repo.get("description"),
            "language": repo.get("language"),
            "stars": repo.get("stargazers_count", 0),
        }
        for repo in repos[:limit]
    ]


def fetch_projects():
    try:
        projects = fetch_pinned_projects()
    except Exception as error:
        print(f"research: couldn't read pinned repos ({error}), using top repos instead")
        projects = []
    return projects or fetch_top_projects()


# Keep titles and descriptions from breaking the markdown around them.
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


def render_projects(projects):
    if not projects:
        return ""
    lines = [
        "### Featured projects",
        "",
        "| Project | About | Language | Stars |",
        "| --- | --- | --- | ---: |",
    ]
    for project in projects:
        lines.append(
            f"| [{clean_markdown(project['name'])}]({project['url']}) "
            f"| {clean_markdown(project['description']) or ' '} "
            f"| {clean_markdown(project['language']) or ' '} "
            f"| {project['stars']} |"
        )
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

    sections = (
        ("publications", fetch_publications, render_publications),
        ("projects", fetch_projects, render_projects),
    )
    for name, fetch, render in sections:
        try:
            updated = replace_block(updated, name, render(fetch()))
        except Exception as error:
            print(f"research: skipped {name} this run, keeping the old one ({error})")

    if updated != readme:
        path.write_text(updated, encoding="utf-8")
        print("research: README updated")
    else:
        print("research: README already up to date")
