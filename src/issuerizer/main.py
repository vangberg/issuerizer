import typer
import re
import sys
from datetime import datetime
from rich.console import Console
from rich.markdown import Markdown
from urllib.parse import urlparse
from issuerizer.github import GitHubClient
from issuerizer.llm import get_summary

app = typer.Typer()
console = Console()

def parse_issue_query(query: str):
    """
    Parses a GitHub issue URL or shorthand string (owner/repo#number).
    Returns (owner, repo, issue_number).
    """
    # Try URL
    if query.startswith("http"):
        parsed = urlparse(query)
        # path: /owner/repo/issues/number
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 4 and parts[2] == "issues":
            return parts[0], parts[1], int(parts[3])
            
    # Try owner/repo#number
    match = re.match(r"^([^/]+)/([^/]+)#(\d+)$", query)
    if match:
        return match.group(1), match.group(2), int(match.group(3))
    
    # Try owner/repo issue_number (space separated, handled by typer usually but here query is one string?)
    # If the user provides arguments like "owner repo number", typer handles that if we define args.
    # But we want a single entrypoint.
    
    raise ValueError(f"Could not parse issue query: '{query}'. Expected URL or 'owner/repo#number'.")

def process_issue(owner: str, repo: str, issue_number: int, update: bool, verbose: bool):
    client = GitHubClient()
    with console.status(f"[bold green]Fetching issue #{issue_number} from {owner}/{repo}..."):
        issue = client.get_issue(owner, repo, issue_number)
        readme_content = client.get_readme(owner, repo)
    
    console.print(f"[bold blue]Title:[/bold blue] {issue.title}")
    console.print(f"[bold blue]State:[/bold blue] {issue.state}")
    console.print(f"[bold blue]Author:[/bold blue] {issue.user.login}")
    console.print(f"[bold blue]Created:[/bold blue] {issue.created_at}")
    console.print(f"[bold blue]Link:[/bold blue] {issue.html_url}")
    console.print(f"[bold blue]Comments:[/bold blue] {len(issue.comments_list)}")
    console.print(f"[bold blue]Events:[/bold blue] {len(issue.events_list)}")
    if not issue.comments_list:
        console.print("[yellow]No comments found for this issue. Skipping summary generation.[/yellow]")
        return
    if readme_content:
        console.print(f"[bold blue]README:[/bold blue] Found ({len(readme_content)} chars)")
    else:
        console.print(f"[bold blue]README:[/bold blue] Not found")
    
    console.print("\n[bold]Generating Summary...[/bold]")
    try:
        summary = get_summary(issue, readme_content, verbose)
        console.print("\n[bold]--- AI Summary ---[/bold]\n")
        console.print(Markdown(summary))

        if update:
            issuerizer_repo_link = "https://github.com/vangberg/issuerizer"
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z") # %Z for timezone name, but it's often empty
            generated_by_note = f"\n\n---\n_Generated on {current_time} by [Issuerizer]({issuerizer_repo_link})_"
            summary_with_note = summary + generated_by_note

            try:
                with console.status(f"[bold green]Updating issue #{issue_number} in {owner}/{repo}..."):
                    client.update_issue(owner, repo, issue_number, summary_with_note)
                console.print(f"[bold green]Successfully updated issue #{issue_number} with the generated summary.[/bold green]")
            except Exception as update_e:
                console.print(f"[bold red]Error updating issue:[/bold red] {update_e}")

    except ValueError as e:
            console.print(f"[yellow]Warning: Skipping AI summary ({e})[/yellow]")
            raise

@app.command()
def summarize(
    issue_query: str,
    update: bool = typer.Option(False, "--update", "-u", help="Update the GitHub issue body with the generated summary."),
    update_parent: bool = typer.Option(False, "--update-parent", help="Find and summarize the parent of the provided issue."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Print the prompt sent to the LLM.")
):
    """
    Fetch and summarize a GitHub issue.
    Accepts a URL (e.g., https://github.com/owner/repo/issues/1)
    or a shorthand string (e.g., owner/repo#1).
    
    If --update-parent is used, the provided issue is treated as a child, and its parent
    is fetched and summarized instead.
    """
    try:
        owner, repo, issue_number = parse_issue_query(issue_query)

        if update_parent:
            client = GitHubClient()
            with console.status(f"[bold green]Fetching issue #{issue_number} from {owner}/{repo} to find parent..."):
                issue = client.get_issue(owner, repo, issue_number)
            
            if issue.parent:
                # Determine parent owner/repo
                # Default to same repo
                p_owner, p_repo = owner, repo
                if issue.parent.repository_url:
                    # Expected format: https://api.github.com/repos/OWNER/REPO
                    parts = issue.parent.repository_url.split("/repos/")
                    if len(parts) > 1:
                        repo_part = parts[1].split("/")
                        if len(repo_part) >= 2:
                            p_owner, p_repo = repo_part[0], repo_part[1]
                
                console.print(f"[bold green]Found parent issue:[/bold green] {p_owner}/{p_repo}#{issue.parent.number}")
                owner, repo, issue_number = p_owner, p_repo, issue.parent.number
            else:
                console.print(f"[yellow]No parent issue found for #{issue_number}. Exiting.[/yellow]")
                return

        process_issue(owner, repo, issue_number, update, verbose)

    except ValueError as ve:
        console.print(f"[bold red]Input Error:[/bold red] {ve}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")

if __name__ == "__main__":
    app()
