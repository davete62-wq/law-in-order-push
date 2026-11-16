-- =============================================================
-- LAW IN ORDER — KB ACADEMY
-- PostgreSQL Database Schema
-- =============================================================
-- Run this file against your PostgreSQL database to create
-- all required tables. Order matters — tables that are
-- referenced by foreign keys are created first.
-- =============================================================

-- ─────────────────────────────────────────────
-- 1. CLUB SETTINGS
--    Stores editable club information such as the name,
--    motto, mission statement, and contact handles.
--    There is always exactly ONE row in this table.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS club_settings (
    id                      SERIAL PRIMARY KEY,
    club_name               VARCHAR(120)  NOT NULL DEFAULT 'Law in Order',
    school_name             VARCHAR(120)  NOT NULL DEFAULT 'KB Academy',
    motto                   TEXT          NOT NULL DEFAULT 'Think Critically. Speak Fearlessly. Seek Justice.',
    mission                 TEXT,
    vision                  TEXT,
    president_instagram     VARCHAR(100),
    vp_instagram            VARCHAR(100),
    recruitment_open        BOOLEAN       NOT NULL DEFAULT TRUE,
    delegate_capacity       INT           NOT NULL DEFAULT 55,
    mock_trial_time         VARCHAR(10)   NOT NULL DEFAULT '15:00',
    updated_at              TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- Insert the single settings row if it doesn't exist yet.
INSERT INTO club_settings (id) VALUES (1) ON CONFLICT DO NOTHING;


-- ─────────────────────────────────────────────
-- 2. ACCESS CODES
--    Codes that students enter when registering.
--    Each code maps to a role (e.g. 'delegate', 'leader').
--    Leaders can change or revoke codes from the settings panel.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS access_codes (
    id          SERIAL PRIMARY KEY,
    role        VARCHAR(30)  NOT NULL UNIQUE,  -- 'delegate' | 'leader'
    code        VARCHAR(100) NOT NULL,
    active      BOOLEAN      NOT NULL DEFAULT TRUE,
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Default codes. Change these from the settings panel after setup.
INSERT INTO access_codes (role, code) VALUES
    ('delegate', 'KBADELEGATES'),
    ('leader',   'KBALEADERS')
ON CONFLICT (role) DO NOTHING;


-- ─────────────────────────────────────────────
-- 3. USERS
--    Every person with an account: presidents, vice presidents,
--    staff members, delegates, and applicants.
--
--    role values:
--      'president'      – full administrative access
--      'vice_president' – same as president, equal authority
--      'staff'          – limited admin, permissions set separately
--      'delegate'       – accepted member
--      'applicant'      – registered but not yet accepted
--
--    status values:
--      'active'     – normal access
--      'suspended'  – blocked from portal
--      'deleted'    – soft-deleted, number never reused
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    member_number   INT          NOT NULL UNIQUE,  -- e.g. 1 → displayed as #001
    username        VARCHAR(60)  NOT NULL UNIQUE,
    first_name      VARCHAR(80)  NOT NULL,
    last_name       VARCHAR(80)  NOT NULL,
    grade           SMALLINT     CHECK (grade IN (9, 10, 11, 12)),
    role            VARCHAR(20)  NOT NULL DEFAULT 'applicant'
                        CHECK (role IN ('president','vice_president','staff','delegate','applicant')),
    status          VARCHAR(20)  NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active','suspended','deleted')),
    password_hash   TEXT         NOT NULL,          -- bcrypt hash, never plain text
    profile_pic_url TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Auto-assign the next member number on insert.
CREATE SEQUENCE IF NOT EXISTS member_number_seq START 1;

CREATE OR REPLACE FUNCTION assign_member_number()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.member_number := nextval('member_number_seq');
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_assign_member_number ON users;
CREATE TRIGGER trg_assign_member_number
    BEFORE INSERT ON users
    FOR EACH ROW EXECUTE FUNCTION assign_member_number();

-- Auto-update updated_at whenever a row changes.
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ─────────────────────────────────────────────
-- 4. STAFF PERMISSIONS
--    Each staff member can be given specific permissions
--    by the president or vice president. This is stored
--    as individual on/off flags rather than a list,
--    so the backend can check each one precisely.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS staff_permissions (
    user_id                 INT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    can_review_applications BOOLEAN NOT NULL DEFAULT FALSE,
    can_review_essays       BOOLEAN NOT NULL DEFAULT FALSE,
    can_manage_assignments  BOOLEAN NOT NULL DEFAULT FALSE,
    can_manage_events       BOOLEAN NOT NULL DEFAULT FALSE,
    can_manage_announcements BOOLEAN NOT NULL DEFAULT FALSE,
    can_manage_case_files   BOOLEAN NOT NULL DEFAULT FALSE,
    can_manage_chats        BOOLEAN NOT NULL DEFAULT FALSE,
    can_manage_points       BOOLEAN NOT NULL DEFAULT FALSE,
    can_manage_participation BOOLEAN NOT NULL DEFAULT FALSE,
    can_manage_rules        BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_staff_perms_updated_at ON staff_permissions;
CREATE TRIGGER trg_staff_perms_updated_at
    BEFORE UPDATE ON staff_permissions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ─────────────────────────────────────────────
-- 5. APPLICATIONS (Essay submissions)
--    When a student registers, an application row is created.
--    They can upload one essay (PDF or DOCX).
--    A reviewer then marks it PASS or FAIL.
--    PASS converts the applicant to a delegate.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS applications (
    id              SERIAL PRIMARY KEY,
    user_id         INT          NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    essay_filename  VARCHAR(300),              -- stored file name
    essay_url       TEXT,                      -- Cloudinary / storage URL
    essay_mime      VARCHAR(80),               -- 'application/pdf' or docx
    submitted_at    TIMESTAMPTZ,
    status          VARCHAR(20)  NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','submitted','pass','fail')),
    reviewed_by     INT          REFERENCES users(id),
    reviewed_at     TIMESTAMPTZ,
    reviewer_notes  TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);


-- ─────────────────────────────────────────────
-- 6. ANNOUNCEMENTS
--    Public announcements appear on the public site.
--    Private announcements appear only in the member portal.
--    Authorized users can create, edit, and delete them.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS announcements (
    id          SERIAL PRIMARY KEY,
    title       VARCHAR(200) NOT NULL,
    body        TEXT         NOT NULL,
    is_public   BOOLEAN      NOT NULL DEFAULT FALSE,  -- TRUE = visible on public site
    pinned      BOOLEAN      NOT NULL DEFAULT FALSE,
    created_by  INT          NOT NULL REFERENCES users(id),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_ann_updated_at ON announcements;
CREATE TRIGGER trg_ann_updated_at
    BEFORE UPDATE ON announcements
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ─────────────────────────────────────────────
-- 7. EVENTS
--    General club events (meetings, workshops, etc.).
--    Separate from mock trials (see table 8).
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS events (
    id              SERIAL PRIMARY KEY,
    title           VARCHAR(200) NOT NULL,
    description     TEXT,
    event_date      DATE         NOT NULL,
    event_time      VARCHAR(10),                -- e.g. '14:30'
    location        VARCHAR(200),
    is_public       BOOLEAN      NOT NULL DEFAULT FALSE,
    created_by      INT          NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_events_updated_at ON events;
CREATE TRIGGER trg_events_updated_at
    BEFORE UPDATE ON events
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ─────────────────────────────────────────────
-- 8. MOCK TRIALS
--    Dedicated table for monthly mock trials and the
--    end-of-year courtroom trial. The website calculates
--    the next recurring date automatically; this table
--    stores overrides and past records.
--
--    trial_type: 'monthly' | 'end_of_year' | 'special'
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mock_trials (
    id              SERIAL PRIMARY KEY,
    title           VARCHAR(200) NOT NULL,
    trial_type      VARCHAR(20)  NOT NULL DEFAULT 'monthly'
                        CHECK (trial_type IN ('monthly','end_of_year','special')),
    trial_date      DATE         NOT NULL,
    trial_time      VARCHAR(10),
    case_topic      TEXT,
    instructions    TEXT,
    status          VARCHAR(20)  NOT NULL DEFAULT 'upcoming'
                        CHECK (status IN ('upcoming','completed','cancelled')),
    result_summary  TEXT,
    created_by      INT          NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_mt_updated_at ON mock_trials;
CREATE TRIGGER trg_mt_updated_at
    BEFORE UPDATE ON mock_trials
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ─────────────────────────────────────────────
-- 9. MOCK TRIAL ROLES
--    Tracks which delegate plays which role in a trial
--    (e.g. judge, prosecutor, defence, witness).
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mock_trial_roles (
    id              SERIAL PRIMARY KEY,
    mock_trial_id   INT          NOT NULL REFERENCES mock_trials(id) ON DELETE CASCADE,
    user_id         INT          NOT NULL REFERENCES users(id),
    role_name       VARCHAR(80)  NOT NULL,  -- 'Judge', 'Prosecutor', etc.
    UNIQUE (mock_trial_id, user_id)
);


-- ─────────────────────────────────────────────
-- 10. TEAMS
--     Named groups of delegates for mock trials or tasks.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS teams (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(120) NOT NULL,
    description TEXT,
    created_by  INT          NOT NULL REFERENCES users(id),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS team_members (
    team_id     INT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id     INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (team_id, user_id)
);


-- ─────────────────────────────────────────────
-- 11. ASSIGNMENTS
--     Tasks created by leaders or authorized staff.
--     Can be assigned to individual users or whole teams.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS assignments (
    id              SERIAL PRIMARY KEY,
    title           VARCHAR(200) NOT NULL,
    description     TEXT,
    instructions    TEXT,
    deadline        TIMESTAMPTZ,
    created_by      INT          NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_assign_updated_at ON assignments;
CREATE TRIGGER trg_assign_updated_at
    BEFORE UPDATE ON assignments
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Which users (delegates) are assigned to an assignment.
CREATE TABLE IF NOT EXISTS assignment_assignees (
    assignment_id   INT NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
    user_id         INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (assignment_id, user_id)
);

-- Which teams are assigned to an assignment.
CREATE TABLE IF NOT EXISTS assignment_teams (
    assignment_id   INT NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
    team_id         INT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    PRIMARY KEY (assignment_id, team_id)
);

-- Tracks whether a delegate has completed their assignment.
CREATE TABLE IF NOT EXISTS assignment_submissions (
    id              SERIAL PRIMARY KEY,
    assignment_id   INT          NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
    user_id         INT          NOT NULL REFERENCES users(id),
    status          VARCHAR(20)  NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','submitted','approved','rejected')),
    submitted_at    TIMESTAMPTZ,
    notes           TEXT,
    UNIQUE (assignment_id, user_id)
);


-- ─────────────────────────────────────────────
-- 12. CASE FILES (Documents)
--     Uploaded PDFs and other club documents.
--     Each file belongs to a category and optionally
--     to a mock trial, case, or assignment.
--
--     category: 'case' | 'assignment' | 'constitution'
--               | 'rules' | 'general'
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS case_files (
    id              SERIAL PRIMARY KEY,
    filename        VARCHAR(300) NOT NULL,
    file_url        TEXT         NOT NULL,  -- Cloudinary URL
    mime_type       VARCHAR(80),
    category        VARCHAR(30)  NOT NULL DEFAULT 'general'
                        CHECK (category IN ('case','assignment','constitution','rules','general')),
    mock_trial_id   INT          REFERENCES mock_trials(id),
    assignment_id   INT          REFERENCES assignments(id),
    description     TEXT,
    uploaded_by     INT          NOT NULL REFERENCES users(id),
    uploaded_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);


-- ─────────────────────────────────────────────
-- 13. CHAT ROOMS
--     'general' is permanent and cannot be deleted.
--     'group'   are temporary rooms created by leaders.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chat_rooms (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(120) NOT NULL,
    room_type   VARCHAR(20)  NOT NULL DEFAULT 'group'
                    CHECK (room_type IN ('general','group')),
    created_by  INT          REFERENCES users(id),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Insert the permanent general chat if it doesn't exist yet.
INSERT INTO chat_rooms (name, room_type)
SELECT 'General', 'general'
WHERE NOT EXISTS (SELECT 1 FROM chat_rooms WHERE room_type = 'general');

CREATE TABLE IF NOT EXISTS chat_room_members (
    room_id     INT NOT NULL REFERENCES chat_rooms(id) ON DELETE CASCADE,
    user_id     INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (room_id, user_id)
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id          SERIAL PRIMARY KEY,
    room_id     INT          NOT NULL REFERENCES chat_rooms(id) ON DELETE CASCADE,
    user_id     INT          NOT NULL REFERENCES users(id),
    body        TEXT         NOT NULL,
    sent_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_room ON chat_messages(room_id, sent_at);


-- ─────────────────────────────────────────────
-- 14. POINTS (Participation Scoring)
--     One row per member. Points are changed only by
--     authorized staff or leaders — never by the member.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS points (
    user_id     INT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    total       INT         NOT NULL DEFAULT 0,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_points_updated_at ON points;
CREATE TRIGGER trg_points_updated_at
    BEFORE UPDATE ON points
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Every change to a member's points is recorded here
-- so leaders can see a full history.
CREATE TABLE IF NOT EXISTS point_audit_log (
    id          SERIAL PRIMARY KEY,
    user_id     INT          NOT NULL REFERENCES users(id),
    changed_by  INT          NOT NULL REFERENCES users(id),
    delta       INT          NOT NULL,          -- positive = added, negative = deducted
    reason      TEXT,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);


-- ─────────────────────────────────────────────
-- 15. CERTIFICATES
--     Issued to delegates by leaders.
--     Five certificate categories/tiers (names TBD by club).
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS certificates (
    id          SERIAL PRIMARY KEY,
    user_id     INT          NOT NULL REFERENCES users(id),
    category    VARCHAR(80)  NOT NULL,  -- Tier name set by leadership
    title       VARCHAR(200),
    issued_by   INT          NOT NULL REFERENCES users(id),
    issued_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    notes       TEXT
);


-- ─────────────────────────────────────────────
-- 16. AUDIT LOG
--     Records important administrative actions
--     (account changes, suspensions, role changes, etc.)
--     so there is always a traceable history.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id          SERIAL PRIMARY KEY,
    actor_id    INT          REFERENCES users(id),  -- who did it
    action      VARCHAR(100) NOT NULL,              -- e.g. 'suspend_user'
    target_id   INT,                                -- who/what was affected
    detail      TEXT,                               -- optional extra info (JSON string)
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_actor ON audit_log(actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log(created_at);


-- ─────────────────────────────────────────────
-- 17. SESSIONS
--     Stores login session tokens.
--     The backend checks this table on every request
--     to confirm the user is still logged in.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
    token       VARCHAR(128) PRIMARY KEY,
    user_id     INT          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at  TIMESTAMPTZ  NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);


-- ─────────────────────────────────────────────
-- END OF SCHEMA
-- ─────────────────────────────────────────────
