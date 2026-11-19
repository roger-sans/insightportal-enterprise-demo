"""Initialise an empty GitHub delivery backlog without changing existing issues."""
import argparse
import json
from pathlib import Path
import re
from subprocess import check_output

ROOT = Path(__file__).resolve().parents[1]


def gh(*args):
    return check_output(["gh", *args], text=True).strip()


def issue_body(item):
    dependencies = ", ".join(item["dependencies"]) or "None"
    acceptance = "\n".join(f"- [ ] {criterion}" for criterion in item["acceptance"])
    if item["status"] == "done":
        acceptance = acceptance.replace("- [ ] ", "- [x] ")
    return (
        f"**{item['type']} · {item['epic']} · Priority {item['priority']}**\n\n"
        f"**Owner** — {item['owner']}\n\n{item['value']}\n\n"
        f"## Acceptance criteria\n\n{acceptance}\n\n"
        f"**Dependencies** — {dependencies}\n\n**Evidence** — {item['evidence']}\n"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="target GitHub owner/repository")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9-]+/[a-zA-Z0-9._-]+", args.repo):
        parser.error("use owner/repository format")
    manifest = json.loads((ROOT / "docs/backlog.json").read_text(encoding="utf-8"))
    repository = ["--repo", args.repo]
    milestones = set(gh("api", f"repos/{args.repo}/milestones?state=all&per_page=100",
                        "--paginate", "--jq", ".[].title").splitlines())
    for milestone in manifest["milestones"]:
        if milestone["name"] not in milestones:
            gh("api", f"repos/{args.repo}/milestones", "-f", f"title={milestone['name']}",
               "-f", f"description={milestone['description']}")
    issues = json.loads(gh("issue", "list", *repository, "--state", "all", "--limit", "500", "--json", "title"))
    existing = {item["title"].split(" ", 1)[0] for item in issues}
    for item in manifest["issues"]:
        if item["id"] in existing:
            continue
        url = gh("issue", "create", *repository, "--title", f"{item['id']} {item['title']}",
                 "--body", issue_body(item), "--milestone", manifest["milestones"][item["milestone"]]["name"])
        print(url)
        if item["status"] == "done":
            gh("issue", "close", url, "--reason", "completed")


if __name__ == "__main__":
    main()
