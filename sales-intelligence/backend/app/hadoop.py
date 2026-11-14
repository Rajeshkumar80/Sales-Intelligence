"""Thin subprocess wrappers around HDFS and the MapReduce jar."""

import csv
import io
import os
import subprocess
from pathlib import Path

from . import config


class HadoopError(RuntimeError):
    pass


def _run(cmd: list[str], timeout: int = 900) -> str:
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=config.hadoop_env(),
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        tail = " | ".join(detail[-6:]) if detail else "no output"
        raise HadoopError(f"{Path(cmd[0]).name} failed ({proc.returncode}): {tail}")
    return proc.stdout


def hdfs_mkdir(path: str) -> None:
    _run([str(config.HDFS_BIN), "dfs", "-mkdir", "-p", path], timeout=120)


def hdfs_put(local: Path, dest: str) -> None:
    _run([str(config.HDFS_BIN), "dfs", "-put", "-f", str(local), dest], timeout=300)


def hdfs_rm(path: str, recursive: bool = True) -> None:
    cmd = [str(config.HDFS_BIN), "dfs", "-rm", "-f"]
    if recursive:
        cmd.append("-r")
    cmd.append(path)
    _run(cmd, timeout=180)


def hdfs_cat(path: str) -> str:
    return _run([str(config.HDFS_BIN), "dfs", "-cat", path], timeout=300)


def hdfs_test(path: str) -> bool:
    proc = subprocess.run(
        [str(config.HDFS_BIN), "dfs", "-test", "-e", path],
        capture_output=True,
        text=True,
        env=config.hadoop_env(),
        timeout=60,
    )
    return proc.returncode == 0


def run_mr(batch_id: str, reducers: int = 1) -> dict:
    """Run the genuine MapReduce job on YARN for one batch partition."""
    if not config.MR_JAR.exists():
        raise HadoopError(
            f"MapReduce jar not found at {config.MR_JAR}. Run scripts/build.sh first."
        )
    output_dir = f"{config.HDFS_REVENUE}/batch_id={batch_id}"
    hdfs_rm(output_dir)
    cmd = [
        str(config.HADOOP_BIN),
        "jar",
        str(config.MR_JAR),
        "edu.bda.sales.SalesDriver",
        "-D",
        f"mapreduce.job.reduces={reducers}",
        "-D",
        "mapreduce.input.fileinputformat.split.maxsize=4194304",
        f"{config.HDFS_INPUT}/batch_id={batch_id}",
        output_dir,
    ]
    output = _run(cmd, timeout=1800)
    if "SALES_JOB_COUNTER" not in output:
        raise HadoopError("MapReduce job produced no counters")
    counters = {}
    for line in output.splitlines():
        if line.startswith("SALES_JOB_COUNTER "):
            key, _, value = line[len("SALES_JOB_COUNTER ") :].partition("=")
            counters[key.strip()] = int(value.strip())
    return {"output_dir": output_dir, "counters": counters}


def read_mr_output(batch_id: str) -> list[dict]:
    raw = hdfs_cat(f"{config.HDFS_REVENUE}/batch_id={batch_id}/part-r-00000")
    rows = []
    for record in csv.reader(io.StringIO(raw), delimiter="\t"):
        if len(record) != 5:
            continue
        product_id, name, revenue, quantity, orders = record
        rows.append(
            {
                "product_id": product_id,
                "product_name": name,
                "revenue": float(revenue),
                "quantity": int(quantity),
                "orders": int(orders),
            }
        )
    return rows


def jar_built() -> bool:
    return config.MR_JAR.exists()


def staging_path(batch_id: str) -> Path:
    directory = config.STAGING_DIR / batch_id
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "data.tsv"


def env_ready() -> dict:
    return {
        "hadoop_bin": str(config.HADOOP_BIN),
        "hadoop_bin_exists": os.access(config.HADOOP_BIN, os.X_OK),
        "hdfs_bin_exists": os.access(config.HDFS_BIN, os.X_OK),
        "beeline_exists": os.access(config.BEELINE_BIN, os.X_OK),
        "jar_built": jar_built(),
    }
