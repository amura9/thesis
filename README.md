
# Prerequisites

Before running the project locally, ensure that the following dependencies are installed:

* **Node.js** (v16 or higher)
* **npm**
* **Python** (3.9 or higher)

---

# How to Run the Project (Local Development)

The platform requires both the backend server and the frontend development server to run simultaneously in separate terminal windows.

---

## 1. Start the Backend (FastAPI / Python)

Open a terminal, navigate to the root directory of the project, and execute the following commands:

```bash
# Create a virtual environment (recommended)
python -m venv venv

# Activate the virtual environment
# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Start the FastAPI server
uvicorn backend.main:app --reload --port 8000
```

The backend server will run locally on:

```text
http://localhost:8000
```

---

## 2. Start the Frontend (Vue.js / Vite)

Open a second terminal and navigate to the frontend directory:

```bash
cd frontend
```

Install the required Node.js dependencies:

```bash
npm install
```

Start the Vite development server:

```bash
npm run dev
```

The frontend application will usually be available at:

```text
http://localhost:5173
```

