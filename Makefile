SPLUNK_TO_SNOW_IMAGE="splunk-to-snow"

.PHONY: all
all: validate

.PHONY: build
build:
	docker build -t $(SPLUNK_TO_SNOW_IMAGE) .

.PHONY: validate
validate: build
	docker run -i -t $(SPLUNK_TO_SNOW_IMAGE)

.PHONY: clean-image
clean-image:
	@if [ "$$(docker images -q $(SPLUNK_TO_SNOW_IMAGE))" != "" ]; then\
		docker rmi -f $$(docker images -q $(SPLUNK_TO_SNOW_IMAGE));\
	fi
