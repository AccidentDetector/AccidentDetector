````md
# [Your Model Name] Detection Service

## How to use this template

Copy this folder:

```bash
cp -r services/_template services/your_model_name
````

Pick a free port number:

* `8001` — fall
* `8002` — fire
* `8003` — violence

## Update these files

### `app/config.py`

Set:

* `model_path`
* `class_names`
* `alert_class`
* thresholds

For video models, also set clip-related parameters if needed:

* `clip_num_frames`
* `clip_duration_sec`
* `image_size`

### `app/schemas.py`

Change the model name from:

```python
model = 'your-model'
```

to your actual model name.

Keep the standard response format:

* `alert`
* `detections`
* `count`
* `inference_ms`

### `app/model.py`

Rename `YourDetector` to something meaningful and implement the model loading/inference logic.

Use the correct input type:

* **image model** — one frame/image
* **video model** — short clip

### `app/router.py`

Implement:

* `GET /health`
* `POST /predict`

Use:

* `image/*` validation for image models
* `video/*` validation for video models

`/predict/annotated` is optional.
For video models, returning `501 Not Implemented` is acceptable at first.

### `app/main.py`

Update the FastAPI title string.

### `Dockerfile`

Update:

* `EXPOSE` to your port
* uvicorn `--port` to the same port

### `weights/`

Place your model weights in:

```text
weights/
```

Do not commit model weights.

## Register the model in gateway

### Add your service to root `docker-compose.yml`

Copy an existing service block and update:

* service name
* build path
* port
* weights mount

### Add your service URL to root `.env.example`

### Add your model to `gateway/app/config.py`

Register it in `MODEL_REGISTRY`.

For an **image model**:

```python
'your-image-model': {
    'url': settings.your_image_model_url,
    'input_mode': 'image',
    'filename': 'frame.jpg',
    'content_type': 'image/jpeg',
},
```

For a **video model**:

```python
'your-video-model': {
    'url': settings.your_video_model_url,
    'input_mode': 'video',
    'filename': 'clip.avi',
    'content_type': 'video/x-msvideo',
    'clip_frames': 16,
    'clip_duration_sec': 1.0,
    'clip_fps': 16,
},
```

Also add the corresponding URL field to `Settings`.

### Add your routes to `gateway/app/router.py`

Copy an existing route block such as `fall-detection` and adapt it.

Use:

* image upload validation for image models
* video upload validation for video models

```
```

## Policy Integration

Model services should **not** hardcode `warning` vs `alert`.

A service should return raw detection output in the standard format:

```json
{
  "model": "your-model",
  "version": "1.0.0",
  "alert": false,
  "detections": [
    {
      "class_name": "your-class",
      "confidence": 0.83
    }
  ],
  "count": 1,
  "inference_ms": 12.5
}
```

### What you must do when adding a new model

1. Register the model in `gateway/app/config.py`
2. Make sure the service returns:
   - `detections[].class_name`
   - `detections[].confidence`
3. Add an incident type mapping for the model
4. Add policy rules in `gateway/app/policies.py`

### Example policy rule

```python
"your-model": {
    "rules": [
        {
            "class_name": "your-class",
            "min_confidence": 0.70,
            "max_confidence": 0.90,
            "action": "warning",
            "cooldown_sec": 20,
        },
        {
            "class_name": "your-class",
            "min_confidence": 0.90,
            "max_confidence": 1.01,
            "action": "alert",
            "cooldown_sec": 10,
        },
    ]
}
```

### Notes

- `class_name` must be stable and consistent
- `confidence` must be numeric
- `alert` may still be returned as a fallback
- final `ignore / warning / alert` decision is made by the gateway policy
- batch / video models may use custom transport, but should still be adapted to the same detection result format before reaching the gateway policy layer
