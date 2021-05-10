SPLUNK_TO_SNOW_IMAGE="splunk-to-snow"

.PHONY: all
all: validate

.venv:
	@echo "[+] Installing virtualenv using 'venv'"
	@python3 -m venv .venv

	@echo "[+] Initializing necessary dependencies in virtualenv"
	@. .venv/bin/activate && \
	pip install --upgrade pip && \
	pip install -r requirements.txt && \
	pre-commit install

.PHONY: build
build:
	docker build -t $(SPLUNK_TO_SNOW_IMAGE) .

.PHONY: test
test: .venv
	@. .venv/bin/activate && \
	cd ./src/bin && \
	python -B -m unittest test_create_service_now_ticket.py

.PHONY: validate
validate: package build
	docker run $(SPLUNK_TO_SNOW_IMAGE)

.PHONY: clean
clean:
	rm -rf splunk_to_snow.spl
	rm -rf ./.venv

.PHONY: clean-image
clean-image:
	@if [ "$$(docker images -q $(SPLUNK_TO_SNOW_IMAGE))" != "" ]; then\
		docker rmi -f $$(docker images -q $(SPLUNK_TO_SNOW_IMAGE));\
	fi

.PHONY: package
package:
	@echo "[+] Removing old 'splunk_to_snow/'"
	@rm -rf splunk_to_snow

	@echo "[+] Copying 'src/' to 'splunk_to_snow/'"
	@rsync -r src/ splunk_to_snow

	@echo "[+] Clean up 'splunk_to_snow/'"
	@find ./splunk_to_snow -type d -name __pycache__\* -exec rm  -rf {} \; 2>/dev/null
	@find ./splunk_to_snow -type d -name .\* -exec rm  -rf {} \; 2>/dev/null
	@rm -rf ./splunk_to_snow/**/.env

	@echo "[+] Fixing permissions within 'splunk_to_snow/'"
	@sudo chmod -R 644 ./splunk_to_snow && sudo find ./splunk_to_snow -type d -exec chmod 755 {} +

	@echo "[+] Compress 'splunk_to_snow/' using tar"
	@tar c ./splunk_to_snow > ./splunk_to_snow.tar

	@echo "[+] Gziping 'splunk_to_snow.tar'"
	@gzip ./splunk_to_snow.tar

	@echo "[+] Renaming 'splunk_to_snow.tar.gz' to 'splunk_to_snow.spl'"
	@mv ./splunk_to_snow.tar.gz ./splunk_to_snow.spl

	@echo "[+] Removing old 'splunk_to_snow/'"
	@rm -rf splunk_to_snow
