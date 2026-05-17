# Dalal Street Quants

**Algorithmic Trading Strategies, Quant Research, and Temporary Video Sharing Platform**

Dalal Street Quants is a community-driven platform for systematic traders. It provides educational content, tools like a Nifty 500 performance report generator, grid trading setup instructions, broker partner codes, and a temporary video upload feature (videos auto-delete after 10 minutes). Built with FastAPI and a modular backend, it’s designed to scale and be easily maintainable.

---

## Features

- 📊 **Quant Edge** – Information on algorithmic trading, quantitative research, and systematic strategies.
- 📈 **Nifty 500 Report** – Paste JSON performance data and receive a parsed summary with net returns.
- 🤖 **Grid Trading Setup** – Step‑by‑step guide for MT5 Expert Advisor installation.
- 🤝 **Partners & Referral Codes** – Broker account links with partner codes (Vantage, Roboforex, XM).
- 🎥 **Temporary Video Sharing** – Upload videos (max 200 MB) that are automatically deleted after **10 minutes**. Perfect for quick sharing.
- 🌐 **Community Links** – Telegram, YouTube, GitHub, Instagram.

---

## Tech Stack

- **Backend:** Python 3.10+, FastAPI, Uvicorn
- **Frontend:** HTML5, Bootstrap 5, vanilla JavaScript
- **Scheduling:** APScheduler (for automatic video cleanup)
- **File Storage:** Local filesystem (`temp_videos/`)

---

## Project Structure (Modular)


dalal-street-quants/
├── main.py # App creation, lifespan, static files, router includes
├── routers/
│ ├── init.py
│ ├── video.py # Video upload, list, serve, delete, cleanup
│ ├── nifty500.py # Nifty 500 JSON report endpoint
│ ├── info.py # (optional) Info tab backend (currently minimal)
│ └── partners.py # (optional) Partners tab backend (currently minimal)
├── templates/
│ └── index.html # Single‑page application template
├── static/ # Static assets (CSS, JS, images) – auto‑created
├── temp_videos/ # Temporary video upload directory – auto‑created
└── requirements.txt # Python dependencies

text

The backend is split into separate FastAPI `APIRouter` modules for each feature, making the codebase easy to navigate and extend.

---

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ranjanZ/dalal-street-quants.git
   cd dalal-street-quants
Create a virtual environment (recommended):

bash
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
Install dependencies:

bash
pip install -r requirements.txt
Ensure required directories exist (they will be created automatically on first run, but you can also create them manually):

bash
mkdir -p templates static temp_videos
Running the Application
Start the FastAPI server with Uvicorn:

bash
python main.py
The server will start at http://0.0.0.0:8000. For development with auto‑reload:

bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
Then open your browser and go to http://localhost:8000.

API Endpoints
Method	Endpoint	Description
GET	/	Serve the main HTML page
POST	/api/upload-video	Upload a video file (multipart/form‑data)
GET	/api/videos	List all currently active (non‑expired) videos
GET	/video/{file_id}	Stream a video file (if not expired)
DELETE	/api/delete-video/{id}	Manually delete a video before expiration
POST	/api/nifty500-report	Accept JSON with performance data and return a summary
Video Upload Limits
Max file size: 200 MB

Allowed MIME types: video/mp4, video/quicktime, video/x-msvideo, video/x-matroska, video/webm, video/mpeg

Expiration: Videos are automatically deleted 10 minutes after upload by a background scheduler (runs every 60 seconds). Expired videos are also cleaned on server startup.

Configuration
The following constants can be adjusted in routers/video.py and main.py:

MAX_FILE_SIZE: maximum allowed upload size (default 200 MB)

ALLOWED_MIME_TYPES: set of accepted video MIME types

timedelta(minutes=10): lifetime of uploaded videos

Scheduler interval: currently 60 seconds (IntervalTrigger(seconds=60) in main.py)

Contributing
Contributions are welcome! Please follow these steps:

Fork the repository.

Create a feature branch: git checkout -b feature/my-new-feature

Commit your changes: git commit -am 'Add some feature'

Push to the branch: git push origin feature/my-new-feature

Open a Pull Request.

For major changes, please open an issue first to discuss what you’d like to change.

License
This project is licensed under the MIT License – see the LICENSE file for details.

