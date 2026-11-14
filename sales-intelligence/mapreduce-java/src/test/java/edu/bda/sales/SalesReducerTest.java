package edu.bda.sales;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

import java.util.Arrays;

import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Reducer;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

class SalesReducerTest {

    @SuppressWarnings("unchecked")
    private final Reducer<Text, ProductRevenueWritable, Text, ProductRevenueWritable>.Context ctx =
            (Reducer<Text, ProductRevenueWritable, Text, ProductRevenueWritable>.Context) mock(Reducer.Context.class);

    private final SalesReducer reducer = new SalesReducer();

    @Test
    void sumsRevenueQuantityAndOrdersPerProduct() throws Exception {
        Iterable<ProductRevenueWritable> values = Arrays.asList(
                new ProductRevenueWritable("Keyboard", 76.5, 3, 1),
                new ProductRevenueWritable("Keyboard", 25.5, 1, 1),
                new ProductRevenueWritable("Keyboard", 0.1, 1, 1),
                new ProductRevenueWritable("Keyboard", 0.2, 1, 1));

        reducer.reduce(new Text("P-100"), values, ctx);

        ArgumentCaptor<ProductRevenueWritable> out = ArgumentCaptor.forClass(ProductRevenueWritable.class);
        verify(ctx).write(org.mockito.ArgumentMatchers.eq(new Text("P-100")), out.capture());

        assertEquals(102.3, out.getValue().getRevenue(), 1e-9); // rounded, not 102.30000000000001
        assertEquals(6, out.getValue().getQuantity());
        assertEquals(4, out.getValue().getOrders());
        assertEquals("Keyboard", out.getValue().getProductName());
    }

    @Test
    void writesTabSeparatedLineHiveCanRead() {
        ProductRevenueWritable v = new ProductRevenueWritable("Cable, USB-C", 12.0, 2, 1);
        v.roundRevenue();
        assertEquals("Cable, USB-C\t12.0\t2\t1", v.toString());
    }
}
