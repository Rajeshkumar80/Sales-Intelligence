package edu.bda.sales;

import java.io.IOException;

import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Mapper;

/**
 * Reads one transaction per line (TSV, no header in HDFS) and emits
 * product_id -> quantity x unit_price plus the quantity and order count.
 */
public class SalesMapper extends Mapper<LongWritable, Text, Text, ProductRevenueWritable> {

    static final String COUNTER_GROUP = "SALES";
    static final String MALFORMED = "MALFORMED_ROWS";
    static final String INVALID_VALUES = "INVALID_QUANTITY_OR_PRICE";

    private final Text outKey = new Text();

    @Override
    protected void map(LongWritable key, Text value, Context context)
            throws IOException, InterruptedException {

        String line = value.toString().trim();
        if (line.isEmpty() || line.startsWith("transaction_id")) {
            return;
        }

        String[] f = line.split("\t", -1);
        if (f.length < 8) {
            context.getCounter(COUNTER_GROUP, MALFORMED).increment(1);
            return;
        }

        String productId = f[1].trim();
        String productName = f[2].trim();
        int quantity;
        double unitPrice;
        try {
            quantity = Integer.parseInt(f[4].trim());
            unitPrice = Double.parseDouble(f[5].trim());
        } catch (NumberFormatException e) {
            context.getCounter(COUNTER_GROUP, MALFORMED).increment(1);
            return;
        }

        if (productId.isEmpty() || quantity <= 0 || unitPrice < 0) {
            context.getCounter(COUNTER_GROUP, INVALID_VALUES).increment(1);
            return;
        }

        outKey.set(productId);
        context.write(outKey, new ProductRevenueWritable(productName, quantity * unitPrice, quantity, 1));
    }
}
