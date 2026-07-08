.PHONY: setup data train dev dev-backend dev-frontend test

setup:            ## 의존성 설치 (backend: uv 우선, 없으면 venv+pip / frontend: npm)
	cd backend && (uv sync --extra dev || (python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"))
	cd frontend && npm install

data:             ## raw 13종 -> data/processed/app.db
	cd backend && uv run python scripts/preprocess.py

train:            ## LightGBM 2종 학습 -> backend/models/
	cd backend && uv run python scripts/train_congestion.py && uv run python scripts/train_route_difficulty.py

dev:              ## backend(:8000) + frontend(:5173) 동시 실행
	@$(MAKE) -j2 dev-backend dev-frontend

dev-backend:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

test:
	cd backend && uv run pytest -q
	cd frontend && npm run build
