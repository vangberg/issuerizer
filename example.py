from issuerizer.github import GitHubClient
import os

# This example demonstrates how to use the GitHubClient directly.
# For private repositories or to avoid GitHub API rate limits,
# it's recommended to set a GITHUB_TOKEN environment variable.
# You can do this by creating a .env file in the project root with
# GITHUB_TOKEN="your_token_here" or by setting it in your shell.

def demonstrate_github_client():
    """
    Demonstrates fetching a GitHub issue using the GitHubClient.
    """
    # Example: Summarize a public issue from python/cpython
    # You can change these values to any public GitHub repository and issue number.
    owner = "python"
    repo = "cpython"
    issue_num = 1
    
    print(f"--- Demonstrating direct GitHubClient usage ---")
    print(f"Fetching issue #{issue_num} from {owner}/{repo}...")

    try:
        client = GitHubClient()
        issue_obj = client.get_issue(owner, repo, issue_num)
        
        print(f"Title: {issue_obj.title}")
        print(f"Author: {issue_obj.user.login}")
        print(f"State: {issue_obj.state}")
        print(f"Link: {issue_obj.html_url}")
        print(f"Comments: {len(issue_obj.comments_list)}")
        
        if issue_obj.body:
            print("\nIssue Body Snippet:")
            print(issue_obj.body[:200] + ("..." if len(issue_obj.body) > 200 else ""))

        if issue_obj.comments_list:
            first_comment = issue_obj.comments_list[0]
            print(f"\nFirst comment by {first_comment.user.login} (ID: {first_comment.id}):")
            print(first_comment.body[:150] + ("..." if len(first_comment.body) > 150 else ""))
            
    except Exception as e:
        print(f"An error occurred: {e}")

# Call the demonstration function directly
demonstrate_github_client()

print("\n--- Example complete ---")