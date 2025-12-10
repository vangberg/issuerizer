import os
import anthropic
from issuerizer.github import Issue

def get_summary(issue: Issue) -> str:
    """
    Generates a summary of the provided GitHub issue using the Anthropic API.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")

    client = anthropic.Anthropic(api_key=api_key)

    # Construct the prompt
    prompt = f"""
    You are an expert technical assistant tasked with summarizing a GitHub issue discussion.
    The goal is to create a "clean" entrypoint summary that captures the current consensus, 
    open questions, decisions made, and key action items.

    CRITICAL REQUIREMENT:
    You MUST cite your sources. Every key claim, decision, or quote in your summary must be 
    linked back to the specific comment URL where it originated. 
    Use markdown links like this: [comment by username](url).
    
    Ignore simple "+1" or "me too" comments unless they indicate significant community support for a specific approach.
    Focus on the technical details and the flow of the conversation.

    Title: {issue.title}
    Author: {issue.user.login}
    State: {issue.state}
    Created At: {issue.created_at}
    
    Issue Body:
    {issue.body or "(No body)"}
    
    Comments:
    """
    
    for comment in issue.comments_list:
        prompt += f"\n--- Comment by {comment.user.login} at {comment.created_at} (URL: {comment.html_url}) ---\\n"
        prompt += f"{comment.body}\\n"

    prompt += """
    \nPlease provide a concise summary in Markdown, using an outline or nested list style, with fewer main headlines.
    Focus on being brief and to the point. Include the following consolidated sections:
    
    ### Summary of Discussion
    
    *   **Issue Overview**: A brief, one-paragraph explanation of the issue/feature request.
    *   **Key Points & Decisions**:
        *   Summarize the main arguments, technical details, and any decisions made. Cite sources!
        *   Use a nested list if appropriate for clarity.
    *   **Action Items/Next Steps**:
        *   List any remaining tasks or next steps identified. Cite sources!
        *   Use a nested list if appropriate.
    """

    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2000,
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    
    return message.content[0].text