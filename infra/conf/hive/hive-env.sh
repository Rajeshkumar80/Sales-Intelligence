#!/usr/bin/env bash
# Hive environment for JDK 17 + 7.4 GB WSL. Sourced by Hive scripts.

export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export HADOOP_HOME=/home/rajesh/BDA-Projects/infra/installed/hadoop
export HADOOP_CONF_DIR=/home/rajesh/BDA-Projects/infra/conf/hadoop
export HIVE_HOME=/home/rajesh/BDA-Projects/infra/installed/hive
export HIVE_CONF_DIR=/home/rajesh/BDA-Projects/infra/conf/hive
export HIVE_LOG_DIR=/home/rajesh/BDA-Projects/infra/logs/hive
export HIVE_PID_DIR=/home/rajesh/BDA-Projects/infra/run
export HADOOP_MAPRED_HOME=/home/rajesh/BDA-Projects/infra/installed/hadoop

export HIVE_JDK17_OPENS="--add-opens=java.base/java.lang=ALL-UNNAMED \
--add-opens=java.base/java.lang.reflect=ALL-UNNAMED \
--add-opens=java.base/java.lang.invoke=ALL-UNNAMED \
--add-opens=java.base/java.io=ALL-UNNAMED \
--add-opens=java.base/java.net=ALL-UNNAMED \
--add-opens=java.base/java.nio=ALL-UNNAMED \
--add-opens=java.base/java.util=ALL-UNNAMED \
--add-opens=java.base/java.util.concurrent=ALL-UNNAMED \
--add-opens=java.base/sun.nio.ch=ALL-UNNAMED \
--add-opens=java.base/sun.nio.cs=ALL-UNNAMED \
--add-opens=java.base/sun.security.action=ALL-UNNAMED \
--add-opens=java.base/sun.util.calendar=ALL-UNNAMED \
--add-opens=java.sql/java.sql=ALL-UNNAMED"

# JVM flags must go in HADOOP_CLIENT_OPTS. Hive's launcher appends HIVE_OPTS
# *after* the main class, so JVM flags there fail with "Unrecognized option".
export HADOOP_CLIENT_OPTS="-Xmx768m $HIVE_JDK17_OPENS"
