import uuid
from functools import wraps
from fastapi import Request
from loguru import logger

def audit_log(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request: Request = kwargs.get("request")
        req_id = str(uuid.uuid4())
        user_ip = request.client.host if request else "unknown"
        endpoint = request.url.path if request else "unknown"
        try:
            response = await func(*args, **kwargs)
            status_code = getattr(response, "status_code", 200)
        except Exception as e:
            status_code = 500
            raise
        finally:
            logger.info({
                "req_id": req_id,
                "user_ip": user_ip,
                "endpoint": endpoint,
                "status": status_code
            })
        return response
    return wrapper
