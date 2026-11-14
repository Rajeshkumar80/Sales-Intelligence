CREATE DATABASE IF NOT EXISTS bda_sales;
USE bda_sales;

CREATE EXTERNAL TABLE IF NOT EXISTS transactions_raw (
  transaction_id STRING,
  product_id STRING,
  product_name STRING,
  category STRING,
  quantity INT,
  unit_price DOUBLE,
  region STRING,
  timestamp_ms BIGINT
)
PARTITIONED BY (batch_id STRING)
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\t'
STORED AS TEXTFILE
LOCATION '/bda/sales/input';

CREATE EXTERNAL TABLE IF NOT EXISTS sales_fact_daily (
  sale_date STRING,
  product_id STRING,
  product_name STRING,
  category STRING,
  region STRING,
  revenue DOUBLE,
  quantity BIGINT,
  orders BIGINT
)
PARTITIONED BY (batch_id STRING)
STORED AS ORC
LOCATION '/bda/sales/fact';
