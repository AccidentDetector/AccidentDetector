# Fall Detection Service

Detects fallen/fainted persons in images using YOLOv11s.

## Classes
- `Fall` — person is fallen or fainted on the ground
- `Fine` — person is sitting or crouching
- `Stand` — person is standing normally

## Alert condition
`alert: true` when class `Fall` is detected with confidence >= `ALERT_THRESHOLD`

## Setup

```bash
cp .env.example .env
# place best.pt in weights/

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## Endpoints

```
GET  /health
POST /predict           → JSON detections
POST /predict/annotated → JPEG with bounding boxes drawn
```

Auth is handled by the gateway — no key needed when calling this service directly.

## Model weights

Place your trained `best.pt` in the `weights/` folder.
Not committed to git — download or train separately.
