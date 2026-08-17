# PhonicsMaker Core Backend

https://www.phonicsmaker.com

PhonicsMaker Core is the backend service for generating phonics-based children's stories and illustrations. It uses AI to create customized stories with phoneme emphasis and difficulty-level adjustments, supporting educators and children in interactive phonics learning.

---

## 🚀 Features

- **Story Generation**

  - Phoneme-based customization
  - Multi-level difficulty settings (Foundation, Year 1, Year 2)
  - AI-driven content generation
  - PDF compilation for print-ready children's books

- **AI-Powered Analysis**

  - LLM integration (OpenAI GPT 4o)
  - Custom prompt engineering
  - Text-to-image illustration generation

- **Smart Content Creation**
  - Story text generation
  - AI-generated illustrations (OpenAI Dall E)
  - Image-text consistency validation (OpenAI GPT 4o vision)
  - Print-ready PDF formatting (WeasyPrint)

## 🛠️ Tech Stack

- Python FastAPI
- Redis (for task queueing)
- Celery (task management)
- OpenAI API
- Docker

---

## 💻 Local Development

### Prerequisites

- Python 3.8+
- poetry
- Virtual environment

### Quick Start

1. **Clone the Repository**

   ```bash
   git clone https://github.com/phonicsmaker/phonicsmaker-core
   cd phonicsmaker-core
   ```

2. **Set Up Virtual Environment**

   ```bash
   poetry shell
   poetry install
   ```

3. **Configure Environment Variables**  
   Create a `.env` file in the project root:

   ```bash
   OPENAI_API_KEY=your_openai_api_key
   REDIS_URL=redis://localhost:6379/0
   ```

4. **Run Local Server**

   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. **Run Celery Workers**

   ```bash
   celery -A main.celery_app worker --loglevel=info -Q story_generation --concurrency=2
   ```

   **Explanation of Celery Command Parameters:**

   - `worker`: Starts Celery in worker mode to process tasks.
   - `-Q story_generation`: Specifies the queue (`story_generation`) that the worker will process tasks from.
   - `--concurrency=2`: Allows the worker to process 2 tasks concurrently.

---

## 📁 Project Structure

```
main.py
app/
├── core/
│   ├── ai/                   # AI integration
│   │   ├── ai_config.py      # AI configuration and client setup
│   │   ├── prompts.py        # Prompt templates for story and image generation
│   │   ├── input_service.py  # Service for validating and processing user inputs
│   ├── api/
│   │   ├── routes.py         # API endpoints for story generation and task management
│   ├── auth/
│   │   ├── auth_service.py   # Authentication and user token management
│   ├── config/
│   │   ├── celery_config.py  # Celery configuration for task queueing
│   │   ├── config.py         # Application configuration and settings
│   │   ├── logger.py         # Logging configuration
│   ├── error_handling/
│   │   ├── error_service.py  # Error handling and logging
│   ├── user/
│   │   ├── user_service.py   # User management and preferences
├── db/
│   ├── database.py           # Database connection and session management
│   ├── models/               # Database models
│   │   ├── api.py            # API request and response models
│   │   ├── basic.py          # Basic user and subscription models
│   │   ├── image.py          # Image generation and validation models
│   │   ├── pdf.py            # PDF generation models
│   │   ├── story.py          # Story generation models
│   │   ├── task.py           # Task management models
│   ├── redis_service.py      # Redis service for task and cache management
├── phonics_maker/
│   ├── image_generation/
│   │   ├── image_service.py  # Service for generating and validating images
│   ├── input_processing/
│   │   ├── input_service.py  # Service for validating and processing user inputs
│   ├── pdf_generation/
│   │   ├── pdf_service.py    # PDF generation utility functions
│   │   ├── html_renderer.py  # HTML template rendering
│   │   ├── pdf_generator.py  # PDF file generation from HTML
│   │   ├── text_processor.py # Text processing for images and covers
│   │   ├── file_utils.py     # File system operations for PDF workflow
│   ├── story_generation/
│   │   ├── story_service.py  # Service for generating phonics-based stories
│   ├── task_management/
│   │   ├── task_service.py   # Service for managing task progress and status
│   ├── tasks/
│   │   ├── story_tasks.py    # Celery tasks for story generation workflow
```

---

## 🐳 Docker Deployment

1. **Build Image**

   ```bash
   docker build -t phonicsmaker-core .
   ```

2. **Run Container**

   ```bash
   docker run -p 8000:8000 --env-file .env phonicsmaker-core
   ```

---

## 📝 API Documentation

API documentation is available at:

- Development: `http://localhost:8000/docs`
- Production: `https://api.phonicsmaker.com/docs`

---

Built with ❤️ to inspire phonics learning through stories and illustrations.
