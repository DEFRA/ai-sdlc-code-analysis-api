#!/bin/bash

# Exit on error
set -e

echo "Starting development environment..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Start dependent services
echo "Starting dependent services with Docker Compose..."
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 5

# Set environment variables for local development
export PORT=8085
export LOCALSTACK_ENDPOINT=http://localhost:4566
export MONGO_URI=mongodb://localhost:27017/

# Load application environment variables
echo "Loading environment variables..."
if [ -f compose/aws.env ]; then
    export $(grep -v '^#' compose/aws.env | xargs)
else
    echo "Error: compose/aws.env file not found. This file is required."
    exit 1
fi

echo "Loading secrets..."
if [ -f compose/secrets.env ]; then
    export $(grep -v '^#' compose/secrets.env | xargs)
else
    echo "Error: compose/secrets.env file not found. This file is required."
    exit 1
fi

# Check Python virtual environment exists
if [ ! -d ".venv" ]; then
    echo "No Python virtual environment found. Please setup your environment as per the README."
    exit 1
fi

# Start the application
echo "Starting FastAPI application with Uvicorn..."
uvicorn app.main:app --host 0.0.0.0 --port $PORT --reload

# Cleanup function
cleanup() {
    echo "Shutting down..."
    deactivate
    echo "Development server stopped."
}

# Register cleanup function
trap cleanup EXIT
