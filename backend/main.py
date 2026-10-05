from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import os

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel


# =========================
# CONFIGURATION
# =========================

BASE = Path(__file__).resolve().parent
DB = BASE / "placement.db"

SECRET = os.getenv("SECRET_KEY", "change-this-secret-before-production")
ALGORITHM = "HS256"


# =========================
# FASTAPI APP
# =========================

app = FastAPI(
    title="Placement & Interview Management API",
    version="1.0.0"
)


# =========================
# CORS
# =========================

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# AUTHENTICATION
# =========================

pwd = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

oauth2 = OAuth2PasswordBearer(
    tokenUrl="/api/login"
)


# =========================
# DATABASE
# =========================

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = db()

    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS jobs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT NOT NULL,
            description TEXT NOT NULL,
            posted_by INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS applications(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Applied'
        );

        CREATE TABLE IF NOT EXISTS interviews(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id INTEGER NOT NULL,
            interview_date TEXT NOT NULL,
            interviewer TEXT NOT NULL,
            mode TEXT NOT NULL,
            result TEXT NOT NULL DEFAULT 'Pending'
        );
        """
    )

    con.commit()
    con.close()


init_db()


# =========================
# PYDANTIC MODELS
# =========================

class Register(BaseModel):
    name: str
    email: str
    password: str
    role: str = "student"


class JobCreate(BaseModel):
    title: str
    company: str
    location: str
    description: str


class ApplicationCreate(BaseModel):
    job_id: int


class InterviewCreate(BaseModel):
    application_id: int
    interview_date: str
    interviewer: str
    mode: str = "Online"


# =========================
# CURRENT USER
# =========================

def current_user(token: str = Depends(oauth2)):

    try:
        payload = jwt.decode(
            token,
            SECRET,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

        con = db()

        user = con.execute(
            "SELECT * FROM users WHERE id=?",
            (int(user_id),)
        ).fetchone()

        con.close()

        if not user:
            raise HTTPException(
                status_code=401,
                detail="User not found"
            )

        return dict(user)

    except (JWTError, ValueError):

        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )


# =========================
# HEALTH CHECK
# =========================

@app.get("/api/health")
def health():

    return {
        "status": "ok",
        "service": "placement-interview-management"
    }


# =========================
# REGISTER
# =========================

@app.post("/api/register")
def register(data: Register):

    role = data.role.lower()

    if role not in {
        "student",
        "recruiter",
        "admin"
    }:
        raise HTTPException(
            status_code=400,
            detail="Invalid role"
        )

    con = db()

    try:

        cur = con.execute(
            """
            INSERT INTO users(
                name,
                email,
                password,
                role
            )
            VALUES(?,?,?,?)
            """,
            (
                data.name,
                data.email.lower(),
                pwd.hash(data.password),
                role
            )
        )

        con.commit()

        return {
            "message": "Registration successful",
            "id": cur.lastrowid
        }

    except sqlite3.IntegrityError:

        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    finally:

        con.close()


# =========================
# LOGIN
# =========================

@app.post("/api/login")
def login(
    form: OAuth2PasswordRequestForm = Depends()
):

    con = db()

    user = con.execute(
        "SELECT * FROM users WHERE email=?",
        (form.username.lower(),)
    ).fetchone()

    con.close()

    if not user or not pwd.verify(
        form.password,
        user["password"]
    ):

        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )

    token = jwt.encode(
        {
            "sub": str(user["id"]),
            "exp": datetime.utcnow()
            + timedelta(hours=8)
        },
        SECRET,
        algorithm=ALGORITHM
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }
    }


# =========================
# USER PROFILE
# =========================

@app.get("/api/me")
def me(
    user=Depends(current_user)
):

    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"]
    }


# =========================
# CREATE JOB
# =========================

@app.post("/api/jobs")
def create_job(
    data: JobCreate,
    user=Depends(current_user)
):

    if user["role"] not in {
        "recruiter",
        "admin"
    }:

        raise HTTPException(
            status_code=403,
            detail="Recruiter/admin access required"
        )

    con = db()

    cur = con.execute(
        """
        INSERT INTO jobs(
            title,
            company,
            location,
            description,
            posted_by
        )
        VALUES(?,?,?,?,?)
        """,
        (
            data.title,
            data.company,
            data.location,
            data.description,
            user["id"]
        )
    )

    con.commit()
    con.close()

    return {
        "message": "Job created",
        "id": cur.lastrowid
    }


# =========================
# GET JOBS
# =========================

@app.get("/api/jobs")
def jobs(
    user=Depends(current_user)
):

    con = db()

    rows = con.execute(
        """
        SELECT *
        FROM jobs
        ORDER BY id DESC
        """
    ).fetchall()

    con.close()

    return [
        dict(row)
        for row in rows
    ]


# =========================
# APPLY FOR JOB
# =========================

@app.post("/api/applications")
def apply(
    data: ApplicationCreate,
    user=Depends(current_user)
):

    if user["role"] != "student":

        raise HTTPException(
            status_code=403,
            detail="Student access required"
        )

    con = db()

    job = con.execute(
        "SELECT id FROM jobs WHERE id=?",
        (data.job_id,)
    ).fetchone()

    if not job:

        con.close()

        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    try:

        cur = con.execute(
            """
            INSERT INTO applications(
                job_id,
                student_id
            )
            VALUES(?,?)
            """,
            (
                data.job_id,
                user["id"]
            )
        )

        con.commit()

        return {
            "message": "Application submitted",
            "id": cur.lastrowid
        }

    except sqlite3.IntegrityError:

        raise HTTPException(
            status_code=409,
            detail="Could not submit application"
        )

    finally:

        con.close()


# =========================
# GET APPLICATIONS
# =========================

@app.get("/api/applications")
def applications(
    user=Depends(current_user)
):

    con = db()

    if user["role"] == "student":

        rows = con.execute(
            """
            SELECT
                a.*,
                j.title,
                j.company,
                u.name AS student_name
            FROM applications a
            JOIN jobs j
                ON a.job_id = j.id
            JOIN users u
                ON a.student_id = u.id
            WHERE a.student_id=?
            ORDER BY a.id DESC
            """,
            (user["id"],)
        ).fetchall()

    else:

        rows = con.execute(
            """
            SELECT
                a.*,
                j.title,
                j.company,
                u.name AS student_name
            FROM applications a
            JOIN jobs j
                ON a.job_id = j.id
            JOIN users u
                ON a.student_id = u.id
            ORDER BY a.id DESC
            """
        ).fetchall()

    con.close()

    return [
        dict(row)
        for row in rows
    ]


# =========================
# UPDATE APPLICATION STATUS
# =========================

@app.patch("/api/applications/{application_id}/status")
def update_status(
    application_id: int,
    status: str,
    user=Depends(current_user)
):

    if user["role"] not in {
        "recruiter",
        "admin"
    }:

        raise HTTPException(
            status_code=403,
            detail="Recruiter/admin access required"
        )

    allowed = {
        "Applied",
        "Shortlisted",
        "Rejected",
        "Selected"
    }

    if status not in allowed:

        raise HTTPException(
            status_code=400,
            detail="Invalid status"
        )

    con = db()

    result = con.execute(
        """
        UPDATE applications
        SET status=?
        WHERE id=?
        """,
        (
            status,
            application_id
        )
    )

    if result.rowcount == 0:

        con.close()

        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    con.commit()
    con.close()

    return {
        "message": "Status updated"
    }


# =========================
# CREATE INTERVIEW
# =========================

@app.post("/api/interviews")
def create_interview(
    data: InterviewCreate,
    user=Depends(current_user)
):

    if user["role"] not in {
        "recruiter",
        "admin"
    }:

        raise HTTPException(
            status_code=403,
            detail="Recruiter/admin access required"
        )

    con = db()

    application = con.execute(
        """
        SELECT id
        FROM applications
        WHERE id=?
        """,
        (data.application_id,)
    ).fetchone()

    if not application:

        con.close()

        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    cur = con.execute(
        """
        INSERT INTO interviews(
            application_id,
            interview_date,
            interviewer,
            mode
        )
        VALUES(?,?,?,?)
        """,
        (
            data.application_id,
            data.interview_date,
            data.interviewer,
            data.mode
        )
    )

    con.execute(
        """
        UPDATE applications
        SET status='Shortlisted'
        WHERE id=?
        """,
        (data.application_id,)
    )

    con.commit()
    con.close()

    return {
        "message": "Interview scheduled",
        "id": cur.lastrowid
    }


# =========================
# GET INTERVIEWS
# =========================

@app.get("/api/interviews")
def interviews(
    user=Depends(current_user)
):

    con = db()

    rows = con.execute(
        """
        SELECT
            i.*,
            a.status,
            j.title,
            j.company,
            u.name AS student_name
        FROM interviews i
        JOIN applications a
            ON i.application_id = a.id
        JOIN jobs j
            ON a.job_id = j.id
        JOIN users u
            ON a.student_id = u.id
        ORDER BY i.interview_date
        """
    ).fetchall()

    con.close()

    return [
        dict(row)
        for row in rows
    ]


# =========================
# DASHBOARD
# =========================

@app.get("/api/dashboard")
def dashboard(
    user=Depends(current_user)
):

    con = db()

    stats = {

        "jobs": con.execute(
            "SELECT COUNT(*) FROM jobs"
        ).fetchone()[0],

        "applications": con.execute(
            "SELECT COUNT(*) FROM applications"
        ).fetchone()[0],

        "interviews": con.execute(
            "SELECT COUNT(*) FROM interviews"
        ).fetchone()[0],

        "selected": con.execute(
            """
            SELECT COUNT(*)
            FROM applications
            WHERE status='Selected'
            """
        ).fetchone()[0]
    }

    con.close()

    return stats