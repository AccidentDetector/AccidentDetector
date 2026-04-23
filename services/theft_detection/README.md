# Theft Detection Service

Detects robbery/theft events in surveillance footage using a sequence-based model (ResNet50 + GRU + Attention).

## Classes

- **Normal** — normal activity, no theft detected
- **Robbery** — theft/robbery in progress

## Alert condition

`alert: true` when class `Robbery` is detected with confidence >= `CONF_THRESHOLD` (default: 0.50)

## Setup

```bash
cp .env.example .env
# place crime_detection_scripted.pt in weights/

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload
```

## Environment variables (`.env`)

```env
MODEL_PATH=weights/crime_detection_scripted.pt
SEQUENCE_LENGTH=16
CONF_THRESHOLD=0.50
ALERT_CLASS=Robbery
IMG_SIZE=224
STRIDE=1
```

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health check |
| POST | `/predict/batch` | Accepts exactly 16 image frames, returns prediction |

## Request format

`POST /predict/batch?camera_id=default`

Content-Type: `multipart/form-data`

Body: 16 files with key `files`

```bash
curl -X POST "http://localhost:8005/predict/batch?camera_id=test" \
  -F "files=@frame_0.png;type=image/png" \
  -F "files=@frame_1.png;type=image/png" \
  ... (16 files total)
```

## Response format

```json
{
  "model": "theft-detection",
  "version": "1.0.0",
  "alert": true,
  "confidence": 0.9895,
  "class_name": "Robbery",
  "inference_ms": 1209.15
}
```

## Model weights

Place your trained `crime_detection_scripted.pt` in the `weights/` folder. Not committed to git — download or train separately.

## Auth

Auth is handled by the gateway — no key needed when calling this service directly.