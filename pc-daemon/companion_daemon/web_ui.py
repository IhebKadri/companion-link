from __future__ import annotations

import html

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

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
            .code { font-size: 2.5rem; letter-spacing: 0.3em; font-weight: 600;
                     margin: 20px 0; }
            button { padding: 10px 20px; font-size: 1rem; cursor: pointer; }
        </style>
    </head>
    <body>
        <h1>Companion Link</h1>
        <div class="status">Daemon running</div>
        <p><button onclick="startPairing()">Pair a new device</button></p>
        <div id="pairing-area"></div>

        <script>
        async function startPairing() {
            const res = await fetch('/pairing/start', { method: 'POST' });
            const data = await res.json();

            const area = document.getElementById('pairing-area');
            area.replaceChildren();

            const codeDiv = document.createElement('div');
            codeDiv.className = 'code';
            codeDiv.textContent = data.code;

            const waitingP = document.createElement('p');
            waitingP.textContent = 'Waiting for device...';

            area.append(codeDiv, waitingP);
            pollStatus();
        }

        async function pollStatus() {
            const res = await fetch('/pairing/status');
            const data = await res.json();
            const area = document.getElementById('pairing-area');

            if (data.paired_device) {
                area.replaceChildren();
                const p = document.createElement('p');
                p.textContent = `Paired with ${data.paired_device.device_name}`;
                area.append(p);
            } else {
                setTimeout(pollStatus, 1500);
            }
        }
        </script>
    </body>
    </html>
    """


@app.post("/pairing/start")
async def start_pairing() -> JSONResponse:
    result = await app.state.pairing_manager.start_session()
    return JSONResponse({"code": result.code, "expires_at": result.expires_at})


@app.get("/pairing/status")
async def pairing_status() -> JSONResponse:
    device = app.state.pairing_manager.get_last_paired_device()
    return JSONResponse({
        "paired_device": {"device_name": html.escape(device.device_name)} if device else None
    })


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}