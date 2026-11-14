package edu.bda.sales;

import java.io.DataInput;
import java.io.DataOutput;
import java.io.IOException;
import java.util.Objects;

import org.apache.hadoop.io.Writable;

/**
 * Per-product aggregate emitted by the mapper (one order) and summed by the
 * reducer (all orders). Order count is carried so the reducer never needs to
 * re-read the raw data.
 */
public class ProductRevenueWritable implements Writable {

    private String productName = "";
    private double revenue;
    private long quantity;
    private long orders;

    public ProductRevenueWritable() {
    }

    public ProductRevenueWritable(String productName, double revenue, long quantity, long orders) {
        this.productName = productName == null ? "" : productName;
        this.revenue = revenue;
        this.quantity = quantity;
        this.orders = orders;
    }

    public void add(ProductRevenueWritable other) {
        if (productName.isEmpty()) {
            productName = other.productName;
        }
        revenue += other.revenue;
        quantity += other.quantity;
        orders += other.orders;
    }

    /** Money is rounded to 2 decimals so Hive and Mongo comparisons are exact. */
    public void roundRevenue() {
        revenue = Math.round(revenue * 100.0) / 100.0;
    }

    public String getProductName() {
        return productName;
    }

    public double getRevenue() {
        return revenue;
    }

    public long getQuantity() {
        return quantity;
    }

    public long getOrders() {
        return orders;
    }

    @Override
    public void write(DataOutput out) throws IOException {
        out.writeUTF(productName);
        out.writeDouble(revenue);
        out.writeLong(quantity);
        out.writeLong(orders);
    }

    @Override
    public void readFields(DataInput in) throws IOException {
        productName = in.readUTF();
        revenue = in.readDouble();
        quantity = in.readLong();
        orders = in.readLong();
    }

    /** Tab-separated so product names containing commas cannot corrupt Hive. */
    @Override
    public String toString() {
        return productName + "\t" + revenue + "\t" + quantity + "\t" + orders;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (!(o instanceof ProductRevenueWritable other)) {
            return false;
        }
        return Double.compare(revenue, other.revenue) == 0
                && quantity == other.quantity
                && orders == other.orders
                && productName.equals(other.productName);
    }

    @Override
    public int hashCode() {
        return Objects.hash(productName, revenue, quantity, orders);
    }
}
