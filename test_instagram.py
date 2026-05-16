import time
import requests
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
# Local upload endpoint (must be reachable from this script)
UPLOAD_ENDPOINT = "http://127.0.0.1:8000/api/upload-video"
# Public base URL for Instagram to access the video
PUBLIC_BASE = "http://103.76.103.41"

# Instagram credentials
ACCESS_TOKEN = "EAANoKFQpQSEBRUm1NaUaJqKqJ3IZCaR3zMKmY8F7NqD72iX4gZBvHt9nBABulEfVtTGpDl9flzOJOSkbWaenKyfUrMM3HeGVkzjlPMCQoZCH0le95S10MDQWWxKIt73XcRX8smbsYW6AU1ZBi2rmY1Oxn2bDRpHlxnNoCuieg6ImfgtqysoQLama6HJY"
USER_ID = "17841428515744120"

# Your local video file
LOCAL_VIDEO = "./data/test_video.mp4"

# ----------------------------------------------------------------------
# Instagram Adapter
# ----------------------------------------------------------------------
class InstagramAdapter:
    def __init__(self, config: Dict[str, str]):
        self.config = config
        self.access_token = config.get("access_token")
        self.user_id = config.get("user_id")

    def validate_credentials(self) -> bool:
        if not self.access_token or not self.user_id:
            return False
        try:
            resp = requests.get(
                f"https://graph.facebook.com/{self.user_id}",
                params={"access_token": self.access_token, "fields": "id,username"},
                timeout=8,
            )
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def post(self, post: Any) -> Dict[str, Any]:
        if not self.access_token:
            return self._error("Instagram access token not configured.", post)
        if not self.user_id:
            return self._error("Instagram user ID not configured.", post)

        if post.type == "text":
            return self._error("Text-only posts not supported.", post)
        elif post.type == "image":
            return self._post_image(post)
        elif post.type in ("reels", "video"):
            return self._post_reel(post)
        else:
            return self._error(f"Unsupported post type: {post.type}", post)

    def _post_image(self, post: Any) -> Dict[str, Any]:
        image_url = post.media_path
        if not image_url.startswith(("http://", "https://")):
            return self._error("Image post requires a public URL.", post)

        container_resp = requests.post(
            f"https://graph.facebook.com/{self.user_id}/media",
            params={"access_token": self.access_token},
            data={"image_url": image_url, "caption": post.text or ""},
            timeout=10,
        )
        if container_resp.status_code != 200:
            return self._error(f"Container creation failed: {container_resp.text}", post)

        creation_id = container_resp.json().get("id")
        print(f"  -> Image container created: {creation_id}")

        publish_resp = requests.post(
            f"https://graph.facebook.com/{self.user_id}/media_publish",
            params={"access_token": self.access_token},
            data={"creation_id": creation_id},
            timeout=10,
        )
        if publish_resp.status_code == 200:
            post_id = publish_resp.json().get("id")
            return {
                "platform": "instagram",
                "operation": "create_image_post",
                "status": "success",
                "message": f"Posted image. Post ID: {post_id}",
                "post_id": post_id,
                "post": post,
            }
        else:
            return self._error(f"Publish failed: {publish_resp.text}", post)

    def _post_reel(self, post: Any) -> Dict[str, Any]:
        media_path = post.media_path

        # If it's a local file, upload to local server
        if not media_path.startswith(("http://", "https://")):
            print("  -> Uploading local file to local server (127.0.0.1:8000)...")
            relative_url = self._upload_to_local_server(media_path)
            if not relative_url:
                return self._error("Failed to upload video to local server.", post)
            # Convert relative URL to absolute public URL
            public_url = PUBLIC_BASE + relative_url   # relative_url starts with "/video/..."
            media_path = public_url
            print(f"  -> Public URL (for Instagram): {media_path}")
            print("  -> (This URL is valid for 10 minutes)")

        # Create media container (REELS)
        container_resp = requests.post(
            f"https://graph.facebook.com/{self.user_id}/media",
            params={"access_token": self.access_token},
            data={
                "media_type": "REELS",
                "video_url": media_path,
                "caption": post.text or "",
            },
            timeout=10,
        )
        if container_resp.status_code != 200:
            return self._error(f"Container creation failed: {container_resp.text}", post)

        creation_id = container_resp.json().get("id")
        print(f"  -> Container created: {creation_id}")

        # Wait for processing (poll status)
        if not self._wait_for_processing(creation_id):
            return self._error("Video processing failed. Check format, duration, and aspect ratio (9:16).", post)

        # Publish
        publish_resp = requests.post(
            f"https://graph.facebook.com/{self.user_id}/media_publish",
            params={"access_token": self.access_token},
            data={"creation_id": creation_id},
            timeout=10,
        )
        if publish_resp.status_code == 200:
            post_id = publish_resp.json().get("id")
            return {
                "platform": "instagram",
                "operation": "create_reel",
                "status": "success",
                "message": f"Posted reel. Post ID: {post_id}",
                "post_id": post_id,
                "post": post,
            }
        else:
            return self._error(f"Publish failed: {publish_resp.text}", post)

    def _upload_to_local_server(self, local_path: str) -> Optional[str]:
        """Upload file to local server and return the relative video URL (e.g., '/video/abc123')."""
        file_path = Path(local_path)
        if not file_path.exists():
            print(f"  -> File not found: {local_path}")
            return None
        if file_path.stat().st_size > 200 * 1024 * 1024:
            print("  -> File exceeds 200 MB.")
            return None

        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f, "video/mp4")}
                resp = requests.post(UPLOAD_ENDPOINT, files=files, timeout=120)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("success"):
                        # Expecting relative path like "/video/..."
                        video_url = data.get("video_url")
                        if video_url:
                            return video_url
                    print(f"  -> Server returned error: {data}")
                    return None
                else:
                    print(f"  -> Server HTTP {resp.status_code}: {resp.text}")
                    return None
        except Exception as e:
            print(f"  -> Upload exception: {e}")
            return None

    def _wait_for_processing(self, creation_id: str, max_attempts: int = 30, delay: int = 2) -> bool:
        for _ in range(max_attempts):
            resp = requests.get(
                f"https://graph.facebook.com/{creation_id}",
                params={"access_token": self.access_token, "fields": "status_code"},
                timeout=10,
            )
            if resp.status_code != 200:
                print(f"  -> Status check HTTP error: {resp.text}")
                return False

            data = resp.json()
            if "error" in data:
                print(f"  -> API error: {data['error'].get('message', 'Unknown')}")
                return False

            status = data.get("status_code")
            print(f"  -> Processing status: {status}")

            if status == "FINISHED":
                return True
            if status == "ERROR":
                # Try to get error details
                err_resp = requests.get(
                    f"https://graph.facebook.com/{creation_id}",
                    params={"access_token": self.access_token, "fields": "status_code,error"},
                    timeout=10,
                )
                if err_resp.status_code == 200:
                    err_data = err_resp.json()
                    error_msg = err_data.get("error", {}).get("message", "No details")
                    print(f"  -> Processing ERROR: {error_msg}")
                else:
                    print(f"  -> Processing ERROR (raw data: {data})")
                return False
            if status == "EXPIRED":
                return False
            time.sleep(delay)
        return False

    def _error(self, message: str, post: Any) -> Dict[str, Any]:
        return {
            "platform": "instagram",
            "operation": "post",
            "status": "error",
            "message": message,
            "post": post,
        }


