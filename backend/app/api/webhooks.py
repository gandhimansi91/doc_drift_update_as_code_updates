import hmac
import hashlib
from fastapi import APIRouter, Request, HTTPException, Header
from app.config import settings

router = APIRouter()

@router.post("/github")
async def handle_github_webhook(request: Request, x_hub_signature_256: str = Header(None)):
    """Receives Git push webhooks to trigger doc drift updates."""
    payload = await request.body()
    
    # Verify the webhook signature against our WEBHOOK_SECRET
    if settings.WEBHOOK_SECRET and not settings.USE_MOCKS:
        if not x_hub_signature_256:
            raise HTTPException(status_code=400, detail="Missing signature")
            
        mac = hmac.new(
            settings.WEBHOOK_SECRET.encode(),
            msg=payload,
            digestmod=hashlib.sha256
        )
        expected_signature = "sha256=" + mac.hexdigest()
        
        if not hmac.compare_digest(expected_signature, x_hub_signature_256):
            raise HTTPException(status_code=403, detail="Invalid webhook signature")
            
    event_type = request.headers.get("X-GitHub-Event")
    data = await request.json()
    
    # Further processing to trigger doc drift analysis
    # e.g., if event_type == "push", kick off AnalysisJob...
    
    return {"status": "accepted", "event": event_type}