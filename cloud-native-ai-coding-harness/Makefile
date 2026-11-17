.PHONY: install test run dev clean docker-build docker-up

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v --tb=short

run:
	uvicorn server.app:app --host 0.0.0.0 --port 8000

dev:
	uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload

clean:
	rm -rf .pytest_cache .cache __pycache__ */__pycache__ */*/__pycache__

docker-build:
	docker compose build

docker-up:
	docker compose up -d
