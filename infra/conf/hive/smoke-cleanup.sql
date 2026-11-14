USE bda_sales;
ALTER TABLE sales_fact_daily DROP PARTITION (batch_id='smoke');
SHOW PARTITIONS sales_fact_daily;
