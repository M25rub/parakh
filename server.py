"""
OWNER: Person 1. Parakh web server.
Serves the pages in web/ and the API those pages call.
Run locally:  uvicorn server:app --reload     then open http://127.0.0.1:8000
"""
import json
import queue
import threading
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from parakh import service  # noqa: E402
from parakh.checks import extract_links  # noqa: E402
from parakh.parse_email import parse_raw_email  # noqa: E402
from parakh.schemas import EmailInput  # noqa: E402

WEB = Path(__file__).parent / "web"
app = FastAPI(title="Parakh")
app.mount("/static", StaticFiles(directory=WEB), name="static")


def _stream(fn, *args) -> StreamingResponse:
    """Run a Parakh function in the background and stream every step to the page.
    The page receives events named 'trace' (one per step), then 'result' or 'error'."""
    q: queue.Queue = queue.Queue()

    def worker():
        try:
            result = fn(*args, on_event=lambda ev: q.put(("trace", ev.model_dump(mode="json"))))
            q.put(("result", result.model_dump(mode="json")))
        except Exception as e:  # never crash the page
            q.put(("error", {"message": str(e)}))
        q.put(None)

    threading.Thread(target=worker, daemon=True).start()

    def events():
        while (item := q.get()) is not None:
            kind, data = item
            yield f"event: {kind}\ndata: {json.dumps(data)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


# ---------- API ----------
@app.get("/api/health")
def health():
    return {"ok": True, "mock": service.is_mock()}


@app.get("/api/scan")
def scan():
    """Scan the connected inbox (live stream)."""
    return _stream(service.scan_inbox, 10)


@app.post("/api/check")
async def check(sender: str = Form(""), subject: str = Form(""), body: str = Form(""),
                headers: str = Form(""), eml: Optional[UploadFile] = File(None)):
    """Check ONE email: either an uploaded .eml file or pasted fields (live stream)."""
    if eml is not None and eml.filename:
        raw = (await eml.read()).decode("utf-8", errors="replace")
        email = parse_raw_email(raw, email_id=eml.filename)
    else:
        email = EmailInput(email_id="pasted-1", sender=sender, subject=subject, body_text=body,
                           raw_headers=headers, links=extract_links(body))
    return _stream(service.check_email, email)


# ---------- Pages ----------
PAGES = {"/": "index.html", "/scan": "scan.html", "/check": "check.html", "/privacy": "privacy.html"}

for route, filename in PAGES.items():
    def page(filename=filename):
        path = WEB / filename
        return FileResponse(path) if path.exists() else JSONResponse(
            {"error": f"web/{filename} not created yet"}, status_code=404)
    app.add_api_route(route, page, methods=["GET"], include_in_schema=False)
