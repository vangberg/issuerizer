import os
import httpx
from typing import List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class User(BaseModel):
    login: str
    html_url: str

class Comment(BaseModel):
    id: int
    user: User
    body: str
    html_url: str
    created_at: str

class SimpleIssue(BaseModel):
    number: int
    title: str
    html_url: str
    state: str
    body: Optional[str] = None
    user: Optional[User] = None
    repository_url: Optional[str] = None
    pull_request: Optional[dict] = None

class EventSource(BaseModel):
    type: Optional[str] = None
    issue: Optional[SimpleIssue] = None

class Event(BaseModel):
    id: int
    event: str
    actor: Optional[User] = None
    created_at: str
    commit_id: Optional[str] = None
    source: Optional[EventSource] = None

class Issue(BaseModel):
    id: int
    number: int
    title: str
    user: User
    html_url: str
    state: str
    created_at: str
    updated_at: Optional[str] = None
    body: Optional[str] = None
    comments_url: str
    events_url: str
    comments_list: List[Comment] = []
    events_list: List[Event] = []
    sub_issues_list: List[SimpleIssue] = []
    parent: Optional[SimpleIssue] = None

class GitHubClient:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.headers = {
            "Accept": "application/vnd.github.sub-issues+json",
            "User-Agent": "issuerizer-cli"
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    def _get_all_pages(self, url: str, client: httpx.Client) -> List[dict]:
        all_items = []
        while url:
            resp = client.get(url, headers=self.headers)
            resp.raise_for_status()
            items = resp.json()
            if isinstance(items, list):
                all_items.extend(items)
            else:
                # Should not happen for list endpoints, but safety first
                break
            
            # Check for next page
            url = None
            if "link" in resp.headers: # Header keys are case-insensitive, httpx lowercases them?
                # httpx headers are case-insensitive.
                links = resp.headers["link"].split(", ")
                for link in links:
                    if 'rel="next"' in link:
                        # Extract URL from <url>; rel="next"
                        url = link.split(";")[0].strip("<>")
                        break
        return all_items

    def get_issue(self, owner: str, repo: str, issue_number: int) -> Issue:
        url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
        
        with httpx.Client() as client:
            response = client.get(url, headers=self.headers)
            response.raise_for_status()
            issue_data = response.json()
            
            # Fetch comments
            comments_url = issue_data["comments_url"]
            # For comments, we might also want pagination, but let's stick to events for now as per request.
            # But wait, large discussions might miss comments too. Let's do it for comments as well.
            comments_data = self._get_all_pages(comments_url, client)
            
            # Parse comments
            comments = [Comment(**c) for c in comments_data]

            # Fetch events
            events_url = issue_data["events_url"]
            events_data = self._get_all_pages(events_url, client)
            
            # Parse events
            events = [Event(**e) for e in events_data]

            # Fetch sub-issues (if any)
            sub_issues = []
            if "sub_issues_summary" in issue_data and issue_data["sub_issues_summary"]["total"] > 0:
                sub_issues_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/sub_issues"
                try:
                    sub_resp = client.get(sub_issues_url, headers=self.headers)
                    if sub_resp.status_code == 200:
                        sub_data = sub_resp.json()
                        sub_issues = [SimpleIssue(**s) for s in sub_data]
                except Exception as e:
                    print(f"Warning: Failed to fetch sub-issues: {e}")

            # Handle parent issue
            parent_obj = None
            if "parent" in issue_data:
                # If parent is already in the response, we use it (Pydantic can handle dict, but let's be explicit)
                parent_obj = SimpleIssue(**issue_data["parent"])
                del issue_data["parent"] # Remove to avoid collision
            elif issue_data.get("parent_issue_url"):
                # If only URL is present, fetch the parent
                try:
                    p_resp = client.get(issue_data["parent_issue_url"], headers=self.headers)
                    if p_resp.status_code == 200:
                        parent_obj = SimpleIssue(**p_resp.json())
                except Exception as e:
                    print(f"Warning: Failed to fetch parent issue: {e}")

            # Create Issue object
            issue = Issue(
                **issue_data,
                comments_list=comments,
                events_list=events,
                sub_issues_list=sub_issues,
                parent=parent_obj
            )
            
            return issue

    def get_readme(self, owner: str, repo: str) -> Optional[str]:
        """
        Fetches the README.md content for the specified repository.
        Returns None if not found or on error.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/readme"
        headers = self.headers.copy()
        headers["Accept"] = "application/vnd.github.v3.raw"
        
        with httpx.Client() as client:
            try:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                return response.text
            except httpx.HTTPStatusError as e:
                # 404 Not Found is common if no README exists
                if e.response.status_code == 404:
                    return None
                print(f"Error fetching README: {e}")
                return None
            except Exception as e:
                print(f"Error fetching README: {e}")
                return None

    def update_issue(self, owner: str, repo: str, issue_number: int, new_body: str) -> None:
        url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
        headers = self.headers.copy()
        
        # GitHub API requires "application/vnd.github.v3+json" for PATCH requests
        # and sends back the updated issue object.
        headers["Accept"] = "application/vnd.github.v3+json" 
        
        payload = {"body": new_body}
        
        with httpx.Client() as client:
            response = client.patch(url, headers=headers, json=payload)
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
            # Optionally, you could return the updated issue data if needed

if __name__ == "__main__":
    # Example usage
    # Ensure you have GITHUB_TOKEN set in your .env file or environment variables
    
    # Using a public repository for demonstration: python/cpython, issue #1
    # Note: Accessing public repos might work without a token but rate limits are strict.
    owner = "python"
    repo = "cpython"
    issue_num = 1
    
    try:
        client = GitHubClient()
        print(f"Fetching issue #{issue_num} from {owner}/{repo}...")
        issue_obj = client.get_issue(owner, repo, issue_num)
        
        print(f"Title: {issue_obj.title}")
        print(f"Author: {issue_obj.user.login}")
        print(f"State: {issue_obj.state}")
        print(f"Comments: {len(issue_obj.comments_list)}")
        print(f"Events: {len(issue_obj.events_list)}")
        
        if issue_obj.comments_list:
            first_comment = issue_obj.comments_list[0]
            print(f"First comment by {first_comment.user.login}: {first_comment.body[:50]}...")

        if issue_obj.events_list:
            first_event = issue_obj.events_list[0]
            print(f"First event: {first_event.event} by {first_event.actor.login if first_event.actor else 'Unknown'} at {first_event.created_at}")
            
            # Print linked issues from events
            print("\nLinked Issues/PRs from events:")
            for event in issue_obj.events_list:
                if event.source and event.source.issue:
                    linked = event.source.issue
                    print(f" - {linked.title} (#{linked.number}) [{linked.state}]")

            
    except Exception as e:
        print(f"An error occurred: {e}")
