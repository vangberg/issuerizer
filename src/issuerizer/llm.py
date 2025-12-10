import os
import anthropic
from typing import Optional
from issuerizer.github import Issue

def get_summary(issue: Issue, readme_content: Optional[str] = None) -> str:
    """
    Generates a summary of the provided GitHub issue using the Anthropic API.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")

    client = anthropic.Anthropic(api_key=api_key)

    # Construct the prompt
    prompt = f"""
    You are an expert technical editor summarizing a GitHub issue discussion.
    Produce a succinct, academic-style review of the conversation.

    CRITICAL REQUIREMENTS:
    1. **Style**: EXTREMELY concise, dense, and objective. Avoid ALL fluff. Be telegraphic.
    2. **Citations**: Use inline markdown links for every claim, e.g., "The proposed API changes [user1](url) were debated, with concerns raised about backward compatibility [user2](url), [user3](url)."
    3. **Content**: Capture the core problem, proposed solutions, consensus (or lack thereof), and next steps.

    Title: {issue.title}
    Author: {issue.user.login}
    State: {issue.state}
    Created At: {issue.created_at}
    
    Issue Body:
    {issue.body or "(No body)"}
    """

    if readme_content:
        prompt += f"\n\nProject README:\n{readme_content[:10000]}... (truncated if too long)\n"

    prompt += """
    \nComments:
    """
    
    for comment in issue.comments_list:
        prompt += f"\n--- Comment by {comment.user.login} at {comment.created_at} (URL: {comment.html_url}) ---\\n"
        prompt += f"{comment.body}\\n"

    prompt += """
    \nProduce the summary in Markdown. Structure it as follows:

    ### Executive Summary
    (Maximum 2-3 sentences. Ultra-dense summary of the issue, key debates, and current status, heavily cited.)

    ### Key Technical Points
    *   (Short, single-line bullet points for major technical arguments or decisions. Use inline citations profusely.)

    ### Action Items
    *   (Concise list of next steps or open tasks, with citations.)
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