import sys
import time
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, schema_of_json, when, struct, to_timestamp,
    current_timestamp, to_json, lit, coalesce
)
from pyspark.sql.types import StructType, StructField, DoubleType, StringType, LongType

try:
    print("🔄 Initializing Spark session for EV Battery Processing...")
    
    spark = SparkSession.builder \
        .appName("EVBatteryProcessor") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1") \
        .config("spark.sql.streaming.schemaInference", "true") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.shuffle.partitions", "8")  \
        .config("spark.default.parallelism", "8") \
        .config("spark.streaming.backpressure.enabled", "true")  \
        .config("spark.streaming.kafka.maxRatePerPartition", "5000") \
        .config("spark.executor.memory", "4g") \
        .config("spark.driver.memory", "2g") \
        .config("spark.memory.fraction", "0.7") \
        .config("spark.sql.streaming.statefulOperator.checkCorrectness.enabled", "false") \
        .config("spark.sql.streaming.forceDeleteTempCheckpointLocation", "true") \
        .getOrCreate()
    # tunning
    spark.conf.set("spark.sql.shuffle.partitions", "10")
    spark.conf.set("spark.streaming.stopGracefullyOnShutdown", "true")
    spark.conf.set("spark.sql.streaming.forceDeleteTempCheckpointLocation", "true")
    
    spark.sparkContext.setLogLevel("WARN")
    print("✓ SparkSession created successfully")
    print(f"  Spark version: {spark.version}")
    print(f"  Master: spark://spark-master:7077\n")
    
    # ============================
    # 1. Connect to Kafka (ev_raw)
    # ============================
    print("🔗 Subscribing to Kafka topic 'ev_raw'...")
    
    kafka_broker = "kafka:9092"
    input_topic = "ev_raw"
    
    df_kafka = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_broker) \
        .option("subscribe", input_topic) \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "true") \
        .option("maxOffsetsPerTrigger", "10000") \
        .option("fetch.min.bytes", "50000") \
        .option("fetch.max.bytes", "52428800") \
        .option("max.poll.records", "1000") \
        .load()
    
    print(f"✓ Connected to Kafka broker: {kafka_broker}")
    print(f"✓ Consuming from topic: {input_topic}\n")
    
    # ============================
    # 2. Parse JSON from Kafka
    # ============================
    print("📝 Parsing JSON schema...")
    
    schema = StructType([
        StructField("voltage", DoubleType()),
        StructField("temperature", DoubleType()),
        StructField("current", DoubleType()),
        StructField("soc", DoubleType()),  # State of Charge
        StructField("soh", DoubleType()),  # State of Health
        StructField("timestamp", StringType())
    ])
    
    df_parsed = df_kafka.selectExpr("CAST(value AS STRING)") \
        .select(from_json(col("value"), schema).alias("data")) \
        .select("data.*")
    
    print("✓ Schema parsed:\n")
    df_parsed.printSchema()
    
    # ============================
    # 3. Transform & Enrich Data
    # ============================
    print("\n⚙️  Transforming data...")
    df_transformed = df_parsed \
        .withColumn("processing_timestamp", current_timestamp()) \
        .withColumn("voltage", col("voltage").cast(DoubleType())) \
        .withColumn("temperature", col("temperature").cast(DoubleType())) \
        .withColumn("soc", col("soc").cast(DoubleType())) \
        .withColumn("soh", col("soh").cast(DoubleType())) \
        .withColumn("current", col("current").cast(DoubleType()))
    
    # ============================
    # 4. Anomaly Detection
    # ============================
    print("🚨 Setting up anomaly detection...\n")
    
    df_anomalies = df_transformed \
        .withColumn("is_anomaly", 
             when(
        (col("voltage") > 4.2) |
        (col("voltage") < 2.5) |
        (col("temperature") > 50) |
        (col("temperature") < 0) |
        (col("soc") < 20) |
        (col("soh") < 50),
        True
    ).otherwise(False)) \
        .withColumn("anomaly_type",
            when((col("voltage") > 4.2), "HIGH_VOLTAGE")
            .when((col("voltage") < 2.5), "LOW_VOLTAGE")
            .when((col("temperature") > 50), "OVERHEAT")
            .when((col("temperature") < 0), "UNDERCOOL")
            .when((col("soc") < 20), "CRITICAL_LOW_SOC")
            .when((col("soh") < 50), "DEGRADED_BATTERY")
            .otherwise("NORMAL")
        ) \
        .withColumn("severity",
            when((col("voltage") > 4.2) | (col("temperature") > 50) | (col("soc") < 20), "CRITICAL")
            .when((col("voltage") < 2.5) | (col("soh") < 50), "WARNING")
            .otherwise("INFO")
        )
    
    print("✓ Anomaly detection configured")
    print("  - HIGH_VOLTAGE: voltage > 4.2V")
    print("  - LOW_VOLTAGE: voltage < 2.5V")
    print("  - OVERHEAT: temperature > 50°C")
    print("  - UNDERCOOL: temperature < 0°C")
    print("  - CRITICAL_LOW_SOC: soc < 20%")
    print("  - DEGRADED_BATTERY: soh < 50%\n")
    
    # ============================
    # 5. Split Normal & Alert Data
    # ============================
    print("📤 Setting up Kafka publishers...\n")
    
    df_normal = df_anomalies.filter(col("is_anomaly") == False) \
        .select(to_json(struct(
            coalesce(col("voltage"), lit(0.0)).alias("voltage"), 
            coalesce(col("temperature"), lit(0.0)).alias("temperature"), 
            coalesce(col("current"), lit(0.0)).alias("current"),
            coalesce(col("soc"), lit(0.0)).alias("soc"), 
            coalesce(col("soh"), lit(0.0)).alias("soh"),                 
            col("timestamp"),
            col("processing_timestamp"), col("anomaly_type"), col("severity")
        )).alias("value"))
    
    df_alerts = df_anomalies.filter(col("is_anomaly") == True) \
        .select(to_json(struct(
            coalesce(col("voltage"), lit(0.0)).alias("voltage"), 
            coalesce(col("temperature"), lit(0.0)).alias("temperature"), 
            coalesce(col("current"), lit(0.0)).alias("current"),
            coalesce(col("soc"), lit(0.0)).alias("soc"), 
            coalesce(col("soh"), lit(0.0)).alias("soh"),                 
            col("timestamp"),
            col("processing_timestamp"), col("anomaly_type"), col("severity")
        )).alias("value"))
    df_normal.printSchema()
    df_alerts.printSchema()
    print("✓ Data streams prepared for publishing:")
    print("  - Normal data → topic 'ev_processed'")
    print("  - Anomalies → topic 'ev_alerts'\n")
    df_normal = df_normal.na.drop()
    df_alerts = df_alerts.na.drop()
    # ============================
    # 6. Stream 1: Publish Normal Data
    # ============================
    query_normal = df_normal.writeStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_broker) \
        .option("topic", "ev_processed") \
        .option("checkpointLocation", "/tmp/spark-checkpoints/ev_processed") \
        .option("failOnDataLoss", "false") \
        .outputMode("append") \
        .start()
    
    print("✓ Stream 1 started: ev_raw → ev_processed (normal data)")
    print("Optimizations applied for high-throughput streaming.\n")
    # ============================
    # 7. Stream 2: Publish Alert Data
    # ============================
    query_alerts = df_alerts.writeStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_broker) \
        .option("topic", "ev_alerts") \
        .option("checkpointLocation", "/tmp/spark-checkpoints/ev_alerts") \
        .option("failOnDataLoss", "false") \
        .outputMode("append") \
        .start()
    
    print("✓ Stream 2 started: ev_raw → ev_alerts (anomalies)\n")
    
    # ============================
    # 8. Stream 3: Console Output (Debug)
    # ============================
    query_console = df_anomalies.writeStream \
        .format("console") \
        .option("truncate", "false") \
        .option("numRows", "20") \
        .option("checkpointLocation", "/tmp/spark-checkpoints/console") \
        .start()
    
    print("✓ Stream 3 started: Console output (debug)\n")
    
    print("=" * 70)
    print("📊 EV Battery Processing Pipeline Active")
    print("=" * 70)
    print(f"Input Stream:  Kafka topic 'ev_raw' ({kafka_broker})")
    print(f"Output Stream 1: Kafka topic 'ev_processed' (Normal data)")
    print(f"Output Stream 2: Kafka topic 'ev_alerts' (Anomalies)")
    print(f"Output Stream 3: Console (Debug logs)")
    print("=" * 70)
    print("Waiting for data... Press Ctrl+C to stop\n")
    
    # Keep running
    query_normal.awaitTermination()
    
except KeyboardInterrupt:
    print("\n\n⏹️  Stopping Spark streams...")
    query_normal.stop()
    query_alerts.stop()
    query_console.stop()
    print("✓ All streams stopped")

except Exception as e:
    print(f"\n✗ Error: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)

finally:
    print("Done.")