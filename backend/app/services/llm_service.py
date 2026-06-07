import time
import httpx
from app.config import settings
from app.models.schemas import DriftResult

async def generate_suggested_rewrite(drift_result: DriftResult) -> str:
    """Uses the LLM to rewrite out-of-date documentation."""
    if settings.USE_MOCKS or not settings.LLM_API_KEY:
        time.sleep(settings.MOCK_LLM_DELAY)
        return f"Mock updated documentation for section: {drift_result.section_heading}"

    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = (
        f"Update the documentation. Original content:\n{drift_result.original_content}\n\n"
        f"Changed symbols: {', '.join(drift_result.changed_symbols)}"
    )
    
    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": "You are an expert technical writer and code reviewer."},
            {"role": "user", "content": prompt}
        ]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.LLM_API_BASE}/chat/completions",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]