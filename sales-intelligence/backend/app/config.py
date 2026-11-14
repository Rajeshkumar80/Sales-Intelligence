"""Configuration loaded from .env. Credentials are never logged or returned."""

import os
import urllib.parse
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
REPO_DIR = PROJECT_DIR.parent

for candidate in (BACKEND_DIR / ".env", REPO_DIR / ".env"):
    if candidate.exists():
        load_dotenv(candidate, override=False)

BDA_HOME = Path(os.getenv("BDA_HOME", Path.home() / "BDA-Projects"))
HADOOP_BIN = BDA_HOME / "infra/installed/hadoop/bin/hadoop"
HDFS_BIN = BDA_HOME / "infra/installed/hadoop/bin/hdfs"
BEELINE_BIN = BDA_HOME / "infra/installed/hive/bin/beeline"
MR_JAR = PROJECT_DIR / "mapreduce-java/target/sales-mapreduce.jar"
STAGING_DIR = BDA_HOME / "infra/data/sales-staging"
JAVA_HOME = os.getenv("JAVA_HOME", str(BDA_HOME / "infra/installed/java"))

HDFS_INPUT = "/bda/sales/input"
HDFS_REVENUE = "/bda/sales/revenue"
HIVE_DB = "bda_sales"
HIVE_URL = os.getenv("HIVE_URL", "jdbc:hive2://127.0.0.1:10000/default")

BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5000"))
MONGO_DB = os.getenv("MONGODB_DB", "bda_sales")
SIMULATOR_INTERVAL = float(os.getenv("SIMULATOR_INTERVAL_SECONDS", "5"))
SIMULATOR_BATCH = int(os.getenv("SIMULATOR_BATCH_SIZE", "20"))
CSV_MAX_BYTES = int(os.getenv("CSV_MAX_BYTES", str(5 * 1024 * 1024)))
CSV_MAX_ROWS = int(os.getenv("CSV_MAX_ROWS", "50000"))


class ConfigError(RuntimeError):
    pass


def mongo_uri() -> str:
    """Build the Atlas URI at call time so the password never lives in a module constant."""
    explicit = os.getenv("MONGODB_URI")
    if explicit:
        return explicit
    host = os.getenv("MONGODB_HOST")
    user = os.getenv("MONGODB_USERNAME")
    password = os.getenv("MONGODB_PASSWORD")
    if not host or not user or not password:
        raise ConfigError(
            "MongoDB configuration missing. Create sales-intelligence/backend/.env "
            "from .env.example and set MONGODB_HOST, MONGODB_USERNAME and MONGODB_PASSWORD."
        )
    return (
        "mongodb+srv://"
        f"{urllib.parse.quote(user, safe='')}:{urllib.parse.quote(password, safe='')}"
        f"@{host}/{os.getenv('MONGODB_DB', 'bda_sales')}"        "?retryWrites=true&w=majority&appName=BDA-Sales"
    )


def hadoop_env() -> dict:
    env = dict(os.environ)
    env["JAVA_HOME"] = JAVA_HOME
    env["PATH"] = f"{HADOOP_BIN.parent}:{BEELINE_BIN.parent}:{env.get('PATH', '')}"
    env.setdefault("HADOOP_CONF_DIR", str(BDA_HOME / "infra/conf/hadoop"))
    env.setdefault("HIVE_CONF_DIR", str(BDA_HOME / "infra/conf/hive"))
    return env
