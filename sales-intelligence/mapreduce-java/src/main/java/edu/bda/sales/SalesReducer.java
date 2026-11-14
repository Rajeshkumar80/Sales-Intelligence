package edu.bda.sales;

import java.io.IOException;

import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Reducer;

/**
 * Sums revenue, quantity and order count for every product ID.
 */
public class SalesReducer extends Reducer<Text, ProductRevenueWritable, Text, ProductRevenueWritable> {

    @Override
    protected void reduce(Text key, Iterable<ProductRevenueWritable> values, Context context)
            throws IOException, InterruptedException {

        String name = "";
        double revenue = 0.0;
        long quantity = 0;
        long orders = 0;

        for (ProductRevenueWritable v : values) {
            if (name.isEmpty()) {
                name = v.getProductName();
            }
            revenue += v.getRevenue();
            quantity += v.getQuantity();
            orders += v.getOrders();
        }

        ProductRevenueWritable total = new ProductRevenueWritable(name, revenue, quantity, orders);
        total.roundRevenue();
        context.write(key, total);
    }
}
