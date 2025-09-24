# docker/Dockerfile
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install CuraEngine and clean up
RUN apt-get update \
 && apt-get install -y --no-install-recommends cura-engine \
 && rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["curaengine"]
