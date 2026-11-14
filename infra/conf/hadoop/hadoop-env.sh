#!/usr/bin/env bash
# Hadoop environment for JDK 17 + 7.4 GB WSL. Sourced by Hadoop scripts.

export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export HADOOP_HOME=/home/rajesh/BDA-Projects/infra/installed/hadoop
export HADOOP_CONF_DIR=/home/rajesh/BDA-Projects/infra/conf/hadoop
export HADOOP_LOG_DIR=/home/rajesh/BDA-Projects/infra/logs/hadoop
export HADOOP_PID_DIR=/home/rajesh/BDA-Projects/infra/run
export HADOOP_HEAPSIZE_MAX=384
export HADOOP_CLIENT_OPTS="-Xmx256m"

export HADOOP_JDK17_OPENS="--add-opens=java.base/java.lang=ALL-UNNAMED \
--add-opens=java.base/java.lang.reflect=ALL-UNNAMED \
--add-opens=java.base/java.io=ALL-UNNAMED \
--add-opens=java.base/java.net=ALL-UNNAMED \
--add-opens=java.base/java.nio=ALL-UNNAMED \
--add-opens=java.base/java.util=ALL-UNNAMED \
--add-opens=java.base/java.util.concurrent=ALL-UNNAMED \
--add-opens=java.base/java.util.concurrent.atomic=ALL-UNNAMED \
--add-opens=java.base/sun.nio.ch=ALL-UNNAMED \
--add-opens=java.base/sun.nio.cs=ALL-UNNAMED \
--add-opens=java.base/sun.security.action=ALL-UNNAMED \
--add-opens=java.base/sun.util.calendar=ALL-UNNAMED"

export HADOOP_OPTS="$HADOOP_JDK17_OPENS"

export HDFS_NAMENODE_OPTS="-Xmx256m -XX:+UseSerialGC $HADOOP_JDK17_OPENS"
export HDFS_DATANODE_OPTS="-Xmx384m -XX:+UseSerialGC $HADOOP_JDK17_OPENS"
export YARN_RESOURCEMANAGER_OPTS="-Xmx384m -XX:+UseSerialGC $HADOOP_JDK17_OPENS"
export YARN_NODEMANAGER_OPTS="-Xmx384m -XX:+UseSerialGC $HADOOP_JDK17_OPENS"
export MAPRED_HISTORYSERVER_OPTS="-Xmx256m -XX:+UseSerialGC $HADOOP_JDK17_OPENS"
