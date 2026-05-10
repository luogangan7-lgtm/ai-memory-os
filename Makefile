.PHONY: up down install run test clean

# Start all services
up:
	docker compose up -d

# Stop all services
down:
	docker compose down

# Install Python dependencies
install:
	pip install -r backend/requirements.txt

# Run the FastAPI dev server
run:
	cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Quick smoke test
test:
	curl -s http://localhost:8000/ | python3 -m json.tool
	curl -s -X POST http://localhost:8000/auth/token?team_id=default | python3 -m json.tool

# Clean volumes
clean:
	docker compose down -v

# One-click deploy
deploy:
	python3 deploy.py
