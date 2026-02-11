#!/bin/bash
# Deployment Script for AI Site Coordinator

# Define project directory
PROJECT_DIR="/home/server-admin/AI_Site_Coordinator"

echo "Deploying to $PROJECT_DIR..."

if [ -d "$PROJECT_DIR" ]; then
    cd "$PROJECT_DIR" || exit
    echo "Pulling latest changes from GitHub..."
    git pull
else
    echo "Project directory not found! Cloning..."
    git clone https://github.com/Thulfiqar87/TelegramBot_AI_Engineer.git "$PROJECT_DIR"
    cd "$PROJECT_DIR" || exit
fi

echo "Building and restarting Docker containers..."
docker compose down
docker compose up -d --build

echo "Deployment complete! 🚀"
