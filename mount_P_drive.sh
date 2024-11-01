#!/bin/bash

if [ ! -d /mnt/P ]; then
  mkdir /mnt/P
fi
if ! mountpoint -q /mnt/P; then
  sudo mount -t drvfs "P:" /mnt/P
fi
if [ ! -d /mnt/P ] || ! mountpoint -q /mnt/P; then
  echo "The P: drive was not mounted."
  exit 0
fi