# ----------------------------------------------------------------------
# __main__
# ----------------------------------------------------------------------
if __name__ == "__main__":
    @dataclass
    class Post:
        type: str
        media_path: str
        text: str
        title: Optional[str] = None
        extra: Optional[Dict] = None

    test_post = Post(
        type="reels",
        media_path=LOCAL_VIDEO,
        text="🔥 Grid trading, Forex/Nifty500 analysis, and GOLD/BTC strategy in this short.\n\n#gridtrading #forex #nifty500 #gold #btc #trading #shorts",
        title=None,
    )

    config = {"access_token": ACCESS_TOKEN, "user_id": USER_ID}
    adapter = InstagramAdapter(config)

    print("🔍 Validating credentials...")
    if not adapter.validate_credentials():
        print("❌ Invalid credentials")
        sys.exit(1)
    print("✅ Credentials valid.\n")

    print(f"📤 Posting reel...\n   File: {test_post.media_path}\n   Caption: {test_post.text[:80]}...\n")
    result = adapter.post(test_post)

    print("\n📦 Result:")
    for k, v in result.items():
        if k != "post":
            print(f"  {k}: {v}")

    if result.get("status") == "success":
        print("\n✅ Instagram Reel posted successfully!")
    else:
        print("\n❌ Post failed. Check the error message above.")
        sys.exit(1)