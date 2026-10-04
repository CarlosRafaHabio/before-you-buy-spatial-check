#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(os.environ.get("TBP_DATA_DIR", Path.home() / "workspace" / "projects" / "trust-boundary-probe"))
LOG = ROOT / "events.jsonl"
ROOT.mkdir(parents=True, exist_ok=True)

PAYLOAD = {
    "case_id": "TBP-001",
    "revision": 1,
    "payload": {
        "room_width_mm": "3000",
        "room_depth_mm": "4000",
        "item_width_mm": "1000",
        "item_depth_mm": "2000",
        "position_x_mm": "500",
        "position_y_mm": "500",
    },
}

HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trust Boundary Probe</title>
<style>
body{font-family:system-ui,sans-serif;max-width:760px;margin:40px auto;padding:0 20px}
pre{background:#f5f5f5;padding:16px;border-radius:8px;overflow:auto}
button{font-size:18px;padding:12px 18px;cursor:pointer}
#status{margin-top:16px}
</style>
</head>
<body>
<h1>Capafy Trust Boundary Probe</h1>
<p>This page records a deterministic test event. It does not create Spatial Check authority.</p>
<pre id="payload"></pre>
<button id="approve">Approve X</button>
<div id="status"></div>
<script>
const payload = %PAYLOAD%;
document.querySelector("#payload").textContent = JSON.stringify(payload, null, 2);
document.querySelector("#approve").onclick = async () => {
  const response = await fetch("./api/events", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      action: "approve_test_payload",
      payload: payload
    })
  });
  document.querySelector("#status").textContent =
    response.ok ? "Event recorded." : "Event failed.";
};
</script>
</body>
</html>
""".replace("%PAYLOAD%", json.dumps(PAYLOAD))


class Handler(BaseHTTPRequestHandler):
    def send_text(self, status, body, content_type="text/plain; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/" or self.path == "":
            self.send_text(200, HTML, "text/html; charset=utf-8")
            return
        if self.path == "/api/payload":
            self.send_text(200, json.dumps(PAYLOAD), "application/json; charset=utf-8")
            return
        self.send_text(404, "not found")

    def do_POST(self):
        if self.path != "/api/events":
            self.send_text(404, "not found")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            event = json.loads(raw)
        except Exception:
            self.send_text(400, "invalid json")
            return

        event["server_ts"] = datetime.now(timezone.utc).isoformat()
        with LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")

        self.send_text(200, "ok")


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 4200), Handler).serve_forever()
