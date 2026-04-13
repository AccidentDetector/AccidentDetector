# [Your Model Name] Detection Service

## How to use this template

1. Copy this folder:
   ```bash
   cp -r services/_template services/your_model_name
   ```

2. Pick a port number (8001 is fall, 8002 fire, 8003 violence etc.)

3. Update these files:

   **`app/config.py`**
   - Set `class_names` to your model's classes
   - Set `alert_class` to the class name that should trigger `alert=true`

   **`app/schemas.py`**
   - Change `model = 'your-model'` to your model name

   **`app/model.py`**
   - Rename `YourDetector` class to something meaningful

   **`app/main.py`**
   - Update the `title` string

   **`Dockerfile`**
   - Change `EXPOSE 8001` to your port

4. Place your `best.pt` in `weights/`

5. Add your service to root `docker-compose.yml` (copy the commented block)

6. Add your service URL to root `.env.example`

7. Add your URL to `gateway/app/config.py` SERVICE_REGISTRY

8. Add your routes to `gateway/app/router.py` (copy the fall-detection block)

9. Update the README table in root `README.md`
