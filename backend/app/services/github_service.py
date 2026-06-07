import httpx
from app.config import settings
from app.models.schemas import PRRequest, PRResponse

async def create_pr_for_doc_drift(pr_request: PRRequest) -> PRResponse:
    """Creates a Pull Request via GitHub API using configured credentials."""
    if settings.USE_MOCKS or not settings.GITHUB_TOKEN:
        return PRResponse(
            pr_number=42,
            pr_url=f"https://github.com/{settings.MOCK_GITHUB_REPO}/pull/42",
            head_branch=pr_request.head_branch,
            status="mock_created"
        )

    headers = {
        "Authorization": f"token {settings.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    payload = {
        "title": pr_request.title,
        "body": pr_request.body,
        "head": pr_request.head_branch,
        "base": pr_request.base_branch
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.GITHUB_API_BASE}/repos/{pr_request.repo}/pulls",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        
        return PRResponse(
            pr_number=data["number"],
            pr_url=data["html_url"],
            head_branch=pr_request.head_branch,
            status="created"
        )