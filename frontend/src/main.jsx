
import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

// LOCAL DEVELOPMENT API
// After backend deployment, replace this with your Render backend URL.
const API = "http://127.0.0.1:8000/api";

function App() {
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [user, setUser] = useState(
    JSON.parse(localStorage.getItem("user") || "null")
  );

  const [jobs, setJobs] = useState([]);
  const [applications, setApplications] = useState([]);
  const [interviews, setInterviews] = useState([]);
  const [stats, setStats] = useState({
    jobs: 0,
    applications: 0,
    interviews: 0,
    selected: 0,
  });

  const [mode, setMode] = useState("login");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const [auth, setAuth] = useState({
    name: "",
    email: "",
    password: "",
    role: "student",
  });

  const [jobForm, setJobForm] = useState({
    title: "",
    company: "",
    location: "",
    description: "",
  });

  const [search, setSearch] = useState("");
  const [locationFilter, setLocationFilter] = useState("");

  const [interviewForm, setInterviewForm] = useState({
    application_id: "",
    interview_date: "",
    interviewer: "",
    mode: "Online",
    meeting_link: "",
    notes: "",
  });

  const [showProfile, setShowProfile] = useState(false);

  const isRecruiter = user?.role === "recruiter";
  const isAdmin = user?.role === "admin";

  async function apiFetch(path, options = {}) {
    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    };

    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(`${API}${path}`, {
      ...options,
      headers,
    });

    const text = await response.text();

    let data = {};
    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      data = { detail: text };
    }

    if (!response.ok) {
      throw new Error(
        data?.detail || data?.message || `Request failed (${response.status})`
      );
    }

    return data;
  }

  async function refresh() {
    if (!token) return;

    try {
      const [jobsData, appsData, interviewsData, dashboardData] =
        await Promise.all([
          apiFetch("/jobs"),
          apiFetch("/applications"),
          apiFetch("/interviews"),
          apiFetch("/dashboard"),
        ]);

      setJobs(Array.isArray(jobsData) ? jobsData : []);
      setApplications(Array.isArray(appsData) ? appsData : []);
      setInterviews(Array.isArray(interviewsData) ? interviewsData : []);

      setStats({
        jobs: dashboardData?.jobs ?? 0,
        applications: dashboardData?.applications ?? 0,
        interviews: dashboardData?.interviews ?? 0,
        selected: dashboardData?.selected ?? 0,
      });
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    if (token) {
      refresh();
    }
  }, [token]);

  function clearMessages() {
    setMessage("");
    setError("");
  }

  async function register(e) {
    e.preventDefault();
    clearMessages();
    setLoading(true);

    try {
      await apiFetch("/register", {
        method: "POST",
        body: JSON.stringify({
          name: auth.name,
          email: auth.email,
          password: auth.password,
          role: auth.role,
        }),
      });

      setMessage("Registration successful. Please login.");

      setAuth({
        name: "",
        email: auth.email,
        password: "",
        role: "student",
      });

      setMode("login");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function login(e) {
    e.preventDefault();
    clearMessages();
    setLoading(true);

    try {
      const form = new URLSearchParams();
      form.append("username", auth.email);
      form.append("password", auth.password);

      const response = await fetch(`${API}/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: form.toString(),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data?.detail || "Login failed");
      }

      localStorage.setItem("token", data.access_token);
      localStorage.setItem("user", JSON.stringify(data.user));

      setToken(data.access_token);
      setUser(data.user);

      setMessage("Welcome to PlacementHub!");

      setAuth({
        name: "",
        email: "",
        password: "",
        role: "student",
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function createJob(e) {
    e.preventDefault();
    clearMessages();

    try {
      await apiFetch("/jobs", {
        method: "POST",
        body: JSON.stringify(jobForm),
      });

      setMessage("Job posted successfully.");

      setJobForm({
        title: "",
        company: "",
        location: "",
        description: "",
      });

      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  async function apply(jobId) {
    clearMessages();

    try {
      await apiFetch("/applications", {
        method: "POST",
        body: JSON.stringify({
          job_id: jobId,
        }),
      });

      setMessage("Application submitted successfully.");
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  async function changeStatus(applicationId, status) {
    clearMessages();

    try {
      await apiFetch(
        `/applications/${applicationId}/status?status=${encodeURIComponent(
          status
        )}`,
        {
          method: "PATCH",
        }
      );

      setMessage(`Application marked as ${status}.`);
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  async function scheduleInterview(e) {
    e.preventDefault();
    clearMessages();

    if (!interviewForm.application_id) {
      setError("Please select a shortlisted application.");
      return;
    }

    try {
      await apiFetch("/interviews", {
        method: "POST",
        body: JSON.stringify({
          application_id: Number(interviewForm.application_id),
          interview_date: interviewForm.interview_date,
          interviewer: interviewForm.interviewer,
          mode: interviewForm.mode,
          meeting_link: interviewForm.meeting_link,
          notes: interviewForm.notes,
        }),
      });

      setMessage("Interview scheduled successfully.");

      setInterviewForm({
        application_id: "",
        interview_date: "",
        interviewer: "",
        mode: "Online",
        meeting_link: "",
        notes: "",
      });

      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");

    setToken("");
    setUser(null);
    setJobs([]);
    setApplications([]);
    setInterviews([]);
    setStats({
      jobs: 0,
      applications: 0,
      interviews: 0,
      selected: 0,
    });
  }

  const filteredJobs = useMemo(() => {
    return jobs.filter((job) => {
      const text =
        `${job.title || ""} ${job.company || ""} ${
          job.description || ""
        }`.toLowerCase();

      const location = (job.location || "").toLowerCase();

      return (
        text.includes(search.toLowerCase()) &&
        location.includes(locationFilter.toLowerCase())
      );
    });
  }, [jobs, search, locationFilter]);

  const shortlistedApplications = applications.filter(
    (application) =>
      application.status?.toLowerCase() === "shortlisted"
  );

  function formatDate(date) {
    if (!date) return "Not specified";

    const parsed = new Date(date);

    if (Number.isNaN(parsed.getTime())) {
      return date;
    }

    return parsed.toLocaleString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function statusClass(status) {
    const value = status?.toLowerCase() || "";

    if (value === "selected") return "status selected";
    if (value === "shortlisted") return "status shortlisted";
    if (value === "rejected") return "status rejected";

    return "status pending";
  }

  if (!token) {
    return (
      <div className="auth-page">
        <div className="auth-background">
          <div className="orb orb-one"></div>
          <div className="orb orb-two"></div>
          <div className="orb orb-three"></div>
        </div>

        <div className="auth-card">
          <div className="brand">
            <div className="brand-icon">⚡</div>

            <div>
              <h1>PlacementHub</h1>
              <p>Placement & Interview Management</p>
            </div>
          </div>

          <div className="auth-heading">
            <h2>
              {mode === "login"
                ? "Welcome Back"
                : "Create Your Account"}
            </h2>

            <p>
              {mode === "login"
                ? "Sign in to continue your career journey."
                : "Join PlacementHub and discover new opportunities."}
            </p>
          </div>

          {message && <div className="alert success">{message}</div>}
          {error && <div className="alert error">{error}</div>}

          <form
            onSubmit={mode === "login" ? login : register}
            className="auth-form"
          >
            {mode === "register" && (
              <div className="form-group">
                <label>Full Name</label>
                <input
                  type="text"
                  placeholder="Enter your full name"
                  value={auth.name}
                  onChange={(e) =>
                    setAuth({ ...auth, name: e.target.value })
                  }
                  required
                />
              </div>
            )}

            <div className="form-group">
              <label>Email Address</label>
              <input
                type="email"
                placeholder="Enter your email"
                value={auth.email}
                onChange={(e) =>
                  setAuth({ ...auth, email: e.target.value })
                }
                required
              />
            </div>

            <div className="form-group">
              <label>Password</label>
              <input
                type="password"
                placeholder="Enter your password"
                value={auth.password}
                onChange={(e) =>
                  setAuth({ ...auth, password: e.target.value })
                }
                required
              />
            </div>

            {mode === "register" && (
              <div className="form-group">
                <label>Account Type</label>

                <select
                  value={auth.role}
                  onChange={(e) =>
                    setAuth({ ...auth, role: e.target.value })
                  }
                >
                  <option value="student">Student</option>
                  <option value="recruiter">Recruiter</option>
                </select>
              </div>
            )}

            <button
              type="submit"
              className="btn btn-primary full-btn"
              disabled={loading}
            >
              {loading
                ? "PLEASE WAIT..."
                : mode === "login"
                ? "LOGIN"
                : "CREATE ACCOUNT"}
            </button>
          </form>

          <div className="auth-switch">
            {mode === "login" ? (
              <>
                Don't have an account?
                <button onClick={() => setMode("register")}>
                  Create Account
                </button>
              </>
            ) : (
              <>
                Already have an account?
                <button onClick={() => setMode("login")}>
                  Login
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <div className="page-grid"></div>

      <header className="navbar">
        <div className="nav-brand">
          <div className="nav-logo">⚡</div>

          <div>
            <div className="nav-title">PlacementHub</div>
            <div className="nav-subtitle">
              CAREER MANAGEMENT SYSTEM
            </div>
          </div>
        </div>

        <div className="nav-actions">
          <button
            className="profile-btn"
            onClick={() => setShowProfile(!showProfile)}
          >
            <span className="avatar">
              {(user?.name || "U").charAt(0).toUpperCase()}
            </span>

            <span>{user?.name || "User"}</span>

            <span className="role-text">
              {user?.role || "student"}
            </span>
          </button>

          <button className="logout-btn" onClick={logout}>
            LOGOUT
          </button>
        </div>
      </header>

      <main className="main-container">
        {showProfile && (
          <section className="profile-panel glass-card">
            <div className="profile-avatar">
              {(user?.name || "U").charAt(0).toUpperCase()}
            </div>

            <div>
              <h3>{user?.name}</h3>
              <p>{user?.email}</p>
              <span className="profile-role">
                {user?.role}
              </span>
            </div>
          </section>
        )}

        <section className="hero-section">
          <div className="hero-content">
            <div className="hero-tag">⚡ PLACEMENT PLATFORM</div>

            <h1>
              Your Career.
              <br />
              <span>Your Future.</span>
            </h1>

            <p>
              Discover opportunities, manage applications,
              connect with recruiters and schedule interviews
              from one intelligent placement platform.
            </p>

            <div className="hero-line"></div>
          </div>

          <div className="hero-decoration">
            <div className="neon-circle">
              <div className="neon-circle-inner">⚡</div>
            </div>
          </div>
        </section>

        {message && (
          <div className="alert success page-alert">
            ✓ {message}
          </div>
        )}

        {error && (
          <div className="alert error page-alert">
            ⚠ {error}
          </div>
        )}

        <section className="stats-grid">
          <div className="stat-card cyan">
            <div className="stat-icon">💼</div>
            <div className="stat-number">{stats.jobs}</div>
            <div className="stat-label">AVAILABLE JOBS</div>
          </div>

          <div className="stat-card purple">
            <div className="stat-icon">📄</div>
            <div className="stat-number">
              {stats.applications}
            </div>
            <div className="stat-label">APPLICATIONS</div>
          </div>

          <div className="stat-card pink">
            <div className="stat-icon">📅</div>
            <div className="stat-number">
              {stats.interviews}
            </div>
            <div className="stat-label">INTERVIEWS</div>
          </div>

          <div className="stat-card green">
            <div className="stat-icon">🎯</div>
            <div className="stat-number">{stats.selected}</div>
            <div className="stat-label">SELECTED</div>
          </div>
        </section>

        {(isRecruiter || isAdmin) && (
          <section className="section">
            <div className="section-heading">
              <div>
                <span className="section-number">01</span>
                <h2>Post New Opportunity</h2>
              </div>
            </div>

            <form
              className="glass-card job-form"
              onSubmit={createJob}
            >
              <div className="form-grid">
                <div className="form-group">
                  <label>Job Title</label>
                  <input
                    value={jobForm.title}
                    onChange={(e) =>
                      setJobForm({
                        ...jobForm,
                        title: e.target.value,
                      })
                    }
                    placeholder="e.g. Frontend Web Developer"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Company</label>
                  <input
                    value={jobForm.company}
                    onChange={(e) =>
                      setJobForm({
                        ...jobForm,
                        company: e.target.value,
                      })
                    }
                    placeholder="Company name"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Location</label>
                  <input
                    value={jobForm.location}
                    onChange={(e) =>
                      setJobForm({
                        ...jobForm,
                        location: e.target.value,
                      })
                    }
                    placeholder="Remote / Hyderabad / Bengaluru"
                    required
                  />
                </div>

                <div className="form-group form-full">
                  <label>Job Description</label>
                  <textarea
                    rows="4"
                    value={jobForm.description}
                    onChange={(e) =>
                      setJobForm({
                        ...jobForm,
                        description: e.target.value,
                      })
                    }
                    placeholder="Describe the opportunity..."
                    required
                  />
                </div>
              </div>

              <button className="btn btn-primary">
                ⚡ POST JOB
              </button>
            </form>
          </section>
        )}

        <section className="section">
          <div className="section-heading">
            <div>
              <span className="section-number">02</span>
              <h2>Explore Opportunities</h2>
            </div>

            <button
              className="clear-btn"
              onClick={() => {
                setSearch("");
                setLocationFilter("");
              }}
            >
              CLEAR
            </button>
          </div>

          <div className="glass-card search-panel">
            <div className="search-box">
              <span>⌕</span>

              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search jobs, companies or skills..."
              />
            </div>

            <div className="search-box">
              <span>📍</span>

              <input
                value={locationFilter}
                onChange={(e) =>
                  setLocationFilter(e.target.value)
                }
                placeholder="Filter by location..."
              />
            </div>
          </div>
        </section>

        <section className="section">
          <div className="section-heading">
            <div>
              <span className="section-number">03</span>
              <h2>Latest Jobs</h2>
            </div>

            <span className="count-badge">
              {filteredJobs.length} OPPORTUNITIES
            </span>
          </div>

          {filteredJobs.length === 0 ? (
            <div className="empty-card glass-card">
              <div>🔎</div>
              <h3>No opportunities found</h3>
              <p>Try another search.</p>
            </div>
          ) : (
            <div className="jobs-grid">
              {filteredJobs.map((job) => (
                <article className="job-card glass-card" key={job.id}>
                  <div className="job-top">
                    <span className="job-type">OPEN ROLE</span>

                    <span className="job-id">
                      #{String(job.id).padStart(3, "0")}
                    </span>
                  </div>

                  <h3>{job.title}</h3>

                  <div className="company-name">
                    ◈ {job.company}
                  </div>

                  <div className="location-text">
                    📍 {job.location}
                  </div>

                  <p>{job.description}</p>

                  {user?.role === "student" && (
                    <button
                      className="btn btn-primary job-apply"
                      onClick={() => apply(job.id)}
                    >
                      APPLY NOW →
                    </button>
                  )}
                </article>
              ))}
            </div>
          )}
        </section>

        <section className="section">
          <div className="section-heading">
            <div>
              <span className="section-number">04</span>
              <h2>Candidate Applications</h2>
            </div>
          </div>

          {applications.length === 0 ? (
            <div className="empty-card glass-card">
              <div>📄</div>
              <h3>No applications yet</h3>
              <p>Applications will appear here.</p>
            </div>
          ) : (
            <div className="application-list">
              {applications.map((application) => (
                <article
                  className="application-card glass-card"
                  key={application.id}
                >
                  <div className="application-main">
                    <div className="application-avatar">
                      {(application.student_name || "S")
                        .charAt(0)
                        .toUpperCase()}
                    </div>

                    <div>
                      <h3>{application.job_title}</h3>

                      <div className="company-name">
                        ◈ {application.company}
                      </div>

                      <p>
                        Candidate:{" "}
                        <strong>
                          {application.student_name}
                        </strong>
                      </p>
                    </div>
                  </div>

                  <div className="application-right">
                    <span
                      className={statusClass(
                        application.status
                      )}
                    >
                      {application.status}
                    </span>

                    {(isRecruiter || isAdmin) && (
                      <div className="action-buttons">
                        <button
                          className="action-btn shortlist"
                          onClick={() =>
                            changeStatus(
                              application.id,
                              "Shortlisted"
                            )
                          }
                        >
                          SHORTLIST
                        </button>

                        <button
                          className="action-btn select"
                          onClick={() =>
                            changeStatus(
                              application.id,
                              "Selected"
                            )
                          }
                        >
                          SELECT
                        </button>

                        <button
                          className="action-btn reject"
                          onClick={() =>
                            changeStatus(
                              application.id,
                              "Rejected"
                            )
                          }
                        >
                          REJECT
                        </button>
                      </div>
                    )}
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        {(isRecruiter || isAdmin) && (
          <section className="section">
            <div className="section-heading">
              <div>
                <span className="section-number">05</span>
                <h2>Schedule Interview</h2>
              </div>
            </div>

            <form
              className="glass-card interview-form"
              onSubmit={scheduleInterview}
            >
              <div className="form-grid">
                <div className="form-group form-full">
                  <label>Shortlisted Application</label>

                  <select
                    value={interviewForm.application_id}
                    onChange={(e) =>
                      setInterviewForm({
                        ...interviewForm,
                        application_id: e.target.value,
                      })
                    }
                    required
                  >
                    <option value="">
                      Select shortlisted application
                    </option>

                    {shortlistedApplications.map((application) => (
                      <option
                        key={application.id}
                        value={application.id}
                      >
                        {application.student_name} —{" "}
                        {application.job_title} —{" "}
                        {application.company}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Interview Date & Time</label>

                  <input
                    type="datetime-local"
                    value={interviewForm.interview_date}
                    onChange={(e) =>
                      setInterviewForm({
                        ...interviewForm,
                        interview_date: e.target.value,
                      })
                    }
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Interviewer</label>

                  <input
                    value={interviewForm.interviewer}
                    onChange={(e) =>
                      setInterviewForm({
                        ...interviewForm,
                        interviewer: e.target.value,
                      })
                    }
                    placeholder="e.g. ABC Company HR"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Interview Mode</label>

                  <select
                    value={interviewForm.mode}
                    onChange={(e) =>
                      setInterviewForm({
                        ...interviewForm,
                        mode: e.target.value,
                      })
                    }
                  >
                    <option value="Online">Online</option>
                    <option value="Offline">Offline</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Meeting Link</label>

                  <input
                    type="url"
                    value={interviewForm.meeting_link}
                    onChange={(e) =>
                      setInterviewForm({
                        ...interviewForm,
                        meeting_link: e.target.value,
                      })
                    }
                    placeholder="https://meet.google.com/..."
                  />
                </div>

                <div className="form-group form-full">
                  <label>Notes</label>

                  <textarea
                    rows="3"
                    value={interviewForm.notes}
                    onChange={(e) =>
                      setInterviewForm({
                        ...interviewForm,
                        notes: e.target.value,
                      })
                    }
                    placeholder="Interview instructions or notes..."
                  />
                </div>
              </div>

              <button className="btn btn-primary">
                ⚡ SCHEDULE INTERVIEW
              </button>
            </form>
          </section>
        )}

        <section className="section">
          <div className="section-heading">
            <div>
              <span className="section-number">06</span>
              <h2>Upcoming Interviews</h2>
            </div>

            <span className="count-badge">
              {interviews.length} SCHEDULED
            </span>
          </div>

          {interviews.length === 0 ? (
            <div className="empty-card glass-card">
              <div>📅</div>
              <h3>No interviews scheduled</h3>
              <p>Scheduled interviews will appear here.</p>
            </div>
          ) : (
            <div className="interview-list">
              {interviews.map((interview) => (
                <article
                  className="interview-card glass-card"
                  key={interview.id}
                >
                  <div className="interview-date">
                    <span>DATE</span>
                    <strong>
                      {formatDate(interview.interview_date)}
                    </strong>
                  </div>

                  <div className="interview-info">
                    <h3>{interview.job_title}</h3>

                    <p>
                      <strong>Company:</strong>{" "}
                      {interview.company}
                    </p>

                    <p>
                      <strong>Candidate:</strong>{" "}
                      {interview.student_name}
                    </p>

                    <p>
                      <strong>Interviewer:</strong>{" "}
                      {interview.interviewer}
                    </p>

                    <p>
                      <strong>Mode:</strong>{" "}
                      {interview.mode}
                    </p>

                    {interview.notes && (
                      <p>
                        <strong>Notes:</strong>{" "}
                        {interview.notes}
                      </p>
                    )}
                  </div>

                  <div className="interview-actions">
                    <span
                      className={statusClass(
                        interview.status
                      )}
                    >
                      {interview.status}
                    </span>

                    {interview.meeting_link && (
                      <a
                        className="join-btn"
                        href={interview.meeting_link}
                        target="_blank"
                        rel="noreferrer"
                      >
                        JOIN INTERVIEW ↗
                      </a>
                    )}
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </main>

      <footer className="footer">
        <div className="footer-logo">⚡ PlacementHub</div>

        <p>
          Smart placement management for the next generation
          of careers.
        </p>

        <span>© 2026 PlacementHub</span>
      </footer>
    </div>
  );
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

