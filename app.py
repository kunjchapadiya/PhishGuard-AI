"""
app.py - High-Performance Backend REST API for PhishGuard AI Chrome Extension

Handles URL threat classification requests from the PhishGuard AI Chrome extension,
executing real-time feature extraction and Random Forest inference.
"""

import os
import time
import math
import zlib
import struct
import logging
from flask import Flask, request, jsonify
from predictor import predictor_instance

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"
)
logger = logging.getLogger("PhishGuardAI.API")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False
START_TIME = time.time()


def ensure_extension_icons():
    """Generates Chrome Extension PNG icons automatically if they don't exist yet."""
    icons_dir = os.path.join(os.path.dirname(__file__), "extension", "icons")
    os.makedirs(icons_dir, exist_ok=True)

    def create_shield_png(size, filepath):
        width = size
        height = size
        raw_pixels = bytearray()
        cx = width / 2.0
        cy = height / 2.0
        radius = (width / 2.0) * 0.85

        for y in range(height):
            raw_pixels.append(0)
            for x in range(width):
                dx = (x - cx) / radius
                dy = (y - cy) / radius
                dist = math.sqrt(dx * dx + dy * dy)
                if dist <= 0.95:
                    ratio = (x + y) / (width + height)
                    r = int(6 + ratio * 20)
                    g = int(182 - ratio * 40)
                    b = int(212 + ratio * 30)
                    alpha = 255
                    if dist > 0.82:
                        r = min(255, r + 40)
                        g = min(255, g + 50)
                        b = 255
                else:
                    r, g, b, alpha = 0, 0, 0, 0
                raw_pixels.extend([r, g, b, alpha])

        compressed = zlib.compress(bytes(raw_pixels), 9)

        def make_chunk(chunk_type, data):
            length = len(data)
            crc = zlib.crc32(chunk_type + data) & 0xffffffff
            return struct.pack(">I", length) + chunk_type + data + struct.pack(">I", crc)

        png_header = b"\x89PNG\r\n\x1a\n"
        ihdr_chunk = make_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        idat_chunk = make_chunk(b"IDAT", compressed)
        iend_chunk = make_chunk(b"IEND", b"")

        with open(filepath, "wb") as f:
            f.write(png_header + ihdr_chunk + idat_chunk + iend_chunk)

    for sz in [16, 48, 128]:
        p = os.path.join(icons_dir, f"icon{sz}.png")
        if not os.path.exists(p):
            try:
                create_shield_png(sz, p)
            except Exception:
                pass


ensure_extension_icons()


@app.before_request
def start_timer():
    request.start_time = time.time()


@app.after_request
def add_cors_and_timing_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"

    if hasattr(request, "start_time"):
        elapsed_ms = round((time.time() - request.start_time) * 1000, 2)
        response.headers["X-Process-Time-Ms"] = str(elapsed_ms)

    return response


# ---------------------------------------------------------
# Root & Health Endpoints
# ---------------------------------------------------------
@app.route("/", methods=["GET"])
def index():
    """API Root endpoint for the Chrome Extension."""
    model_info = predictor_instance.get_info()
    return jsonify({
        "status": "online",
        "service": "PhishGuard AI Backend for Chrome Extension",
        "version": "1.0.0",
        "model_loaded": model_info["model_ready"],
        "model_type": model_info["model_type"],
        "endpoints": {
            "predict": "POST /predict",
            "health": "GET /health",
            "model_info": "GET /model-info"
        }
    }), 200


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint to monitor API uptime and model readiness."""
    uptime_seconds = round(time.time() - START_TIME, 2)
    model_info = predictor_instance.get_info()

    return jsonify({
        "status": "healthy",
        "service": "PhishGuard AI Backend API",
        "version": "1.0.0",
        "model_loaded": model_info["model_ready"],
        "model_type": model_info["model_type"],
        "uptime_seconds": uptime_seconds,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }), 200


@app.route("/model-info", methods=["GET"])
@app.route("/api/v1/model-info", methods=["GET"])
def model_information():
    """Returns technical metadata, feature definitions, and model evaluation metrics."""
    return jsonify({
        "success": True,
        "model_info": predictor_instance.get_info()
    }), 200


@app.route("/confusion-matrix", methods=["GET"])
@app.route("/api/v1/confusion-matrix", methods=["GET"])
def confusion_matrix_endpoint():
    """Returns the confusion matrix and evaluation metrics."""
    info = predictor_instance.get_info()
    metrics = info.get("metrics", {})
    return jsonify({
        "success": True,
        "model_type": info.get("model_type"),
        "accuracy": metrics.get("accuracy"),
        "f1_score": metrics.get("f1_score_weighted"),
        "confusion_matrix": metrics.get("confusion_matrix"),
        "breakdown": metrics.get("confusion_matrix_breakdown")
    }), 200


# ---------------------------------------------------------
# Prediction Endpoint for Chrome Extension
# ---------------------------------------------------------
@app.route("/predict", methods=["POST", "OPTIONS"])
@app.route("/api/v1/predict", methods=["POST", "OPTIONS"])
def predict_single_url():
    """
    Main prediction endpoint consumed by Chrome Extension.

    JSON body: { "url": "https://..." }
    """
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({
            "success": False,
            "error": "Invalid request body. Expected JSON object with 'url' field."
        }), 400

    url = data.get("url")
    if not url or not isinstance(url, str) or not url.strip():
        return jsonify({
            "success": False,
            "error": "Missing or empty 'url' parameter."
        }), 400

    try:
        prediction = predictor_instance.predict_single(url.strip())
        latency_ms = round((time.time() - request.start_time) * 1000, 2)

        return jsonify({
            "success": True,
            "data": prediction,
            "latency_ms": latency_ms
        }), 200

    except Exception as e:
        logger.error(f"Prediction error on URL '{url}': {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal prediction processing error",
            "details": str(e)
        }), 500


# ---------------------------------------------------------
# Error Handlers
# ---------------------------------------------------------
@app.errorhandler(404)
def resource_not_found(e):
    return jsonify({
        "success": False,
        "error": "Endpoint not found",
        "status_code": 404
    }), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({
        "success": False,
        "error": "HTTP method not allowed",
        "status_code": 405
    }), 405


@app.errorhandler(500)
def internal_server_error(e):
    return jsonify({
        "success": False,
        "error": "Internal server error",
        "status_code": 500
    }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "True").lower() == "true"
    backend_url = os.environ.get("BACKEND_API", f"http://127.0.0.1:{port}")
    print(f"Starting PhishGuard AI Backend on {backend_url}")
    app.run(host="0.0.0.0", port=port, debug=debug)
