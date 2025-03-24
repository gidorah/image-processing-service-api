export COMPOSE_FILE := "docker-compose.local.yml"

## Just does not yet manage signals for subprocesses reliably, which can lead to unexpected behavior.
## Exercise caution before expanding its usage in production environments.
## For more information, see https://github.com/casey/just/issues/2473 .


# Default command to list all available commands.
default:
    @just --list

# build: Build image.
build:
    @echo "Building image..."
    @docker compose build

# up: Start up containers.
up:
    @echo "Starting up containers..."
    @docker compose up -d --remove-orphans

# down: Stop containers.
down:
    @echo "Stopping containers..."
    @docker compose down

# prune: Remove containers and their volumes.
prune *args:
    @echo "Killing containers and removing volumes..."
    @docker compose down -v {{args}}

# logs: View container logs
logs *args:
    @docker compose logs -f {{args}}

# up_services: Start up services except for the django service.
up_services:
    @echo "Starting up services except for the django service..."
    @docker compose up -d --remove-orphans --scale django=0

# # staging_build: Build staging image.
# staging_build:
#     @echo "Building staging image..."
#     @docker compose -f docker-compose.staging.yml build

# # staging_up: Start up staging containers.
# staging_up:
#     @echo "Starting up staging containers..."
#     @docker compose -f docker-compose.staging.yml up -d --remove-orphans

# # staging_down: Stop staging containers.
# staging_down:
#     @echo "Stopping staging containers..."
#     @docker compose -f docker-compose.staging.yml down

# # staging_prune: Remove staging containers and their volumes.
# staging_prune *args:
#     @echo "Killing staging containers and removing volumes..."
#     @docker compose -f docker-compose.staging.yml down -v {{args}}

# # staging_logs: View staging container logs
# staging_logs *args:
#     @docker compose -f docker-compose.staging.yml logs -f {{args}}

# test_prod_build: Test production Dockerfile build time
# test_prod_build:
#     @echo "Testing production Dockerfile build time..."
#     @time docker build --progress=plain -t personal_website_nextjs_test -f compose/production/Dockerfile .
#     @echo "\nTesting if the image works (Ctrl+C to stop)..."
#     @docker run --rm -p 3000:3000 personal_website_nextjs_test

# test_local_build: Test local Dockerfile build time
# test_local_build:
#     @echo "Testing local Dockerfile build time..."
#     @time docker build --progress=plain -t image_processing_service_test -f compose/local/Dockerfile .
#     @echo "\nTesting if the image works (Ctrl+C to stop)..."
#     @docker run --rm -p 3000:3000 personal_website_nextjs_test
