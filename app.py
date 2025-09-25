from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path
from http import HTTPStatus
import subprocess
import datetime
import logging
import requests
import json
import os

# ────────────────────────────────────────────────────────────────────
# Paths & config
# ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.resolve()
CONFIG_PATH = BASE_DIR / "config.json"

def load_config() -> dict:
    """Load config.json if present, then apply env overrides."""
    cfg = {
        "moonraker": {
            "url": "http://192.168.0.11",
            "api_key": "19ac2a24eb354f8eb494665f0459d770"
        },
        "superslicer": {
            "executable": "/Applications/SuperSlicer.app/Contents/MacOS/SuperSlicer",
            "profile_ini": str(BASE_DIR / "config_LD2.ini")
        },
        "paths": {
            "gcodes_dir": "gcodes",
            "temp_stl": "temp.stl"
        },
        "app": {"debug": True}
    }
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r") as f:
                user_cfg = json.load(f)
            for k, v in user_cfg.items():
                if isinstance(v, dict) and k in cfg:
                    cfg[k].update(v)
                else:
                    cfg[k] = v
        except json.JSONDecodeError:
            print("WARN: config.json is not valid JSON; using defaults")

    # Env overrides
    cfg["moonraker"]["url"] = os.getenv("MOONRAKER_URL", cfg["moonraker"]["url"])
    cfg["moonraker"]["api_key"] = os.getenv("MOONRAKER_API_KEY", cfg["moonraker"]["api_key"])
    cfg["superslicer"]["executable"] = os.getenv("SUPERSLICER_EXECUTABLE", cfg["superslicer"]["executable"])
    cfg["superslicer"]["profile_ini"] = os.getenv("SUPERSLICER_PROFILE", cfg["superslicer"]["profile_ini"])
    return cfg

CFG = load_config()

GCODE_DIR = (BASE_DIR / CFG["paths"]["gcodes_dir"]).resolve()
GCODE_DIR.mkdir(exist_ok=True)
TEMP_STL_PATH = (BASE_DIR / CFG["paths"]["temp_stl"]).resolve()

# ────────────────────────────────────────────────────────────────────
# Flask app
# ────────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder="static", static_url_path="/static")

@app.get("/")
def index():
    return send_from_directory(str(BASE_DIR), "index.html")

@app.get("/gcodes/<path:fname>")
def serve_gcode(fname):
    return send_from_directory(str(GCODE_DIR), fname, as_attachment=True)

# ────────────────────────────────────────────────────────────────────
# Logging
# ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("piy")

def ok(payload: dict, status: int = HTTPStatus.OK):
    return jsonify(payload), status

def fail(message: str, status: int = HTTPStatus.BAD_REQUEST, **extra):
    body = {"error": message}
    if extra:
        body.update(extra)
    return jsonify(body), status

# ────────────────────────────────────────────────────────────────────
# Core helpers
# ────────────────────────────────────────────────────────────────────
def run_superslicer(stl_path: Path, out_path: Path, layer: str, infill: str) -> tuple[bool, str]:
    """Run SuperSlicer on given STL to produce G-code."""
    exe = CFG["superslicer"]["executable"]
    profile = CFG["superslicer"]["profile_ini"]

    if not Path(exe).exists():
        return False, f"SuperSlicer executable not found at: {exe}"
    if not Path(profile).exists():
        return False, f"SuperSlicer profile not found at: {profile}"

    cmd = [
        exe,
        "--export-gcode",
        "--load", profile,
        "--layer-height", str(layer),
        "--fill-density", f"{infill}%",
        "-o", str(out_path),
        str(stl_path),
    ]
    logger.info("Running slicer: %s", " ".join(cmd))
    run = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=os.environ,
        cwd=str(BASE_DIR),
        check=False,
    )
    if run.returncode != 0 or not out_path.exists():
        return False, (run.stderr or "Unknown slicer error").strip()
    return True, (run.stdout or "").strip()

def upload_and_print_moonraker(gcode_path: Path) -> tuple[bool, str]:
    url = CFG["moonraker"]["url"].rstrip("/")
    api_key = CFG["moonraker"]["api_key"]
    headers = {"X-Api-Key": api_key} if api_key else {}

    if not gcode_path.exists():
        return False, f"G-code not found: {gcode_path}"

    filename = gcode_path.name

    try:
        with open(gcode_path, "rb") as fh:
            files = {"file": (filename, fh, "application/octet-stream")}
            resp = requests.post(
                f"{url}/server/files/upload",
                headers=headers,
                files=files,
                params={"root": "gcodes"},
                timeout=30,
            )
        resp.raise_for_status()
    except requests.RequestException as e:
        return False, f"Upload error: {e}"

    candidates = [filename, f"gcodes/{filename}"]
    for cand in candidates:
        try:
            pr = requests.post(
                f"{url}/printer/print/start",
                headers=headers,
                json={"filename": cand},
                timeout=10,
            )
            pr.raise_for_status()
            logger.info("Print started with filename='%s'.", cand)
            return True, f"Print started ({cand})"
        except requests.RequestException as e:
            logger.warning("Start failed for '%s': %s", cand, e)

    return False, f"Unable to start print; tried {candidates}"

# ────────────────────────────────────────────────────────────────────
# Routes
# ────────────────────────────────────────────────────────────────────
@app.post("/slice_and_print")
def slice_and_print():
    stl = request.files.get("stlFile")
    layer = request.form.get("layerHeight")
    infill = request.form.get("infill")
    if not stl or not layer or not infill:
        return fail("Missing stlFile, layerHeight, or infill")

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"sliced_{ts}.gcode"
    out_path = BASE_DIR / out_name

    TEMP_STL_PATH.write_bytes(b"")
    stl.save(TEMP_STL_PATH)

    logger.info("Slicing → %s", out_path)
    try:
        sliced, msg = run_superslicer(TEMP_STL_PATH, out_path, layer, infill)
    finally:
        try:
            TEMP_STL_PATH.unlink(missing_ok=True)
        except Exception:
            logger.warning("Temp STL cleanup failed", exc_info=True)

    if not sliced:
        return fail("Slicing failed", HTTPStatus.INTERNAL_SERVER_ERROR, details=msg)
    if not out_path.exists():
        return fail("Slicing produced no output", HTTPStatus.INTERNAL_SERVER_ERROR)

    started, pmsg = upload_and_print_moonraker(out_path)
    if not started:
        return fail("Print start failed", HTTPStatus.BAD_GATEWAY, details=pmsg)

    return ok({"message": "Print started", "gcode": out_name})

@app.post("/api/slice")
def api_slice_only():
    stl = request.files.get("stlFile")
    layer = request.form.get("layerHeight")
    infill = request.form.get("infill")
    if not stl or not layer or not infill:
        return fail("Missing stlFile, layerHeight, or infill")

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"sliced_{ts}.gcode"
    out_path = GCODE_DIR / out_name
    temp_stl = BASE_DIR / "temp_slice_input.stl"

    temp_stl.write_bytes(b"")
    stl.save(temp_stl)

    try:
        sliced, msg = run_superslicer(temp_stl, out_path, layer, infill)
        if not sliced or not out_path.exists():
            return fail("Slicing failed", HTTPStatus.INTERNAL_SERVER_ERROR, stderr=msg)
        return ok({
            "message": "Sliced OK",
            "filename": out_name,
            "download_url": f"/gcodes/{out_name}"
        })
    finally:
        try:
            temp_stl.unlink(missing_ok=True)
        except Exception:
            logger.warning("Temp STL cleanup failed", exc_info=True)

if __name__ == "__main__":
    app.run(debug=bool(CFG["app"].get("debug", True)))