package edu.bda.sales;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.conf.Configured;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;
import org.apache.hadoop.util.Tool;
import org.apache.hadoop.util.ToolRunner;

/**
 * Runs the sales revenue job on HDFS/YARN.
 *
 * <p>Usage: hadoop jar sales-mapreduce.jar input_dir output_dir
 *
 * <p>Output line: {@code product_id \t product_name \t revenue \t quantity \t orders}
 */
public class SalesDriver extends Configured implements Tool {

    @Override
    public int run(String[] args) throws Exception {
        if (args.length != 2) {
            System.err.println("Usage: SalesDriver <input_dir> <output_dir>");
            return 2;
        }

        Configuration conf = getConf();
        Job job = Job.getInstance(conf, "sales revenue by product");
        job.setJarByClass(SalesDriver.class);

        job.setMapperClass(SalesMapper.class);
        job.setReducerClass(SalesReducer.class);

        job.setMapOutputKeyClass(Text.class);
        job.setMapOutputValueClass(ProductRevenueWritable.class);
        job.setOutputKeyClass(Text.class);
        job.setOutputValueClass(ProductRevenueWritable.class);

        FileInputFormat.addInputPath(job, new Path(args[0]));
        FileOutputFormat.setOutputPath(job, new Path(args[1]));

        boolean ok = job.waitForCompletion(true);
        System.out.println("SALES_JOB_COUNTER product_rows="
                + job.getCounters().findCounter("org.apache.hadoop.mapreduce.TaskCounter", "MAP_OUTPUT_RECORDS")
                        .getValue());
        System.out.println("SALES_JOB_COUNTER malformed_rows="
                + job.getCounters().findCounter(SalesMapper.COUNTER_GROUP, SalesMapper.MALFORMED).getValue());
        System.out.println("SALES_JOB_COUNTER invalid_rows="
                + job.getCounters().findCounter(SalesMapper.COUNTER_GROUP, SalesMapper.INVALID_VALUES).getValue());
        return ok ? 0 : 1;
    }

    public static void main(String[] args) throws Exception {
        System.exit(ToolRunner.run(new Configuration(), new SalesDriver(), args));
    }
}
