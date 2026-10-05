# Architecture

```text
Student / Recruiter / Admin
          |
       React UI
          |
       REST API
          |
       FastAPI
          |
   Authentication (JWT)
          |
      SQLite DB
          |
+---------+----------+
|         |          |
Jobs  Applications Interviews
|         |          |
+---------+----------+
          |
   Status / Selection
```

## Main workflow

Student → Register → Browse Jobs → Apply → Shortlisted → Interview Scheduled → Evaluation → Selected/Rejected.

Recruiter → Login → Post Job → View Applications → Shortlist → Schedule Interview → Update Result.

Admin → Monitor jobs, applications, interviews and placement statistics.
