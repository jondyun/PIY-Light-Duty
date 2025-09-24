
cat > docker/Dockerfile <<'EOF'

mkdir -p docker
cat > docker/Dockerfile <<'EOF'
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends cura-engine \
 && rm -rf /var/lib/apt/lists/*
ENTRYPOINT ["curaengine"]
