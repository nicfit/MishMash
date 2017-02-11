all: MishMash

postgres:
	docker build -t dev-postgres -f ./Dockerfile.postgres .

MishMash: postgres
	docker build -t dev-mishmash .
