# # routers/grid.py
# from fastapi import APIRouter, HTTPException
# from fastapi.responses import JSONResponse
# from pydantic import BaseModel

# router = APIRouter(tags=["grid"])

# class MT5Details(BaseModel):
#     mt5_id: str
#     name: str
#     broker: str

# @router.post("/api/submit-mt5-details")
# async def submit_mt5_details(details: MT5Details):
#     """
#     Receives the user's MT5 details for bot activation.
#     TODO: Store to database, send notification, etc.
#     """
#     # For now, just print and return success
#     print(f"MT5 Submission - ID: {details.mt5_id}, Name: {details.name}, Broker: {details.broker}")
#     # You could write to a file, DB, or send a Telegram message here.

#     return JSONResponse({
#         "success": True,
#         "message": "Your licence has been created successfully for metatrader ID{details.mt5_id}. Ready to go!"
#     })





import os
import base64
import json
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import httpx

router = APIRouter(tags=["grid"])

# GitHub configuration
GITHUB_REPO = "ranjanZ/Dalal_Street_Quants"          # your repo
FILE_PATH = "V1_user_id.json"                        # path in repo
BRANCH = "main"                                       # or "master"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
GITHUB_RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{BRANCH}/{FILE_PATH}"

# Get token from environment
TOKEN = os.environ.get("GITHUB_TOKEN")
if not TOKEN:
    raise RuntimeError("GITHUB_TOKEN environment variable not set.")

class MT5Details(BaseModel):
    mt5_id: str
    name: str
    broker: str

async def get_file_sha_and_content(client: httpx.AsyncClient) -> tuple[str, dict]:
    """Fetch the file metadata (SHA) and parsed JSON content from GitHub."""
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    # First get the file metadata to obtain SHA
    resp = await client.get(GITHUB_API_URL, headers=headers, params={"ref": BRANCH})
    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Failed to fetch file info: {resp.text}")
    data = resp.json()
    sha = data["sha"]
    # The content is base64 encoded in the API response
    content_b64 = data["content"].replace("\n", "")
    content_bytes = base64.b64decode(content_b64)
    content_json = json.loads(content_bytes)
    print(f"Fetched file  content keys: {content_json}")
    return sha, content_json

async def update_file(client: httpx.AsyncClient, sha: str, new_content: dict, commit_message: str):
    headers = {
        "Authorization": f"Bearer {TOKEN}",           # Use Bearer instead of token
        "Accept": "application/vnd.github+json",     # Latest media type
        "X-GitHub-Api-Version": "2022-11-28",        # Or "2026-03-10" if you want
    }
    new_content_str = json.dumps(new_content, indent=2)
    new_content_b64 = base64.b64encode(new_content_str.encode()).decode()
    payload = {
        "message": commit_message,
        "content": new_content_b64,
        "sha": sha,
        "branch": BRANCH
    }
    resp = await client.put(GITHUB_API_URL, headers=headers, json=payload)
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail=f"Failed to update file: {resp.text}")
    return resp.json()

@router.post("/api/submit-mt5-details")
async def submit_mt5_details(details: MT5Details):
    """
    Submits MT5 details, adds user to the GitHub-hosted JSON list.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Fetch current file
        sha, data = await get_file_sha_and_content(client)

        # 2. Validate and add new user
        users_list = data.get("users", [])
        # Optional: check if MT5 ID already exists
        if any(u.get("user_id") == details.mt5_id for u in users_list):
            raise HTTPException(status_code=400, detail=f"MT5 ID {details.mt5_id} already exists.")

        # Create new user entry (set valid_upto to 30 days from now)
        valid_upto = (datetime.utcnow() + timedelta(days=30)).strftime("%d-%m-%Y")
        new_user = {
            "user_id": details.mt5_id,
            "server_name": "unknown",   # you can ask the user if needed
            "broker": details.broker.lower(),
            "name": details.name,
            "valid_upto": valid_upto
        }
        users_list.append(new_user)
        data["users"] = users_list

        print("*********************:",data)
        # 3. Commit the changes
        commit_msg = f"Add user {details.mt5_id} ({details.name})"
        await update_file(client, sha, data, commit_msg)

    return JSONResponse({
        "success": True,
        "message": f"Your licence has been created successfully for MetaTrader ID {details.mt5_id}. Ready to go!"
    })


# Add this at the bottom of routers/grid.py (outside the router definition)

if __name__ == "__main__":
    import asyncio
    import sys

    async def test_endpoint():
        # Create a test user with a unique ID to avoid "already exists"
        import time
        unique_id = f"TEST_{int(time.time())}"
        test_details = MT5Details(
            mt5_id=unique_id,
            name="Test User",
            broker="MetaQuotes-Demo"
        )
        print(f"Testing with user: {test_details}")
        try:
            response = await submit_mt5_details(test_details)
            print("✅ Success:", response.body.decode() if hasattr(response, 'body') else response)
        except HTTPException as e:
            print(f"❌ HTTP error: status={e.status_code}, detail={e.detail}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")


    asyncio.run(test_endpoint())