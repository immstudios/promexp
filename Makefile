VERSION=$(shell uv run python -m promexp --version)
IMAGE_NAME=nebulabroadcast/promexp

check:
	uv version $(VERSION)
	uv run ruff format . 
	uv run ruff check --fix .
	uv run mypy .


build:
	docker build -t $(IMAGE_NAME):dev

run: build
	docker run -it --rm \
		-p 9731:9731 \
		-v ./settings.json:/app/settings.json \
		$(IMAGE_NAME)

push: build
	docker push $(IMAGE_NAME)


