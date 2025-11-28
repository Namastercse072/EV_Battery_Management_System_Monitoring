FROM eclipse-temurin:17-jre

RUN apt-get update && apt-get install -y python3 python3-pip wget && \
    rm -rf /var/lib/apt/lists/*

# Download Spark 4.0.0
RUN wget -q https://archive.apache.org/dist/spark/spark-4.0.0/spark-4.0.0-bin-hadoop3.tgz && \
    tar -xzf spark-4.0.0-bin-hadoop3.tgz -C /opt && \
    mv /opt/spark-4.0.0-bin-hadoop3 /opt/spark && \
    rm spark-4.0.0-bin-hadoop3.tgz

ENV SPARK_HOME=/opt/spark
ENV PATH=$PATH:$SPARK_HOME/bin

# Pre-download Kafka connector JARs to /opt/spark/jars/extra
RUN mkdir -p /opt/spark/jars/extra && cd /opt/spark/jars/extra && \
    wget -q https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.13/4.0.0/spark-sql-kafka-0-10_2.13-4.0.0.jar && \
    wget -q https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.8.0/kafka-clients-3.8.0.jar && \
    wget -q https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.11.1/commons-pool2-2.11.1.jar && \
    wget -q https://repo1.maven.org/maven2/com/fasterxml/jackson/core/jackson-databind/2.15.2/jackson-databind-2.15.2.jar && \
    echo "✓ JARs downloaded successfully"

COPY *.py /opt/spark-apps/

CMD ["spark-submit", \
     "--master", "local[*]", \
     "--jars", "/opt/spark/jars/extra/*", \
     "/opt/spark-apps/test_connection_kafka.py"]