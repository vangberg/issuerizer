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

class GitHubClient:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "issuerizer-cli"
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    def get_issue(self, owner: str, repo: str, issue_number: int) -> Issue:
        url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
        
        with httpx.Client() as client:
            response = client.get(url, headers=self.headers)
            response.raise_for_status()
            issue_data = response.json()
            
            # Fetch comments
            comments_url = issue_data["comments_url"]
            comments_resp = client.get(comments_url, headers=self.headers)
            comments_resp.raise_for_status()
            comments_data = comments_resp.json()
            
            # Parse comments
            comments = [Comment(**c) for c in comments_data]

            # Fetch events
            events_url = issue_data["events_url"]
            events_resp = client.get(events_url, headers=self.headers)
            events_resp.raise_for_status()
            events_data = events_resp.json()
            
            # Parse events
            events = [Event(**e) for e in events_data]

            # Fetch sub-issues (if any)
            # Try to fetch sub-issues blindly or check for sub_issues_summary in issue_data
            # For robustness, we check if the field exists, but since we know the endpoint works,
            # we can just try to fetch them.
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

            # Create Issue object
            issue = Issue(
                **issue_data,
                comments_list=comments,
                events_list=events,
                sub_issues_list=sub_issues
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
