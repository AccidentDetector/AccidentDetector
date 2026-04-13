# AccidentDetector

Real-time multi-model incident detection for building and street cameras.
Reads RTSP camera streams, runs ML inference, and reports detected incidents to the backend.

---

## Architecture

```
MediaMTX (RTSP camera streams)
          │
          │ rtsp://
          ▼
┌─────────────────────────────────────────────┐
│              Gateway  :8000                  │
│                                             │
│  ┌──────────────────────────────────────┐   │
│  │         Stream Processor             │   │
│  │  reads frames → runs all models      │   │
│  │  in parallel → reports alerts        │   │
│  └──────────────────────────────────────┘   │
│                                             │
│  REST API  /api/v1/...                      │
│  (for manual image submission)              │
└──────────┬──────────────────────────────────┘
           │  internal HTTP
     ┌─────┴──────────────────┐
     ▼                        ▼
┌─────────────┐      ┌─────────────────┐
│   fall-     │      │  fire-detection │  ...
│  detection  │      │     :8002       │
│   :8001     │      └─────────────────┘
└─────────────┘
           │
           │ POST /api/v1/incidents
           ▼
┌──────────────────────────┐
│  qamqor-vision-backend   │
│  (Go / Gin)              │
└──────────────────────────┘
```

---

## Services

| Service | Port | Status |
|---|---|---|
| Gateway | 8000 | done |
| Fall Detection | 8001 | done |
| Fire Detection | 8002 | in progress |
| Violence Detection | 8003 | in progress |

---

## Quick Start

### With Docker

```bash
git clone https://github.com/AccidentDetector/AccidentDetector.git
cd AccidentDetector

cp .env.example .env
# edit .env — set API_KEY and BACKEND_URL

cp services/fall_detection/.env.example services/fall_detection/.env
# place best.pt in services/fall_detection/weights/

docker compose up -d

# docs available at:
# http://localhost:8000/docs
```

### Without Docker (local dev)

```bash
cd services/fall_detection
cp .env.example .env
# place best.pt in weights/

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

No auth needed when calling the service directly — auth is on the gateway only.

---

## Endpoints

```
GET  /api/v1/health
GET  /api/v1/models

GET  /api/v1/fall-detection/health
POST /api/v1/fall-detection/predict
POST /api/v1/fall-detection/predict/annotated
```

### Request

```
POST /api/v1/fall-detection/predict
Headers:
  X-Api-Key: <your key>
  Content-Type: multipart/form-data
Body:
  file: <image>
```

### Response

```json
{
  "model": "fall-detection",
  "version": "1.0.0",
  "alert": true,
  "detections": [
    {
      "class_name": "Fall",
      "class_id": 0,
      "confidence": 0.91,
      "box": { "x1": 120.0, "y1": 80.0, "x2": 340.0, "y2": 420.0 }
    }
  ],
  "count": 1,
  "inference_ms": 24.3
}
```

`alert: true` — incident detected above confidence threshold, also reported to backend automatically.

`/predict/annotated` returns a JPEG image with bounding boxes drawn and `X-Alert: true/false` header.

---

## Stream Processor

On startup the gateway:
1. Fetches camera list from the Go backend (`GET /api/v1/cameras/stream-config`)
2. Starts an RTSP reader task per camera
3. Samples one frame per second per camera
4. Sends each frame to all registered ML services in parallel
5. When any model returns `alert: true` → reports incident to Go backend
6. Deduplicates — one alert per camera per model every `ALERT_COOLDOWN_SEC` seconds
7. Refreshes camera list every `CAMERA_REFRESH_SEC` seconds

---

## Configuration

### Root `.env`

```env
API_KEY=your-secret-key

FALL_DETECTION_URL=http://fall-detection:8001

BACKEND_URL=http://qamqor-vision-backend:8080
BACKEND_API_KEY=

FRAME_INTERVAL_SEC=1.0
ALERT_COOLDOWN_SEC=30
CAMERA_REFRESH_SEC=60
```

### Service `.env`

```env
MODEL_PATH=weights/best.pt
CONF_THRESHOLD=0.40
ALERT_THRESHOLD=0.65
ALERT_CLASS=Fall
```

---

## What the Go backend needs to provide

For the stream processor to work, the Go backend needs to expose one endpoint:

```
GET /api/v1/cameras/stream-config
Headers: X-Api-Key: <key>

Response:
{
  "cameras": [
    {
      "id": "uuid",
      "rtsp_url": "rtsp://mediamtx:8554/camera-name",
      "organization_id": "uuid",
      "organization_branch_id": "uuid",
      "incident_type_map": {
        "fall-detection": "incident-type-uuid",
        "fire-detection": "incident-type-uuid"
      }
    }
  ]
}
```

Until that endpoint exists, cameras can be hardcoded in `gateway/app/camera_manager.py` in the `get_manual_cameras()` function.

---

## Adding a New Model Service

1. Copy the template:
   ```bash
   cp -r services/_template services/your_model_name
   ```

2. Edit `app/config.py` — set class names and alert class

3. Edit `app/schemas.py` — set model name string

4. Place `best.pt` in `weights/`

5. Add service to `docker-compose.yml` (copy commented block)

6. Add URL to root `.env.example`

7. Register URL in `gateway/app/config.py`

8. Add routes in `gateway/app/router.py` (copy fall-detection block)

9. Update services table in this README

---

## Model Weights

Weights (`*.pt`) are not stored in git.
Place trained `best.pt` in the service's `weights/` folder before running.

---

## Interactive Docs

```
http://localhost:8000/docs
```

---

## Tech Stack

- Python 3.11
- FastAPI + Uvicorn
- YOLOv11 (Ultralytics)
- OpenCV
- Docker + Docker Compose
