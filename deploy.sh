#!/bin/bash

# Exit on error
set -e

# Configuration
PROJECT_ID="fintech-ai-agent"
SERVICE_NAME="financial-co-pilot"
REGION="us-central1"
REPO_NAME="app-images"
IMAGE_NAME="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$SERVICE_NAME"

echo "----------------------------------------------------------"
echo "🚀 Starting deployment for $SERVICE_NAME to Google Cloud Run"
echo "----------------------------------------------------------"

# Set Google Cloud Project
echo "📍 Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# Enable APIs
echo "⚙️ Enabling necessary Google Cloud APIs..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

# Create Artifact Registry repository if it doesn't exist
echo "📦 Ensuring Artifact Registry repository exists..."
gcloud artifacts repositories create $REPO_NAME \
    --repository-format=docker \
    --location=$REGION \
    --description="Docker repository for Cloud Run images" \
    || echo "Repository already exists"

# Build the container image using Cloud Build
echo "🏗️ Building container image..."
gcloud builds submit --tag $IMAGE_NAME

# Deploy to Cloud Run
# We pass the environment variables from your .env file
echo "🚢 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars "GEMINI_API_KEY=AIzaSyBT9YFgW_zB_ilb74HhykiMQvYGvxwpOY8,GEMINI_MODEL=gemini-3-flash-preview,GOOGLE_CLOUD_PROJECT=fintech-ai-agent"

echo "----------------------------------------------------------"
echo "✅ Deployment successful!"
echo "----------------------------------------------------------"
