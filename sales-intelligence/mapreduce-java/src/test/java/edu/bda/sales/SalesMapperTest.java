package edu.bda.sales;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Counter;
import org.apache.hadoop.mapreduce.Mapper;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

class SalesMapperTest {

    @SuppressWarnings("unchecked")
    private final Mapper<LongWritable, Text, Text, ProductRevenueWritable>.Context ctx =
            (Mapper<LongWritable, Text, Text, ProductRevenueWritable>.Context) mock(Mapper.Context.class);

    private final SalesMapper mapper = new SalesMapper();

    private static String row(String id, String productId, String name, int qty, double price) {
        return id + "\t" + productId + "\t" + name + "\tElectronics\t" + qty + "\t" + price
                + "\tNorth\t1767225600000";
    }

    @Test
    void emitsQuantityTimesUnitPriceKeyedByProductId() throws Exception {
        mapper.map(new LongWritable(0), new Text(row("T1", "P-100", "Keyboard", 3, 25.50)), ctx);

        ArgumentCaptor<Text> key = ArgumentCaptor.forClass(Text.class);
        ArgumentCaptor<ProductRevenueWritable> value = ArgumentCaptor.forClass(ProductRevenueWritable.class);
        verify(ctx).write(key.capture(), value.capture());

        assertEquals("P-100", key.getValue().toString());
        assertEquals(76.5, value.getValue().getRevenue(), 1e-9);
        assertEquals(3, value.getValue().getQuantity());
        assertEquals(1, value.getValue().getOrders());
        assertEquals("Keyboard", value.getValue().getProductName());
    }

    @Test
    void skipsHeaderAndMalformedRows() throws Exception {
        Counter malformed = mock(Counter.class);
        Counter invalid = mock(Counter.class);
        when(ctx.getCounter(SalesMapper.COUNTER_GROUP, SalesMapper.MALFORMED)).thenReturn(malformed);
        when(ctx.getCounter(SalesMapper.COUNTER_GROUP, SalesMapper.INVALID_VALUES)).thenReturn(invalid);

        mapper.map(new LongWritable(0),
                new Text("transaction_id\tproduct_id\tproduct_name\tcategory\tquantity\tunit_price\tregion\ttimestamp_ms"),
                ctx);
        mapper.map(new LongWritable(1), new Text("T2\tP-100\tBroken row"), ctx);
        mapper.map(new LongWritable(2), new Text(row("T3", "P-100", "Keyboard", 0, 10.0)), ctx);

        verify(ctx, never()).write(org.mockito.ArgumentMatchers.any(), org.mockito.ArgumentMatchers.any());
        verify(malformed).increment(1);
        verify(invalid).increment(1);
    }
}
