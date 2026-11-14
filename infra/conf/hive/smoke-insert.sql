USE bda_sales;
INSERT INTO sales_fact_daily PARTITION (batch_id='smoke')
SELECT '2026-01-01' AS sale_date, 'P1' AS product_id, 'Widget' AS product_name,
       'Cat' AS category, 'North' AS region, 10.0 AS revenue, 2 AS quantity, 1 AS orders;
SELECT sale_date, product_id, revenue, quantity, orders
FROM sales_fact_daily WHERE batch_id='smoke';
