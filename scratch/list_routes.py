from backend.main import app
for route in app.routes:
    print(f"{getattr(route, 'methods', 'MOUNT')} {getattr(route, 'path', '???')}")
