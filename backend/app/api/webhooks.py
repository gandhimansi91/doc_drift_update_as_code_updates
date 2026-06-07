import hmac
import hashlib
from fastapi import APIRouter, Request, HTTPException, Header, BackgroundTasks
from app.config import settings
from app.jobs.manager import create_job, run_analysis

router = APIRouter()

@router.post("/github")
async def handle_github_webhook(request: Request, background_tasks: BackgroundTasks, x_hub_signature_256: str = Header(None)):
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

    if event_type == "push":
        try:
            repo_name = data["repository"]["full_name"]
            commit_sha = data["after"]
        except KeyError as e:
            raise HTTPException(status_code=400, detail=f"Missing expected key in push event payload: {e}")

        # Create a job to track the analysis
        job = create_job(repo=repo_name, commit_sha=commit_sha)

        # Schedule the long-running analysis to run in the background
        background_tasks.add_task(run_analysis, job.job_id)

        # Immediately return the job details as requested
        return {"job_id": job.job_id, "status": job.status.value, "commit": job.commit_sha[:7]}

    return {"status": "unhandled_event", "event": event_type}