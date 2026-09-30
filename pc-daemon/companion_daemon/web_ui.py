from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="Companion Link")


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Companion Link</title>
        <style>
            body { font-family: system-ui, sans-serif; max-width: 600px;
                   margin: 60px auto; padding: 0 20px; color: #1a1a1a; }
            h1 { font-size: 1.5rem; }
            .status { padding: 12px 16px; border-radius: 8px;
                       background: #e8f5e9; color: #2e7d32; display: inline-block; }
        </style>
    </head>
    <body>
        <h1>Companion Link</h1>
        <div class="status">Daemon running</div>
        <p>Pairing and device management will appear here.</p>
    </body>
    </html>
    """


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}