broker_url = "redis://cache:6379/0"
result_backend = "redis://cache:6379/0"
task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]
timezone = "UTC"
enable_utc = True
import os
worker_concurrency = int(os.getenv("CELERY_CONCURRENCY", 4))
task_track_started = True
worker_prefetch_multiplier = 1
