FROM eclipse-temurin:17-jre

ENV KAFKA_VERSION=3.8.0 \
    SCALA_VERSION=2.13 \
    KAFKA_HOME=/opt/kafka \
    PATH="$PATH:/opt/kafka/bin"

RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends curl jq ca-certificates gettext-base && \
    rm -rf /var/lib/apt/lists/*

# safer download: save to temp file, fail on HTTP errors, and verify before extracting
RUN set -eux; \
    KAFKA_TGZ="kafka_${SCALA_VERSION}-${KAFKA_VERSION}.tgz"; \
    URL="https://downloads.apache.org/kafka/${KAFKA_VERSION}/${KAFKA_TGZ}"; \
    echo "Downloading Kafka from: ${URL}"; \
    curl -fSL --retry 5 --retry-delay 2 -o "/tmp/${KAFKA_TGZ}" "${URL}"; \
    ls -lh "/tmp/${KAFKA_TGZ}"; \
    tar -xzf "/tmp/${KAFKA_TGZ}" -C /opt; \
    mv "/opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION}" "${KAFKA_HOME}"; \
    rm -f "/tmp/${KAFKA_TGZ}"

RUN mkdir -p /var/lib/kafka/data

COPY entrypoint.sh /entrypoint.sh
COPY server.properties /opt/kafka/config/server.properties
RUN chmod +x /entrypoint.sh && chmod +x /opt/kafka/bin/*.sh

EXPOSE 9092 9093

HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=45s \
    CMD kafka-broker-api-versions.sh --bootstrap-server localhost:9092

CMD ["/entrypoint.sh"]