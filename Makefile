VERSION=$(shell uv run python -m promexp --version)
IMAGE_NAME=nebulabroadcast/promexp

check:
	uv version $(VERSION)
	uv run ruff format . 
	uv run ruff check --fix .
	uv run mypy .


build-dev:
	docker build -t $(IMAGE_NAME):dev .

run: build-dev
	docker run -it --rm \
		-p 9731:9731 \
		-v ./settings.json:/app/settings.json \
		$(IMAGE_NAME):dev

dev: build-dev
	docker push $(IMAGE_NAME):dev

build-prod: check
	uv build
	docker build -t $(IMAGE_NAME):$(VERSION) .
	docker tag $(IMAGE_NAME):$(VERSION) $(IMAGE_NAME):latest
	docker push $(IMAGE_NAME):$(VERSION)
	docker push $(IMAGE_NAME):latest
	
