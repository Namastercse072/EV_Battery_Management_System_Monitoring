import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, schema_of_json, to_timestamp
from pyspark.sql.types import StructType, StructField, DoubleType, StringType

try:
    print("🔄 Initializing Spark session for PostgreSQL Storage...\n")
    
    spark = SparkSession.builder \
        .appName("EVBatteryPostgresStorage") \
        .config("spark.jars.packages", 
                "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1," \
                "org.postgresql:postgresql:42.7.1") \
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
    
    spark.sparkContext.setLogLevel("WARN")
    
    # ============================
    # 1. Read Processed Data from Kafka
    # ============================
    print("🔗 Reading from Kafka topic 'ev_processed'...")
    
    schema = StructType([
        StructField("voltage", DoubleType()),
        StructField("temperature", DoubleType()),
        StructField("current", DoubleType()),
        StructField("soc", DoubleType()),
        StructField("soh", DoubleType()),
        StructField("timestamp", StringType()),
        StructField("processing_timestamp", StringType()),
        StructField("anomaly_type", StringType()),
        StructField("severity", StringType())
    ])
    
    df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka:9092") \
        .option("subscribe", "ev_processed") \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "true") \
        .option("fetch.min.bytes", "50000") \
        .option("fetch.max.bytes", "52428800") \
        .option("max.poll.records", "1000") \
                .load()
    
    df_parsed = df.selectExpr("CAST(value AS STRING)") \
        .select(from_json(col("value"), schema).alias("data")) \
        .select("data.*")
    
    print("✓ Connected to ev_processed\n")
    print("Optimizations applied for high-throughput streaming.\n")

    # ============================
    # 2. Prepare for Database Write
    # ============================
    print("📝 Preparing data for PostgreSQL storage...\n")
    
    df_clean = df_parsed \
        .withColumn("voltage", col("voltage").cast(DoubleType())) \
        .withColumn("temperature", col("temperature").cast(DoubleType())) \
        .withColumn("current", col("current").cast(DoubleType())) \
        .withColumn("soc", col("soc").cast(DoubleType())) \
        .withColumn("soh", col("soh").cast(DoubleType())) \
        .withColumn("timestamp", to_timestamp(col("timestamp"))) \
        .select("voltage", "temperature", "current", "soc", "soh", "timestamp")
    
    # ============================
    # 3. Stream to PostgreSQL
    # ============================
    def write_to_postgres(batch_df, batch_id):
        """Write batch to PostgreSQL"""
        if batch_df.count() > 0:
            batch_df.write \
                .format("jdbc") \
                .option("url", "jdbc:postgresql://postgres:5432/battery_metrics") \
                .option("dbtable", "battery_metrics") \
                .option("user", "superset") \
                .option("password", "superset_pass") \
                .option("driver", "org.postgresql.Driver") \
                .mode("append") \
                .save()
            
            print(f"✓ Batch {batch_id}: {batch_df.count()} records written to PostgreSQL")
        else:
            print(f"  Batch {batch_id}: No records to write")
    
    print("📤 Starting PostgreSQL write stream...\n")
    
    query = df_clean.writeStream \
        .foreachBatch(write_to_postgres) \
        .option("checkpointLocation", "/tmp/spark-checkpoints/postgres") \
        .start()
    
    print("=" * 70)
    print("💾 PostgreSQL Storage Stream Active")
    print("=" * 70)
    print(f"Input: Kafka topic 'ev_processed'")
    print(f"Output: PostgreSQL table 'battery_metrics'")
    print(f"Database: battery_metrics on postgres:5432")
    print("=" * 70)
    print("Writing batches... Press Ctrl+C to stop\n")
    
    query.awaitTermination()

except KeyboardInterrupt:
    print("\n\n⏹️  Stopping PostgreSQL write stream...")
    query.stop()
    print("✓ Stream stopped")

except Exception as e:
    print(f"\n✗ Error: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)

finally:
    print("Done.")