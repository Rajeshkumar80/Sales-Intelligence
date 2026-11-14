#!/usr/bin/env bash
# Sourced by every BDA shell. No sudo.

export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export BDA_HOME="$HOME/BDA-Projects"
export HADOOP_HOME="$BDA_HOME/infra/installed/hadoop"
export HIVE_HOME="$BDA_HOME/infra/installed/hive"
export MAVEN_HOME="$BDA_HOME/infra/installed/maven"

export HADOOP_CONF_DIR="$BDA_HOME/infra/conf/hadoop"
export YARN_CONF_DIR="$HADOOP_CONF_DIR"
export HIVE_CONF_DIR="$BDA_HOME/infra/conf/hive"

export HADOOP_LOG_DIR="$BDA_HOME/infra/logs/hadoop"
export HADOOP_PID_DIR="$BDA_HOME/infra/run"
export HIVE_LOG_DIR="$BDA_HOME/infra/logs/hive"
export HIVE_PID_DIR="$BDA_HOME/infra/run"

export PATH="$MAVEN_HOME/bin:$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$HIVE_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$HADOOP_HOME/lib/native:${LD_LIBRARY_PATH:-}"

# nvm / Node 24 (user-level). Do not use the Windows npm on /mnt/c.
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  . "$NVM_DIR/nvm.sh"
fi
