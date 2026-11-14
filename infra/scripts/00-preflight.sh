#!/usr/bin/env bash
# Phase 2 pre-flight: read-only checks.
set -u

echo "== identity =="
id
echo "HOME=$HOME"
echo "PWD=$(pwd)"

echo
echo "== sudo (non-interactive) =="
if sudo -n true 2>/dev/null; then
  echo "sudo: passwordless available"
else
  echo "sudo: password required (interactive)"
fi

echo
echo "== java =="
java -version 2>&1 | head -3
readlink -f "$(command -v java)"
echo "JAVA_HOME=${JAVA_HOME:-<unset>}"

echo
echo "== memory / disk =="
free -h
df -h /home /mnt/c 2>/dev/null | tail -n +1

echo
echo "== ports =="
ss -ltnp 2>/dev/null | awk 'NR==1 || /:(27017|9870|8088|10000|7077|8080|9000|8020|19888|50070|8042|8032|9083)\b/'

echo
echo "== existing infra =="
ls -la "$HOME/BDA-Projects" 2>/dev/null
ls -la "$HOME/BDA-Projects/infra" 2>/dev/null || echo "infra: not created"

echo
echo "== commands =="
for c in curl wget tar git python3 node npm mvn mongod mongosh; do
  printf '%-8s ' "$c"
  command -v "$c" || echo "missing"
done
