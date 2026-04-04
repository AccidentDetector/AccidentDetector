# Fall Detection Service

Detects fallen/fainted persons in images using YOLOv11s.

## Classes
- `Fall` — person is fallen or fainted
- `Fine` — person is sitting or crouching
- `Stand` — person is standing normally

## Setup

```bash
cp env.example .env
# place best.pt in weights/

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

## Endpoints

```
GET  /health
POST /predict           → JSON detections
POST /predict/annotated → JPEG with boxes drawn
```

Note: auth is handled by the gateway, not this service directly.

## Model weights

Place your trained `best.pt` in the `weights/` folder.
Not committed to git — download separately.
