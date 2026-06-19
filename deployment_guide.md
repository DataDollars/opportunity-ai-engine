# SaaS Platform End-to-End Deployment Guide

This guide documents the entire architecture and hosting process for the **AI Opportunity Intelligence SaaS Platform**, consisting of the **Next.js frontend** on Firebase Hosting, the **FastAPI backend** on Render, and the **Cloud Firestore database** on Firebase.

---

## 1. System Architecture Overview

```mermaid
graph TD
    A[Next.js Frontend App<br/>Firebase Hosting] -->|HTTPS Requests| B[FastAPI Backend Server<br/>Render Web Service]
    B -->|Fetch/Write| C[Cloud Firestore DB<br/>Firebase / Google Cloud]
    B -->|Structured Parsing| D[Google Gemini API]
    B -->|Similarity Metrics| E[Hugging Face Inference API]
    F[GitHub Actions Workflows] -->|CD Deploy| A
    F -->|Daily Sync Trigger| B
```

---

## 2. Step 1: Deploying the FastAPI Backend to Render

We have included a `render.yaml` Blueprint file at the root of the repository to automate this setup.

### Instructions:
1. Log in or sign up at **[Render](https://render.com/)**.
2. Click **New** (top-right button) -> **Blueprint**.
3. Connect your GitHub repository: `https://github.com/DataDollars/opportunity-ai-engine.git`.
4. Render will read the `render.yaml` file and prompt you to enter the required environment variables:
   - `GEMINI_API_KEY`: Paste your Gemini API key: `AIzaSyBi1vUc8p7QS6N8TtbfXKAraaq9zEYMvOI`.
   - `FIREBASE_CREDENTIALS_JSON`: Paste the **raw contents** of your `key.json` file (the Firebase Service Account JSON credentials).
   - `HUGGINGFACE_API_KEY`: (Optional) Paste a Hugging Face API Token to enable live semantic vector search. If left empty, the backend automatically uses the offline synonym-expanded fallback.
5. Click **Approve** / **Apply**. Render will build and deploy the FastAPI backend.
6. Once deployed, note down your Render Web Service URL (e.g. `https://opportunity-ai-backend.onrender.com`).

---

## 3. Step 2: Configuring GitHub Actions Secrets

Now, you need to link your GitHub repository to Firebase and your Render backend.

### Instructions:
1. Go to your GitHub repository: [https://github.com/DataDollars/opportunity-ai-engine](https://github.com/DataDollars/opportunity-ai-engine).
2. Navigate to **Settings** -> **Secrets and variables** -> **Actions**.
3. Add the following **Repository Secrets** (click *New repository secret*):

| Secret Name | Value to Paste | Description |
| :--- | :--- | :--- |
| `FIREBASE_SERVICE_ACCOUNT_OPPORTUNITY_AI_ENGINE` | Copy the entire contents of your local `key.json` file. | Used to authenticate and publish the Next.js static files to Firebase Hosting. |
| `NEXT_PUBLIC_API_URL` | Paste your live **Render Web Service URL** (e.g. `https://opportunity-ai-backend.onrender.com`). | Instructs the frontend app on where to send HTTP requests to query opportunities. |
| `BACKEND_URL` | Paste your live **Render Web Service URL** (e.g. `https://opportunity-ai-backend.onrender.com`). | Used by the daily cron sync workflow to trigger the crawlers pipeline. |

---

## 4. Step 3: Triggering Automated Frontend Deployment

Once the secrets are configured:
1. The GitHub Actions workflow [.github/workflows/firebase-deploy.yml](file:///.github/workflows/firebase-deploy.yml) will trigger automatically whenever you push code changes to `master`.
2. To trigger a deployment manually, go to the **Actions** tab in your GitHub repository, select **Deploy to Firebase Hosting**, and click **Run workflow**.

Once complete, your updated Next.js app will be live and talking to your Render backend at:
👉 **[https://opportunity-ai-engine.web.app](https://opportunity-ai-engine.web.app)**

---

## 5. Summary of URLs

- **Firestore Database Console**: [https://console.firebase.google.com/project/opportunity-ai-engine/firestore](https://console.firebase.google.com/project/opportunity-ai-engine/firestore)
- **Firebase Hosting Console**: [https://console.firebase.google.com/project/opportunity-ai-engine/hosting/main](https://console.firebase.google.com/project/opportunity-ai-engine/hosting/main)
- **Live Frontend App**: [https://opportunity-ai-engine.web.app](https://opportunity-ai-engine.web.app)
- **Live Backend Server (Render)**: Run through your Render dashboard to get the unique domain.
- **GitHub Repository**: [https://github.com/DataDollars/opportunity-ai-engine](https://github.com/DataDollars/opportunity-ai-engine)
