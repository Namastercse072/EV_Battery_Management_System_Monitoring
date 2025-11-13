from pyspark.sql import SparkSession
from pyspark.sql.functions import col

spark = SparkSession.builder.appName("EVProcessor").getOrCreate()
df = spark.readStream.format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "ev_stream").load()

json_df = df.selectExpr("CAST(value AS STRING) as json")
query = json_df.writeStream.format("console").start()
query.awaitTermination()
