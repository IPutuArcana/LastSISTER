#!/usr/bin/env bash
# Regenerate gRPC stubs dari proto/scheduler.proto ke tiap service.
set -e
python3 -m grpc_tools.protoc -I proto \
  --python_out=. --grpc_python_out=. proto/scheduler.proto
cp scheduler_pb2.py scheduler_pb2_grpc.py booking-service/
cp scheduler_pb2.py scheduler_pb2_grpc.py scheduler-service/
rm scheduler_pb2.py scheduler_pb2_grpc.py
echo "Stubs regenerated."
