# AI Memory OS — Admin Localhost-Only Isolation Middleware
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse

class AdminLocalhostMiddleware(BaseHTTPMiddleware):
    """
    Middleware to restrict access to the Admin Dashboard (/manage) and Admin API (/admin)
    exclusively to localhost / loopback interfaces (127.0.0.1, ::1) or local proxies.
    """
    ADMIN_PATHS = ["/manage", "/admin"]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Check if the requested path starts with any admin path prefix
        is_admin_path = any(path.startswith(p) for p in self.ADMIN_PATHS)
        
        # Exclude public auth endpoints so remote client spaces can register/login
        if is_admin_path and path.startswith("/admin/auth/"):
            is_admin_path = False
            
        if is_admin_path:
            client_host = request.client.host if request.client else "unknown"
            # Allow loopback, Docker Desktop macOS interface, and Docker bridge private networks (172.x, 10.x)
            allowed = (client_host in ("127.0.0.1", "::1", "localhost") or
                client_host.startswith("192.168.") or
                client_host.startswith("172.") or
                client_host.startswith("10."))
            
            # Allow X-Forwarded-For if it maps to local loopback or local private networks
            forwarded_for = request.headers.get("X-Forwarded-For", "")
            if forwarded_for:
                actual_ip = forwarded_for.split(",")[0].strip()
                allowed = allowed or (
                    actual_ip in ("127.0.0.1", "::1") or
                    actual_ip.startswith("172.") or
                    actual_ip.startswith("10.")
                )
            
            if not allowed:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "forbidden_remote_admin",
                        "message": "安全锁已锁定：管理端及后台 API 仅允许在本机 localhost/127.0.0.1 访问，请在服务器本机打开浏览器操作。"
                    }
                )
        
        return await call_next(request)

