# AI Memory OS — Admin Localhost Isolation Middleware
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
import os

class AdminLocalhostMiddleware(BaseHTTPMiddleware):
    ADMIN_API = ["/admin"]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        allow_remote = os.getenv("ALLOW_REMOTE_ADMIN", "false").lower() == "true"
        
        is_admin_api = any(path.startswith(p) for p in self.ADMIN_API)
        if path.startswith("/admin/auth/"):
            is_admin_api = False
        
        if is_admin_api and not allow_remote:
            client_host = request.client.host if request.client else "unknown"
            allowed = (client_host in ("127.0.0.1", "::1", "localhost") or
                       client_host.startswith("192.168.") or
                       client_host.startswith("172.") or
                       client_host.startswith("10."))
            
            forwarded = request.headers.get("X-Forwarded-For", "")
            if forwarded:
                actual_ip = forwarded.split(",")[0].strip()
                allowed = allowed or actual_ip in ("127.0.0.1", "::1")
            
            if not allowed:
                return JSONResponse(status_code=403, content={
                    "error": "forbidden_remote_admin",
                    "message": "管理 API 仅允许本地访问。设置 ALLOW_REMOTE_ADMIN=true 可开放远程。"
                })
        
        return await call_next(request)
