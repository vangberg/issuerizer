import os
import anthropic
from typing import Optional
from issuerizer.github import Issue

def get_summary(issue: Issue, readme_content: Optional[str] = None, verbose: bool = False) -> str:
    """
    Generates a summary of the provided GitHub issue using the Anthropic API.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")

    client = anthropic.Anthropic(api_key=api_key)

    # Construct the prompt
    # Follows Anthropic's long context guidelines: Context first (in XML), then instructions.
    prompt = "<context>\n"
    
    prompt += "<issue>\n"
    prompt += f"<title>{issue.title}</title>\n"
    prompt += f"<author>{issue.user.login}</author>\n"
    prompt += f"<state>{issue.state}</state>\n"
    prompt += f"<created_at>{issue.created_at}</created_at>\n"
    prompt += f"<body>\n{issue.body or '(No body)'}\n</body>\n"
    prompt += "</issue>\n"

    if readme_content:
        prompt += f"<project_readme>\n{readme_content[:10000]}... (truncated if too long)\n</project_readme>\n"

    if issue.comments_list:
        prompt += "<comments>\n"
        for comment in issue.comments_list:
            prompt += f"<comment>\n"
            prompt += f"<author>{comment.user.login}</author>\n"
            prompt += f"<date>{comment.created_at}</date>\n"
            prompt += f"<url>{comment.html_url}</url>\n"
            prompt += f"<body>\n{comment.body}\n</body>\n"
            prompt += "</comment>\n"
        prompt += "</comments>\n"

    if issue.events_list:
        prompt += "<events>\n"
        for event in issue.events_list:
            actor_login = event.actor.login if event.actor else "Unknown"
            prompt += f"<event type='{event.event}' actor='{actor_login}' date='{event.created_at}'"
            if event.commit_id:
                 prompt += f" commit_id='{event.commit_id}'"
            prompt += ">\n"
            if event.source and event.source.issue:
                linked = event.source.issue
                prompt += f"  <linked_issue state='{linked.state}' number='{linked.number}'>\n"
                prompt += f"    <title>{linked.title}</title>\n"
                prompt += f"    <url>{linked.html_url}</url>\n"
                if linked.body:
                    prompt += f"    <body>{linked.body[:200]}...</body>\n"
                prompt += "  </linked_issue>\n"
            prompt += "</event>\n"
        prompt += "</events>\n"

    prompt += "</context>\n\n"

    prompt += """
    You are an expert technical editor summarizing a GitHub issue discussion based on the context provided above.
    Produce a succinct, academic-style review of the conversation.

    CRITICAL REQUIREMENTS:
    1. **Style**: EXTREMELY concise, dense, and objective. Avoid ALL fluff. Be telegraphic.
    2. **Citations**: Use inline markdown links for every claim using incrementing numbers, e.g., "The proposed API changes [(1)](url) were debated, with concerns raised about backward compatibility [(2)](url), [(3)](url)."
    3. **Content**: Capture the core problem, proposed solutions, consensus (or lack thereof), and next steps.
    4. **Focus**: Do NOT begin by stating "Issue requests..." or summarizing the title/body if it's generic. Assume the reader knows the title. START IMMEDIATELY with the *discussion*, *technical debate*, or *proposed solutions*.

    Produce the summary in Markdown. Structure it as follows:

    ### Executive Summary
    (Maximum 2-3 sentences. Ultra-dense summary of the issue, key debates, and current status, heavily cited.)

    ### Key Technical Points
    *   (Short, single-line bullet points for major technical arguments or decisions. Use inline citations profusely.)

    ### Action Items
    *   (Concise list of next steps or open tasks, with citations.)
    """

    if verbose:
        print("\n--- LLM Prompt ---")
        print(prompt)
        print("------------------\n")

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