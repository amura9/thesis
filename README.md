
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

---

# Project Architecture

The platform follows a modular architecture that separates frontend presentation logic from backend evaluation services.

## Backend

The backend is implemented using:

* FastAPI
* Python
* REST API architecture
* Dynamic report generation
* Evaluation and scoring services

## Frontend

The frontend is implemented using:

* Vue.js
* Vite
* Dynamic visualization components
* Modular UI architecture

---

# Development Notes

* The backend and frontend must run simultaneously during development.
* Hot-reload functionality is enabled both for FastAPI and Vite.
* The modular architecture simplifies future extensions and maintenance.

---

# Future Improvements

Potential future extensions include:

* Authentication and user management
* Persistent database integration
* Advanced analytics dashboards
* Plugin-based evaluation modules
* Cloud deployment support

---

# License

This project was developed as part of a Master's Thesis research project.


#BACKEND
#if neeeded -> create (at \backend) .venv on CLI-> py -m venv .venv
#alternative if python not on path, create .venv with powershell: py -m venv .venv


#Go to: 
\backend
#venv:
venv\Scripts\Activate.ps1
#run:
uvicorn main:app --reload -> run at localhost:8000


#Dependencies install: 
fastapi, uvicorn, pandas, openpyxl, python-multipart


#FRONTEND
#Go to: 
\frontend 
#venv
venv\Scripts\Activate.ps1
#run:
npm run dev
#Check if frontend running in: 
http://localhost:5173/

#install: npm install vue-router@4, npm i xlsx

#pip install: polaywright, python -m playwright install chromium 



----
TO Do: 
- Binning, 1HE 