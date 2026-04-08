## About the project
<img width="940" height="733" alt="a verfiied shopping receipt scanner" src="https://github.com/user-attachments/assets/67da5afc-ee15-4e22-98e7-4a88df222ace" />
<img width="373" height="667" alt="image" src="https://github.com/user-attachments/assets/bc8d440d-2342-43d5-a326-d5b8407be185" />  <br />


The idea of this project came after noticing that I have a plenty of shopping receipts lying down on my desk. Initially, I was going to dump them all in a bin, but I realized these could help me build a project, so I came up with a shopping receipt scanner using OCR and LLM to extract information, then visualize them on dashboard. At first, I wanted to just use OpenClaw, but since I only use Ollama cloud, the token usage may hit the ceiiling in no time, so I decided to use an OCR combined with LLM. I have been aware of the challenges, but that is why I want to dive into AI Engineering. So far, the PoC is done and I can use it for my daily life. I will also be adding some more features to improve my current project.

### Built with
* ![React](https://img.shields.io/badge/react-20232A?style=flat&logo=react&logoColor=61DAFB)
* ![Hono](https://img.shields.io/badge/hono-ff6b00?style=flat)
* ![FastAPI](https://img.shields.io/badge/fastapi-009688?style=flat&logo=fastapi&logoColor=white)
* ![Supabase](https://img.shields.io/badge/supabase-3ECF8E?style=flat&logo=supabase&logoColor=white)
* ![OpenCV](https://img.shields.io/badge/opencv-5C3EE8?style=flat&logo=opencv&logoColor=white)
* ![RapidOCR](https://img.shields.io/badge/rapidocr-gray?style=flat)
* ![Ollama](https://img.shields.io/badge/ollama-black?style=flat)

## Getting Started
This project is using Cloudflare as the deployment, Supabase as the database, Telegram as the bot, and Ollama as the LLM thus a Cloudflare account, Supabase account, Telegram Bot Token, and Ollama account are required.
### Prerequisites
* [Bun](https://bun.com/docs/installation)
* [Wrangler](https://developers.cloudflare.com/workers/wrangler/install-and-update/)
* [uv](https://docs.astral.sh/uv/getting-started/installation/)

### Installation
1. cd to frontend
     ```sh
   cd frontend
   ```
2. add .env
   ```sh
   VITE_BACKEND_URL=your_backend_url
   VITE_STORAGE_KEY=your_randomized_openssl_rand
   ```
3. install the dependencies
     ```sh
   bun install && bun run dev
   ```
4. cd to backend
     ```sh
   cd backend
   ```
5. add .dev.vars
    ```sh
   SUPABASE_URL=yout_supabase_url
   SUPABASE_KEY=your_supabase_key
   ML_SERVICE=your_ml_service_url
   JWT_SECRET=your_generated_jwt_secret
   BOT_TOKEN=your_telegram_bot_token
   ```
6. install the dependencies
    ```sh
   bun install && bun run dev
   ```
7. cd to ml-service
     ```sh
   uv sync && uvicorn app.main:app --reload
   ```
8. add .env
     ```sh
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   OLLAMA_API_KEY=your_ollama_api_key
   BACKEND_URL=your_backend_url
   ```
> Temporarily the development of the ml-service is using polling as I am in the progress of deploying it to my homelab server. As soon as I do that, I will change the ml-service to run using a webhook instead.

## Features
- Receipt History allowing users to see the receipts data
- HITL (Human-In-The-Loop) enabling edit mode in the dashboard
- Status System -> Verified, Action Required

## To-Do-List Features
- Dashboard with graphs to track outcome / Analytics
- Category Breakdown

