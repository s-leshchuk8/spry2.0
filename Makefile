.PHONY: infra-init infra-plan infra-apply infra-destroy dev-backend dev-front db-up db-migrate

infra-init:
	cd infra && terraform init

infra-plan:
	cd infra && terraform plan

infra-apply:
	cd infra && terraform apply -auto-approve

infra-destroy:
	cd infra && terraform destroy

db-up:
	docker compose up -d

db-migrate:
	cd backend && uv run alembic upgrade head

dev-backend:
	cd backend && uv run uvicorn app.main:app --reload

dev-front:
	cd front && npm run dev
