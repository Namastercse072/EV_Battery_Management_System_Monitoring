FROM eclipse-temurin:17-jre as base
LABEL maintainer="edge-node"

# Install dependencies
RUN apt-get update -qq && apt-get install -y \
    python3 python3-pip curl lz4 mosquitto-clients \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Apache MiNiFi
ENV MINIFI_VERSION=1.25.0
RUN curl -L https://archive.apache.org/dist/nifi/minifi/${MINIFI_VERSION}/minifi-${MINIFI_VERSION}-bin.tar.gz \
    | tar -xz -C /opt \
    && ln -s /opt/minifi-${MINIFI_VERSION} /opt/minifi

# Copy configuration and scripts
COPY conf/ /opt/minifi/conf/
COPY edge_scripts/ /opt/minifi/scripts/
WORKDIR /opt/minifi

# Expose MiNiFi web port
EXPOSE 8081

ENTRYPOINT ["bin/minifi.sh", "run"]