# Placement & Interview Management System

A full-stack CSE/IT portfolio project for managing student placements, recruiters, job openings, applications, interview schedules, evaluations and final selection.

## Tech Stack
- Frontend: React + Vite
- Backend: FastAPI
- Database: SQLite (easy local setup; can be switched to PostgreSQL)
- Authentication: JWT
- API: REST
- Deployment: Render-ready

## Modules
1. Student registration/login
2. Recruiter registration/login
3. Admin dashboard
4. Job posting
5. Student applications
6. Candidate shortlisting
7. Interview scheduling
8. Interviewer evaluation
9. Selection/rejection tracking
10. Placement statistics

## Run Backend
```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend: http://127.0.0.1:8000
API docs: http://127.0.0.1:8000/docs

## Run Frontend
```bash
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173

## GitHub
```bash
git init
git add .
git commit -m "Initial placement interview management system"
git branch -M main
git remote add origin YOUR_GITHUB_URL
git push -u origin main
```

## Deployment

The PlacementHub frontend and backend are deployed separately on Render.

### Live Demo

**Frontend:**
https://placementhub-frontend-uu1q.onrender.com

**Backend API:**
https://placementhub-backend-x16w.onrender.com

**API Documentation (Swagger):**
https://placementhub-backend-x16w.onrender.com/docs

### Demo Login

For security, this repository does not contain passwords or private credentials.

You can register a new Student or Recruiter account directly from the live application and use the system.

### Demo Workflow

1. Register/Login as a Recruiter.
2. Create a job.
3. Register/Login as a Student.
4. Apply for the job.
5. Login as Recruiter and shortlist the applicant.
6. Schedule an interview.
7. Login as Student and view the scheduled interview.
