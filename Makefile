.PHONY: run dev install test validate

PYTHON = python3
PORT ?= 8080

install:
	$(PYTHON) -m pip install -e ../framework.trails/python[http,llm]
	$(PYTHON) -m pip install -r requirements.txt

run:
	PORT=$(PORT) $(PYTHON) app.py

dev:
	TRAILS_ENV=development PORT=$(PORT) $(PYTHON) app.py

validate:
	cd /tmp/word-drift-orig && $(PYTHON) validate.py

test:
	$(PYTHON) -m pytest tests/ -v

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-logs:
	docker compose logs -f word-drift

clean:
	rm -rf __pycache__ *.pyc wd-store/
