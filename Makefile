IMAGE_NAME=nebulabroadcast/promexp:latest

run: build
	docker run -it --rm \
		-p 9731:9731 \
		-v ./settings.json:/app/settings.json \
		$(IMAGE_NAME)

build:
	docker build -t $(IMAGE_NAME) .
