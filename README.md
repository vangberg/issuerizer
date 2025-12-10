# Issuerizer

Issuerizer takes a GitHub issue and creates a summary, which can be used as the body of the
issue itself. The summary serves as the entrypoint to the issue, and can contain quotes and
direct links to comments. Since the summary is intended as the body of the issue, all user-
generated content must be posted as comments, and the initial issue should be created with
an empty body.

## Authentication

The tool requires a GitHub token to access the API.

**Local Development (using GitHub CLI):**
If you have the `gh` CLI installed and are authenticated, you can easily export your token:

```bash
export GITHUB_TOKEN=$(gh auth token)
```

**Environment Variable:**
Alternatively, set the variable manually in your shell or `.env` file:

```bash
export GITHUB_TOKEN=ghp_...
```

## GitHub Actions Integration

You can easily use `issuerizer` in your GitHub Actions workflows to automatically summarize issues.

### Example Workflow

Create a file like `.github/workflows/summarize_issue.yml`:

```yaml
name: Auto-Summarize Issue
on:
  issues:
    types: [opened, edited, labeled]
  issue_comment:
    types: [created, edited, deleted]

jobs:
  summarize:
    runs-on: ubuntu-latest
    if: contains(github.event.issue.labels.*.name, 'summarize')
    permissions:
      issues: write
    steps:
      - name: Run Issuerizer
        uses: harryvangberg/issuerizer@main
        with:
          # Dynamically get the issue number from the event
          issue-query: "${{ github.repository }}#${{ github.event.issue.number }}"
          update: "true"
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

## Usage

You can use the CLI to summarize an issue by providing its URL or shorthand:

```bash
# Using a full URL
issuerizer https://github.com/python/cpython/issues/1

# Using shorthand (owner/repo#number)
issuerizer python/cpython#1
```

### Updating GitHub Issue Body

You can update the GitHub issue's body directly with the generated summary using the `--update` (or `-u`) flag. This will replace the existing issue body with the LLM-generated summary without further confirmation.

**Warning:** This action is irreversible without manually restoring the old content.
**Requires:** Your `GITHUB_TOKEN` must have write permissions for issues in the target repository.

```bash
# Update issue with summary
issuerizer --update https://github.com/your_org/your_repo/issues/123

# Or with shorthand
issuerizer -u your_org/your_repo#123
```

