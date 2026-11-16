# Law in Order — KB Academy
## Complete Website Project

> "Think Critically. Speak Fearlessly. Seek Justice."

---

## Project Structure

```
law_in_order/
├── frontend/           ← Static HTML/CSS/JS → deploy to GitHub Pages
│   ├── index.html      ← Public-facing home page
│   ├── login.html      ← Login + registration page
│   ├── dashboard.html  ← All member dashboards (role-aware)
│   ├── css/style.css   ← All styles (light & dark mode)
│   └── js/
│       ├── api.js          ← Backend API calls
│       ├── theme.js        ← Light/dark mode toggle
│       ├── countdown.js    ← Mock trial countdown
│       └── dashboard.js    ← Full dashboard logic
│
├── backend/            ← FastAPI (Python) → deploy to Render
│   ├── main.py         ← App entry point
│   ├── auth.py         ← Password hashing & sessions
│   ├── database.py     ← PostgreSQL connection
│   ├── setup_db.py     ← Run once to create tables
│   ├── requirements.txt
│   ├── .env.example    ← Copy to .env and fill in
│   └── routes/
│       ├── auth.py
│       ├── users.py
│       ├── announcements.py
│       ├── events.py
│       ├── mock_trials.py
│       ├── assignments.py
│       ├── case_files.py
│       ├── chat.py
│       ├── points.py
│       ├── certificates.py
│       ├── settings.py
│       └── admin.py
│
├── database/
│   └── schema.sql      ← All PostgreSQL tables
│
└── docs/
    └── HOW_THE_DATABASE_WORKS.md  ← Plain-English schema explanation
```

---

## Free Hosting Stack (Recommended)

| Layer | Service | Link |
|-------|---------|------|
| **Frontend** | GitHub Pages | https://pages.github.com |
| **Backend API** | Render (free tier) | https://render.com |
| **Database** | Neon (free PostgreSQL) | https://neon.tech |
| **File Storage** | Cloudinary (free tier) | https://cloudinary.com |

> GitHub Pages hosts static files for free. Render runs your Python backend for free (may sleep after inactivity). Neon gives you a free PostgreSQL database with 512 MB storage. Cloudinary gives 10 GB storage for uploaded files.

---

## Step-by-Step Setup

### 1. Install Python dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in:
- `DATABASE_URL` — your Neon or Supabase PostgreSQL connection string
- `SECRET_KEY` — generate with: `python -c "import secrets; print(secrets.token_hex(32))"`
- `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` — from your Cloudinary dashboard
- `FRONTEND_URL` — your GitHub Pages URL (or `http://localhost:5500` for local dev)

### 3. Create the database tables

```bash
python setup_db.py
```

This creates all tables in your PostgreSQL database.

### 4. Run locally

```bash
uvicorn main:app --reload --port 8000
```

The API is now at `http://localhost:8000`.

### 5. Test the frontend locally

Open `frontend/index.html` in a browser (use VS Code Live Server or any local server on port 5500).

> **Important:** In `frontend/js/api.js`, change `API_BASE` to `http://localhost:8000/api` for local testing.

### 6. Create leadership accounts

1. Open `frontend/login.html` → click **Register**.
2. Enter the **leader access code** (`KBALEADERS` by default).
3. The **first** leader account created becomes the **President**.
4. The **second** becomes the **Vice President**.
5. After both are created, the leader code will refuse further leader registrations.

> Change the default access codes immediately after setup from the **Settings** panel.

---

## Deploying to Production

### A. Deploy the backend to Render

1. Push your code to a GitHub repository.
2. Go to https://render.com → New Web Service.
3. Connect your repository.
4. Set:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn main:app --host 0.0.0.0 --port 10000`
5. Add all environment variables from your `.env` file in Render's Environment panel.
6. After deployment, your API URL will be something like `https://your-app.onrender.com`.

### B. Deploy the frontend to GitHub Pages

1. Create a GitHub repository for the project.
2. Push the contents of `frontend/` to the **root** of a branch called `gh-pages` (or use a `/docs` folder on `main`).
3. In your repository settings → Pages → select the branch.
4. Your site will be live at `https://yourusername.github.io/law-in-order`.

### C. Connect frontend to backend

In `frontend/js/api.js`, update:
```js
const API_BASE = "https://YOUR-APP.onrender.com/api";
```

Also update the `FRONTEND_URL` in your Render environment variables to your GitHub Pages URL.

---

## Security Notes

- Passwords are **never stored in plain text**. All passwords are hashed with bcrypt.
- Role-based access is enforced **on the server**, not just in JavaScript.
- Session tokens are stored in `HttpOnly` cookies — JavaScript cannot steal them.
- File uploads are validated for type and size on the server.
- Uploaded files are stored privately in Cloudinary (authenticated access).
- SQL injection is prevented by using parameterised queries throughout.
- Rate limiting is applied to login and registration endpoints.

**Limitations to be aware of:**
- The free Render tier sleeps after 15 minutes of inactivity (first request after sleep is slow).
- The free Neon tier has a 512 MB database limit.
- HTTPS is handled by Render and GitHub Pages automatically in production.

---

## Default Access Codes

| Role | Default Code |
|------|-------------|
| Delegate | `KBADELEGATES` |
| Leader | `KBALEADERS` |

**Change these from the Settings panel immediately after setup.**

---

## Backup Instructions

To back up the database:
```bash
pg_dump "YOUR_DATABASE_URL" > backup_$(date +%Y%m%d).sql
```

To restore:
```bash
psql "YOUR_DATABASE_URL" < backup_YYYYMMDD.sql
```

Neon also provides automatic daily backups on their free tier.

---

*Built for Law in Order, KB Academy.*
