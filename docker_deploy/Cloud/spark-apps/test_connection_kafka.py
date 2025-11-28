from pyspark.sql import SparkSession
import sys
import time

try:
    print("🔄 Initializing Spark session...")
    spark = SparkSession.builder \
        .appName("KafkaTest") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0") \
        .config("spark.sql.streaming.schemaInference", "true") \
        .getOrCreate()
    
    print("✓ SparkSession created successfully")
    print(f"Spark version: {spark.version}")
    
    kafka_broker = "kafka:9092"
    topic = "ev_raw"
    
    print(f"\n🔗 Subscribing to topic '{topic}' on {kafka_broker}...")
    
    df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_broker) \
        .option("subscribe", topic) \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "false") \
        .load()
    
    print(f"✓ Connected to Kafka!")
    print(f"✓ Topic '{topic}' auto-created (if didn't exist)")
    print(f"✓ Schema:")
    df.printSchema()
    
    query = df.writeStream \
        .outputMode("append") \
        .format("console") \
        .option("truncate", False) \
        .start()
    
    print(f"\n✓ Streaming query started.")
    print(f"📨 Listening for messages on '{topic}'...")
    print(f"(Waiting 30 seconds for messages...)\n")
    
    query.awaitTermination(timeout=30000)  # 30 seconds
    query.stop()
    
    print(f"\n✓ Test completed.")
    print(f"To verify topic was created, run:")
    print(f"  docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list")

except Exception as e:
    print(f"✗ Error: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    print("Done.")