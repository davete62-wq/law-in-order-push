# How the Database Works — Explained Like You're 10

Hi! This document explains what every table in the database does, using simple words.
Think of the **database** like a giant filing cabinet full of folders.
Each **table** is one labelled folder, and each **row** in a table is one piece of paper inside that folder.

---

## 1. `club_settings` — The Club's Identity Card

Imagine a card pinned to the front of the cabinet that says the club's name, its motto, and the Instagram handles of the president and vice president.

There is **always exactly one card** (one row). Leaders update it from the Settings panel.

Things stored here:
- Club name and school name
- The motto ("Think Critically. Speak Fearlessly. Seek Justice.")
- Mission and vision text
- Instagram handles for president and VP
- Whether new members can register right now (recruitment open/closed)
- Maximum number of delegates allowed (default: 55)
- What time mock trials happen each month

---

## 2. `access_codes` — The Secret Door Codes

When a student signs up, they need to type a secret code to prove they belong.

| role | code |
|------|------|
| delegate | KBADELEGATES |
| leader | KBALEADERS |

Leaders can change these codes any time from the Settings panel. The old codes stop working immediately.

---

## 3. `users` — Every Person With an Account

This is the most important folder. Every single person on the website has one row here.

Each row stores:
- **member_number** — a unique number like `#001`, `#002`. These are **never reused**, even if someone's account is deleted.
- **username** — their chosen login name
- **first_name, last_name, grade** — personal info
- **role** — one of: `president`, `vice_president`, `staff`, `delegate`, `applicant`
- **status** — `active` (normal), `suspended` (blocked), or `deleted` (gone but number kept)
- **password_hash** — the password stored scrambled using a technique called bcrypt. Nobody (not even the president) can read the original password.

---

## 4. `staff_permissions` — What Each Staff Member Can Do

Staff members don't all have the same powers. The president or VP turns each permission on or off like a light switch.

For example, one staff member might be allowed to review essays but NOT manage chat rooms. Another might be allowed to manage events but nothing else.

There is one row per staff member, with a column for each permission.

---

## 5. `applications` — The Application Folder

When a student registers, they become an **Applicant**. This folder tracks their application.

- They upload **one essay** (PDF or Word file). They cannot upload a second one.
- A reviewer (president, VP, or authorized staff) reads the essay and marks it **PASS** or **FAIL**.
- If PASS → the student becomes a Delegate.
- If FAIL → the application is finished for this round.

---

## 6. `announcements` — The Club Notice Board

Leaders post announcements here — like a school notice board.

- **Public** announcements show up on the main website that everyone can see.
- **Private** announcements only appear inside the members' portal (you have to be logged in).

---

## 7. `events` — The Events Calendar

Upcoming meetings, workshops, and other club activities are saved here.

Each event has a date, time, location, and description. Some events are public (visible to visitors), others are private (members only).

---

## 8. `mock_trials` — The Mock Courtroom Schedule

Mock trials are a big deal — they happen at the end of every month. This folder keeps track of each one.

Each row stores:
- The date and time
- The case topic
- Instructions for participants
- Whether it's upcoming, completed, or cancelled
- A summary of the result afterwards

There's also a special type for the **end-of-year courtroom trial**, which is separate from the regular monthly ones.

---

## 9. `mock_trial_roles` — Who Plays What in Court

In each mock trial, different delegates play different roles:
- **Judge**
- **Prosecutor**
- **Defence**
- **Witness**
- etc.

This table connects each delegate to their role in each trial.

---

## 10. `teams` — Working Groups

Leaders can organize delegates into teams (like groups in class). This table stores each team.

The `team_members` table connects which delegates belong to which team.

---

## 11. `assignments` — Homework Tasks

Leaders (or authorized staff) can create tasks and assign them to delegates. Think of it like homework.

Three related tables:
- `assignments` — the task itself (title, description, deadline)
- `assignment_assignees` — which individual delegates got this task
- `assignment_teams` — which whole teams got this task
- `assignment_submissions` — whether a delegate has completed it

---

## 12. `case_files` — The Filing Cabinet for Documents

PDFs and other documents (case files, club rules, constitution) are stored here. The actual file lives in Cloudinary (an online storage service), and this table stores the link to it plus info about what it is.

Each file is tagged with a category:
- `case` — a legal case document for a mock trial
- `assignment` — attached to a task
- `constitution` — the club's official rules document
- `rules` — club behaviour rules
- `general` — anything else

---

## 13. `chat_rooms`, `chat_room_members`, `chat_messages` — The Club Messenger

Three folders that work together to run the chat:

- **chat_rooms** — the list of group chats. The **General** chat is permanent; it cannot be deleted.
- **chat_room_members** — who belongs to each chat room
- **chat_messages** — every message ever sent, in order of time

---

## 14. `points` and `point_audit_log` — The Scoreboard

Every delegate has a points total. Points are awarded by leaders or authorized staff for participation.

- `points` — the current score for each member
- `point_audit_log` — a full history of every change (like a bank statement). If someone's points go from 10 to 15, there's a record saying who added 5 points and why.

Members **cannot** change their own points.

---

## 15. `certificates` — Awards and Achievements

Leaders issue certificates to delegates for their achievements. There are five certificate categories (the club will decide the names and criteria).

Each row records who got it, what category it is, who issued it, and when.

---

## 16. `audit_log` — The Security Camera

Every important admin action is recorded here — like a security camera for the website.

For example:
- "President suspended user #012"
- "VP changed access code for delegates"
- "Staff member approved application #004"

This means there is always a record of who did what and when.

---

## 17. `sessions` — Remembering Who's Logged In

When a member logs in, the server creates a unique secret token and saves it here. Every time they click something, the website checks this table to confirm they're still logged in and who they are.

Sessions expire after a set time for security. When a member logs out, their session token is deleted from this table.

---

## How the Tables Connect

```
users ──┬── applications        (one per applicant)
        ├── staff_permissions   (one per staff member)
        ├── team_members        (many-to-many with teams)
        ├── assignment_assignees (many-to-many with assignments)
        ├── assignment_submissions
        ├── mock_trial_roles
        ├── chat_room_members
        ├── chat_messages
        ├── points
        ├── point_audit_log
        └── certificates

mock_trials ── mock_trial_roles
            └── case_files

assignments ── assignment_assignees
            ├── assignment_teams
            ├── assignment_submissions
            └── case_files

chat_rooms ── chat_room_members
           └── chat_messages
```

---

## Rules the Database Enforces Automatically

- Member numbers are **never reused** (assigned by a database sequence counter that only goes forward).
- Passwords are **always stored scrambled** (bcrypt hash). The original password is never saved.
- An applicant can only have **one application row**.
- The general chat room **cannot be deleted** (the backend enforces this).
- Points can only be changed by authorized people (enforced by the backend API).
- Staff permissions default to all-off until a leader turns them on.

---

*This document is part of the Law in Order — KB Academy project.*
