// js/dashboard.js — Full dashboard logic for all roles

let currentUser   = null;
let currentRoomId = null;
let membersList   = [];
let _chatPollTimer = null;  // live chat refresh

// ── Skeleton loader helper ──────────────────────────────────────────
function skeleton(elId, rows = 3) {
  const el = document.getElementById(elId);
  if (!el || el.innerHTML.trim()) return; // already has content — don't flash
  el.innerHTML = Array(rows).fill(
    `<div class="item skel"><div class="skel-line" style="width:60%;height:16px;"></div>
      <div class="skel-line" style="width:85%;height:11px;margin-top:8px;"></div></div>`
  ).join("");
}

// ═══════════════════════════════════════════════════════════════════
// BOOTSTRAP — load user and build the correct dashboard
// ═══════════════════════════════════════════════════════════════════
async function bootstrap() {
  try {
    currentUser = await api.get("/auth/me");
  } catch (_) {
    window.location.href = "login.html";
    return;
  }

  // Header
  document.getElementById("nav-username").textContent =
    `${currentUser.first_name} ${currentUser.last_name}`;
  document.getElementById("welcome-msg").textContent =
    `Welcome back, ${currentUser.first_name}!`;
  document.getElementById("role-pill").textContent =
    roleLabel(currentUser.role);
  document.getElementById("dash-date").textContent =
    new Date().toLocaleDateString("en-GB", { weekday:"long", day:"numeric", month:"long", year:"numeric" });

  buildSidebar();
  loadOverview();
}

function roleLabel(role) {
  const map = {
    president:      "President",
    vice_president: "Vice President",
    staff:          "Staff Member",
    delegate:       "Delegate",
    applicant:      "Applicant",
  };
  return map[role] || role;
}

// ═══════════════════════════════════════════════════════════════════
// SIDEBAR — built dynamically based on role
// ═══════════════════════════════════════════════════════════════════
function buildSidebar() {
  const r = currentUser.role;
  const isLeader = r === "president" || r === "vice_president";
  const isStaff  = r === "staff";
  const isApplicant = r === "applicant";

  let html = navBtn("overview", "⌂", "Overview", true);

  if (isApplicant) {
    html += navBtn("application", "📋", "My Application");
  }

  if (!isApplicant) {
    html += navBtn("announcements", "📢", "Announcements");
    html += navBtn("events",        "📅", "Events");
    html += navBtn("mock-trials",   "⚖",  "Mock Trials");
    html += navBtn("assignments",   "📝", "Assignments");
    html += navBtn("files",         "📁", "Case Files");
    html += navBtn("chat",          "💬", "Group Chats");
    html += navBtn("rankings",      "🏆", "Rankings");
    html += navBtn("certificates",  "🏅", "Certificates");
  }

  if (isLeader || isStaff) {
    html += `<hr class="side-divider">`;
    html += navBtn("applications", "📥", "Applications");
  }

  if (isLeader) {
    html += navBtn("members",  "👥", "Members");
    html += navBtn("settings", "⚙",  "Settings");
  }

  document.getElementById("sidebar").innerHTML = html;

  // Click handlers
  document.querySelectorAll(".side-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const panel = btn.dataset.panel;
      switchPanel(panel);
    });
  });
}

function navBtn(panel, icon, label, active = false) {
  return `<button class="side-btn${active ? " active" : ""}" data-panel="${panel}">${icon} &nbsp; ${label}</button>`;
}

function switchPanel(id) {
  // Stop chat polling whenever we navigate away from chat
  if (id !== "chat" && _chatPollTimer) {
    clearInterval(_chatPollTimer);
    _chatPollTimer = null;
  }

  document.querySelectorAll(".side-btn").forEach(b => b.classList.remove("active"));
  const activeBtn = document.querySelector(`.side-btn[data-panel="${id}"]`);
  if (activeBtn) activeBtn.classList.add("active");

  document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
  const panel = document.getElementById("panel-" + id);
  if (panel) {
    panel.classList.add("active");
    loadPanel(id);
  }
}

// ═══════════════════════════════════════════════════════════════════
// PANEL LOADER — called each time a panel is activated
// ═══════════════════════════════════════════════════════════════════
function loadPanel(id) {
  switch (id) {
    case "overview":       loadOverview();     break;
    case "application":    loadApplication();  break;
    case "announcements":  loadAnnouncements();break;
    case "events":         loadEvents();       break;
    case "mock-trials":    loadMockTrials();   break;
    case "assignments":    loadAssignments();  break;
    case "files":          loadFiles();        break;
    case "chat":           loadChat();         break;
    case "rankings":       loadRankings();     break;
    case "certificates":   loadCerts();        break;
    case "members":        loadMembers();      break;
    case "applications":   loadApplications(); break;
    case "settings":       loadSettings();     break;
  }
}

// ═══════════════════════════════════════════════════════════════════
// OVERVIEW
// ═══════════════════════════════════════════════════════════════════
async function loadOverview() {
  skeleton("overview-announcements", 2);
  try {
    const r = currentUser.role;
    const isLeader = r === "president" || r === "vice_president";

    if (isLeader) {
      const stats = await api.get("/admin/stats");
      document.getElementById("overview-metrics").innerHTML = `
        <div class="metric"><strong>${stats.total_active}</strong><span>Active members</span></div>
        <div class="metric"><strong>${stats.delegates}</strong><span>Delegates</span></div>
        <div class="metric"><strong>${stats.pending_applications}</strong><span>Pending applications</span></div>
      `;
    } else if (r === "delegate") {
      const pts = await api.get("/points/my");
      document.getElementById("overview-metrics").innerHTML = `
        <div class="metric"><strong>${pts.total}</strong><span>My points</span></div>
      `;
    } else {
      document.getElementById("overview-metrics").innerHTML = "";
    }
  } catch (_) {}

  try {
    const anns = await api.get("/announcements/");
    const el   = document.getElementById("overview-announcements");
    if (anns && anns.length > 0) {
      el.innerHTML = anns.slice(0, 3).map(a => `
        <div class="item">
          <div><h3>${a.title}</h3><p>${a.body}</p></div>
        </div>
      `).join("");
    } else {
      el.innerHTML = `<div class="empty">No announcements yet.</div>`;
    }
  } catch (_) {}
}

// ═══════════════════════════════════════════════════════════════════
// APPLICATION (applicant only)
// ═══════════════════════════════════════════════════════════════════
async function loadApplication() {
  try {
    const app = await api.get("/users/my-application");
    const content = document.getElementById("app-status-content");
    if (!app) {
      content.innerHTML = `<p style="color:var(--muted)">No application found.</p>`;
      return;
    }
    const statusColors = { pending:"", submitted:"#2563eb", pass:"pass", fail:"fail" };
    content.innerHTML = `
      <h3>Application status</h3>
      <p style="margin-top:10px;">
        Status: <span class="tag ${statusColors[app.status] || ''}">${app.status.toUpperCase()}</span>
      </p>
      ${app.submitted_at ? `<p style="margin-top:8px;font-size:13px;color:var(--muted)">Essay submitted on ${new Date(app.submitted_at).toLocaleDateString("en-GB")}</p>` : ""}
      ${app.status === "pass" ? `<p style="margin-top:12px;color:#27ae60;font-weight:700;">🎉 Congratulations! You have been accepted as a Delegate. Please refresh the page.</p>` : ""}
      ${app.status === "fail" ? `<p style="margin-top:12px;color:#c0392b;">Your application was not successful this time. The club leadership may contact you for further information.</p>` : ""}
    `;

    // Hide upload form if already submitted or decided
    if (app.status !== "pending") {
      document.getElementById("essay-upload-card").classList.add("hidden");
    }
  } catch (err) {
    document.getElementById("app-status-content").innerHTML = `<p class="error">${err.message}</p>`;
  }

  // Essay submit
  document.getElementById("essay-form").onsubmit = async e => {
    e.preventDefault();
    const file  = document.getElementById("essay-file").files[0];
    const errEl = document.getElementById("essay-error");
    const sucEl = document.getElementById("essay-success");
    errEl.textContent = ""; sucEl.textContent = "";
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      await api.uploadFile("/users/my-application/submit-essay", fd);
      sucEl.textContent = "Essay uploaded successfully! The leadership will review it.";
      document.getElementById("essay-form").reset();
      loadApplication();
    } catch (err) {
      errEl.textContent = err.message;
    }
  };
}

// ═══════════════════════════════════════════════════════════════════
// ANNOUNCEMENTS
// ═══════════════════════════════════════════════════════════════════
async function loadAnnouncements() {
  const r = currentUser.role;
  const canManage = r === "president" || r === "vice_president" || r === "staff";

  if (canManage) {
    document.getElementById("manage-announcements-form").classList.remove("hidden");
  }

  document.getElementById("ann-form").onsubmit = async e => {
    e.preventDefault();
    try {
      await api.post("/announcements/", {
        title:     document.getElementById("ann-title").value.trim(),
        body:      document.getElementById("ann-body").value.trim(),
        is_public: document.getElementById("ann-public").checked,
        pinned:    document.getElementById("ann-pinned").checked,
      });
      document.getElementById("ann-form").reset();
      toast("Announcement published!");
      loadAnnouncements();
    } catch (err) {
      document.getElementById("ann-error").textContent = err.message;
    }
  };

  skeleton("announcements-list", 3);
  try {
    const anns = await api.get("/announcements/");
    const el   = document.getElementById("announcements-list");
    if (!anns || anns.length === 0) {
      el.innerHTML = `<div class="empty">No announcements yet.</div>`;
      return;
    }
    el.innerHTML = anns.map(a => `
      <div class="item">
        <div>
          ${a.pinned ? `<span class="tag">📌 Pinned</span>` : ""}
          ${a.is_public ? `<span class="tag">Public</span>` : ""}
          <h3>${a.title}</h3>
          <p>${a.body}</p>
          <p style="font-size:11px;color:var(--muted);margin-top:6px;">
            ${new Date(a.created_at).toLocaleDateString("en-GB")} · ${a.first_name} ${a.last_name}
          </p>
        </div>
        ${canManage ? `
          <div class="item-actions">
            <button class="btn btn-sm btn-danger" onclick="deleteAnnouncement(${a.id})">Delete</button>
          </div>
        ` : ""}
      </div>
    `).join("");
  } catch (err) {
    document.getElementById("announcements-list").innerHTML = `<div class="empty error">${err.message}</div>`;
  }
}

async function deleteAnnouncement(id) {
  if (!confirm("Delete this announcement?")) return;
  await api.delete(`/announcements/${id}`);
  toast("Deleted.");
  loadAnnouncements();
}

// ═══════════════════════════════════════════════════════════════════
// EVENTS
// ═══════════════════════════════════════════════════════════════════
async function loadEvents() {
  const r = currentUser.role;
  const canManage = r === "president" || r === "vice_president" || r === "staff";

  if (canManage) {
    document.getElementById("manage-events-form").classList.remove("hidden");
  }

  document.getElementById("event-form").onsubmit = async e => {
    e.preventDefault();
    try {
      await api.post("/events/", {
        title:       document.getElementById("ev-title").value.trim(),
        event_date:  document.getElementById("ev-date").value,
        event_time:  document.getElementById("ev-time").value || null,
        location:    document.getElementById("ev-location").value.trim() || null,
        description: document.getElementById("ev-desc").value.trim() || null,
        is_public:   document.getElementById("ev-public").checked,
      });
      document.getElementById("event-form").reset();
      toast("Event published!");
      loadEvents();
    } catch (_) {}
  };

  try {
    const events = await api.get("/events/");
    const el     = document.getElementById("events-list");
    if (!events || events.length === 0) {
      el.innerHTML = `<div class="empty">No events scheduled.</div>`;
      return;
    }
    el.innerHTML = events.map(e => `
      <div class="item">
        <div>
          <h3>${e.title}</h3>
          <p>${e.event_date}${e.event_time ? " at " + e.event_time : ""}${e.location ? " · " + e.location : ""}</p>
          ${e.description ? `<p style="margin-top:6px;">${e.description}</p>` : ""}
          ${e.is_public ? `<span class="tag">Public</span>` : ""}
        </div>
        ${canManage ? `<button class="btn btn-sm btn-danger" onclick="deleteEvent(${e.id})">Delete</button>` : ""}
      </div>
    `).join("");
  } catch (_) {}
}

async function deleteEvent(id) {
  if (!confirm("Delete this event?")) return;
  await api.delete(`/events/${id}`);
  toast("Deleted.");
  loadEvents();
}

// ═══════════════════════════════════════════════════════════════════
// MOCK TRIALS
// ═══════════════════════════════════════════════════════════════════
async function loadMockTrials() {
  const r = currentUser.role;
  const isLeader = r === "president" || r === "vice_president";

  if (isLeader) {
    document.getElementById("manage-trials-form").classList.remove("hidden");
  }

  document.getElementById("trial-form").onsubmit = async e => {
    e.preventDefault();
    try {
      await api.post("/mock-trials/", {
        title:        document.getElementById("tr-title").value.trim(),
        trial_date:   document.getElementById("tr-date").value,
        trial_time:   document.getElementById("tr-time").value || null,
        trial_type:   document.getElementById("tr-type").value,
        case_topic:   document.getElementById("tr-topic").value.trim() || null,
        instructions: document.getElementById("tr-instructions").value.trim() || null,
      });
      document.getElementById("trial-form").reset();
      toast("Mock trial scheduled!");
      loadMockTrials();
    } catch (_) {}
  };

  try {
    const trials = await api.get("/mock-trials/");
    const el     = document.getElementById("trials-list");
    if (!trials || trials.length === 0) {
      el.innerHTML = `<div class="empty">No mock trials scheduled yet.</div>`;
      return;
    }
    el.innerHTML = trials.map(t => `
      <div class="item">
        <div>
          <span class="tag">${t.trial_type}</span>
          <span class="tag">${t.status}</span>
          <h3>${t.title}</h3>
          <p>${t.trial_date}${t.trial_time ? " at " + t.trial_time : ""}</p>
          ${t.case_topic ? `<p style="margin-top:6px;">${t.case_topic}</p>` : ""}
        </div>
      </div>
    `).join("");
  } catch (_) {}
}

// ═══════════════════════════════════════════════════════════════════
// ASSIGNMENTS & FILES HELPERS
// ═══════════════════════════════════════════════════════════════════
let currentAsgnFilter = "all";
let cachedAsgnFiles = [];
let cachedAsgnTasks = [];

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function categoryLabel(cat) {
  const map = {
    assignment: "Assignment",
    rules: "Club Rules",
    case: "Case File",
    constitution: "Constitution",
    general: "General"
  };
  return map[cat] || (cat ? cat.toUpperCase() : "GENERAL");
}

function cleanFilename(name) {
  if (!name) return "Document";
  const parts = name.split("_");
  if (parts.length > 1 && parts[0].length >= 32) {
    return parts.slice(1).join("_");
  }
  return name;
}

function renderAssignmentsList() {
  const el = document.getElementById("assignments-list");
  if (!el) return;
  const r = currentUser.role;
  const canManage = r === "president" || r === "vice_president" || r === "staff";

  let filteredFiles = cachedAsgnFiles;
  if (currentAsgnFilter !== "all") {
    filteredFiles = cachedAsgnFiles.filter(f => f.category === currentAsgnFilter);
  }

  let filteredTasks = cachedAsgnTasks;
  if (currentAsgnFilter !== "all" && currentAsgnFilter !== "assignment") {
    filteredTasks = [];
  }

  if (filteredFiles.length === 0 && filteredTasks.length === 0) {
    const filterName = currentAsgnFilter === "all" ? "assignments or club documents" : `${categoryLabel(currentAsgnFilter)} files`;
    el.innerHTML = `<div class="empty">No ${filterName} published at this time.</div>`;
    return;
  }

  let html = "";

  // Render formal tasks (if any)
  filteredTasks.forEach(t => {
    html += `
      <div class="item" style="border-left: 4px solid var(--gold);">
        <div>
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
            <span class="tag tag-assignment">[ASSIGNMENT]</span>
            ${t.deadline ? `<span style="font-size:11px;color:var(--muted);">Due: ${new Date(t.deadline).toLocaleDateString("en-GB")}</span>` : ""}
          </div>
          <h3 style="margin:2px 0 6px;">${escapeHtml(t.title)}</h3>
          ${t.description ? `<p style="margin-bottom:4px;color:var(--fg);font-size:13px;">${escapeHtml(t.description)}</p>` : ""}
          ${t.instructions ? `<p style="font-size:12px;color:var(--muted);">${escapeHtml(t.instructions)}</p>` : ""}
        </div>
      </div>
    `;
  });

  // Render files with category badges
  filteredFiles.forEach(f => {
    const badgeText = categoryLabel(f.category);
    const catClass = f.category ? `tag-${f.category}` : "tag-general";
    const displayName = cleanFilename(f.filename);
    const dateStr = f.uploaded_at ? new Date(f.uploaded_at).toLocaleDateString("en-GB") : "";

    html += `
      <div class="item">
        <div>
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
            <span class="tag ${catClass}">[${badgeText.toUpperCase()}]</span>
            ${dateStr ? `<span style="font-size:11px;color:var(--muted);">Uploaded ${dateStr}</span>` : ""}
          </div>
          <h3 style="margin:2px 0 6px;">${escapeHtml(displayName)}</h3>
          ${f.description ? `<p style="margin-bottom:4px;color:var(--fg);font-size:13px;">${escapeHtml(f.description)}</p>` : ""}
          <p style="font-size:11px;color:var(--muted);">File: ${escapeHtml(displayName)}</p>
        </div>
        <div class="item-actions">
          <a class="btn btn-sm btn-gold" href="${f.file_url}" target="_blank" rel="noopener">Download / View →</a>
          ${canManage ? `<button class="btn btn-sm btn-danger" onclick="deleteAssignmentFile(${f.id})">Delete</button>` : ""}
        </div>
      </div>
    `;
  });

  el.innerHTML = html;
}

// ═══════════════════════════════════════════════════════════════════
// ASSIGNMENTS
// ═══════════════════════════════════════════════════════════════════
async function loadAssignments() {
  const r = currentUser.role;
  const canManage = r === "president" || r === "vice_president" || r === "staff";

  const formCard = document.getElementById("manage-assignments-form");
  if (formCard) {
    if (canManage) formCard.classList.remove("hidden");
    else formCard.classList.add("hidden");
  }

  // Filter buttons click handler
  document.querySelectorAll("#asgn-filter-bar .filter-btn").forEach(btn => {
    btn.onclick = () => {
      document.querySelectorAll("#asgn-filter-bar .filter-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentAsgnFilter = btn.dataset.filter;
      renderAssignmentsList();
    };
  });

  // Assignment upload form
  const uploadForm = document.getElementById("assignment-upload-form");
  if (uploadForm) {
    uploadForm.onsubmit = async e => {
      e.preventDefault();
      const file = document.getElementById("asgn-upload-file").files[0];
      const errEl = document.getElementById("asgn-upload-error");
      if (errEl) errEl.textContent = "";
      if (!file) return;

      const fd = new FormData();
      fd.append("file", file);
      fd.append("category", document.getElementById("asgn-upload-cat").value);
      fd.append("description", document.getElementById("asgn-upload-desc").value.trim());

      try {
        await api.uploadFile("/files/upload", fd);
        uploadForm.reset();
        toast("File published successfully!");
        await loadAssignments();
        if (typeof loadFiles === "function") loadFiles();
      } catch (err) {
        if (errEl) errEl.textContent = err.message;
      }
    };
  }

  try {
    const [files, tasks] = await Promise.all([
      api.get("/files/").catch(() => []),
      api.get("/assignments/my").catch(() => [])
    ]);
    cachedAsgnFiles = files || [];
    cachedAsgnTasks = tasks || [];
    renderAssignmentsList();
  } catch (err) {
    const el = document.getElementById("assignments-list");
    if (el) el.innerHTML = `<div class="empty">${escapeHtml(err.message)}</div>`;
  }
}

async function deleteAssignmentFile(id) {
  if (!confirm("Are you sure you want to delete this file?")) return;
  try {
    await api.delete(`/files/${id}`);
    toast("File deleted.");
    await loadAssignments();
    if (typeof loadFiles === "function") loadFiles();
  } catch (err) {
    toast(err.message);
  }
}

// ═══════════════════════════════════════════════════════════════════
// CASE FILES
// ═══════════════════════════════════════════════════════════════════
async function loadFiles() {
  const r = currentUser.role;
  const canManage = r === "president" || r === "vice_president" || r === "staff";

  const formCard = document.getElementById("manage-files-form");
  if (formCard) {
    if (canManage) formCard.classList.remove("hidden");
    else formCard.classList.add("hidden");
  }

  const uploadForm = document.getElementById("file-upload-form");
  if (uploadForm) {
    uploadForm.onsubmit = async e => {
      e.preventDefault();
      const file = document.getElementById("upload-file").files[0];
      const errEl = document.getElementById("upload-error");
      if (errEl) errEl.textContent = "";
      if (!file) return;

      const fd = new FormData();
      fd.append("file", file);
      fd.append("category", document.getElementById("upload-cat").value);
      fd.append("description", document.getElementById("upload-desc").value.trim());

      try {
        await api.uploadFile("/files/upload", fd);
        uploadForm.reset();
        toast("File uploaded!");
        await loadFiles();
        if (typeof loadAssignments === "function") loadAssignments();
      } catch (err) {
        if (errEl) errEl.textContent = err.message;
      }
    };
  }

  try {
    const files = await api.get("/files/");
    const el = document.getElementById("files-list");
    if (!el) return;
    if (!files || files.length === 0) {
      el.innerHTML = `<div class="empty">No documents available.</div>`;
      return;
    }
    el.innerHTML = files.map(f => {
      const badgeText = categoryLabel(f.category);
      const catClass = f.category ? `tag-${f.category}` : "tag-general";
      const displayName = cleanFilename(f.filename);
      const dateStr = f.uploaded_at ? new Date(f.uploaded_at).toLocaleDateString("en-GB") : "";

      return `
        <div class="item">
          <div>
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
              <span class="tag ${catClass}">[${badgeText.toUpperCase()}]</span>
              ${dateStr ? `<span style="font-size:11px;color:var(--muted);">Uploaded ${dateStr}</span>` : ""}
            </div>
            <h3 style="margin:2px 0 6px;">${escapeHtml(displayName)}</h3>
            ${f.description ? `<p style="margin-bottom:4px;color:var(--fg);font-size:13px;">${escapeHtml(f.description)}</p>` : ""}
            <p style="font-size:11px;color:var(--muted);">File: ${escapeHtml(displayName)}</p>
          </div>
          <div class="item-actions">
            <a class="btn btn-sm btn-gold" href="${f.file_url}" target="_blank" rel="noopener">Download / View →</a>
            ${canManage ? `<button class="btn btn-sm btn-danger" onclick="deleteFile(${f.id})">Delete</button>` : ""}
          </div>
        </div>
      `;
    }).join("");
  } catch (_) {}
}

async function deleteFile(id) {
  if (!confirm("Delete this file?")) return;
  try {
    await api.delete(`/files/${id}`);
    toast("Deleted.");
    await loadFiles();
    if (typeof loadAssignments === "function") loadAssignments();
  } catch (err) {
    toast(err.message);
  }
}

// ═══════════════════════════════════════════════════════════════════
// CHAT
// ═══════════════════════════════════════════════════════════════════
async function loadChat() {
  // Stop any existing poll before starting fresh
  if (_chatPollTimer) { clearInterval(_chatPollTimer); _chatPollTimer = null; }

  const r = currentUser.role;
  const isLeader = r === "president" || r === "vice_president";

  if (isLeader) {
    document.getElementById("manage-room-form").classList.remove("hidden");
  }

  document.getElementById("room-form").onsubmit = async e => {
    e.preventDefault();
    try {
      const name = document.getElementById("room-name").value.trim();
      const addAll = document.getElementById("room-all-delegates")?.checked ?? true;
      await api.post("/chat/rooms", { name, add_all_delegates: addAll });
      document.getElementById("room-form").reset();
      toast("Group chat created!");
      loadChat();
    } catch (err) { toast(err.message); }
  };

  skeleton("room-list", 2);
  try {
    const rooms = await api.get("/chat/rooms");
    const el    = document.getElementById("room-list");
    if (!rooms || rooms.length === 0) {
      el.innerHTML = `<div class="empty">No chat rooms.</div>`;
      return;
    }
    el.innerHTML = rooms.map(r => `
      <div class="item${r.id === currentRoomId ? ' active-room' : ''}" style="cursor:pointer;" onclick="openRoom(${r.id}, '${escHtml(r.name)}')">
        <div>
          <h3>${r.name}</h3>
          <span class="tag">${r.room_type}</span>
        </div>
        ${isLeader && r.room_type !== "general" ? `<button class="btn btn-sm btn-danger" onclick="event.stopPropagation();deleteRoom(${r.id})">Delete</button>` : ""}
      </div>
    `).join("");

    // Automatically open the first room (General) on load
    if (!currentRoomId && rooms.length > 0) {
      openRoom(rooms[0].id, rooms[0].name);
    }
  } catch (_) {}
}

async function openRoom(roomId, name) {
  currentRoomId = roomId;
  document.getElementById("chat-view").classList.remove("hidden");
  document.getElementById("chat-room-title").textContent = name;

  // Stop old poll, load immediately, then start live 5-second poll
  if (_chatPollTimer) { clearInterval(_chatPollTimer); _chatPollTimer = null; }
  await loadMessages();
  _chatPollTimer = setInterval(() => {
    // Only poll if the chat panel is still visible
    const panel = document.getElementById("panel-chat");
    if (panel && panel.classList.contains("active")) {
      loadMessages();
    } else {
      clearInterval(_chatPollTimer);
      _chatPollTimer = null;
    }
  }, 5000);
}

async function loadMessages() {
  if (!currentRoomId) return;
  try {
    // Don't use cache for messages — always want the latest
    const url = `${API_BASE}/chat/rooms/${currentRoomId}/messages`;
    const res = await fetch(url, { credentials: "include" });
    if (!res.ok) return;
    const msgs = await res.json();
    const el   = document.getElementById("chat-messages");
    const wasAtBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60;

    const html = msgs.map(m => `
      <div class="bubble${m.username === currentUser.username ? " mine" : ""}">
        ${escHtml(m.body)}
        <small>${m.first_name} · ${new Date(m.sent_at).toLocaleTimeString("en-GB", {hour:"2-digit",minute:"2-digit"})}</small>
      </div>
    `).join("");

    if (el.innerHTML !== html) {
      el.innerHTML = html;
      if (wasAtBottom) el.scrollTop = el.scrollHeight;
    }
  } catch (_) {}
}

async function sendMsg() {
  const inp = document.getElementById("chat-input");
  const body = inp.value.trim();
  if (!body || !currentRoomId) return;
  inp.value = "";
  try {
    // Optimistically show own message immediately
    const el = document.getElementById("chat-messages");
    el.innerHTML += `
      <div class="bubble mine">
        ${escHtml(body)}
        <small>${currentUser.first_name} · ${new Date().toLocaleTimeString("en-GB", {hour:"2-digit",minute:"2-digit"})}</small>
      </div>`;
    el.scrollTop = el.scrollHeight;

    await fetch(`${API_BASE}/chat/rooms/${currentRoomId}/messages`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ body }),
    });
    // Real data will sync on next 5-second poll
  } catch (_) {}
}

document.getElementById("chat-input")?.addEventListener("keydown", e => {
  if (e.key === "Enter") sendMsg();
});

async function deleteRoom(id) {
  if (!confirm("Delete this group chat?")) return;
  await api.delete(`/chat/rooms/${id}`);
  toast("Room deleted.");
  loadChat();
}

// ═══════════════════════════════════════════════════════════════════
// RANKINGS
// ═══════════════════════════════════════════════════════════════════
async function loadRankings() {
  const r = currentUser.role;
  const canManage = r === "president" || r === "vice_president" || r === "staff";

  if (canManage) {
    document.getElementById("manage-points-form").classList.remove("hidden");
  }

  try {
    const pts = await api.get("/points/my");
    document.getElementById("my-points-val").textContent = pts.total;
  } catch (_) {}

  document.getElementById("points-form").onsubmit = async e => {
    e.preventDefault();
    try {
      await api.post("/points/award", {
        user_id: parseInt(document.getElementById("pts-uid").value),
        delta:   parseInt(document.getElementById("pts-delta").value),
        reason:  document.getElementById("pts-reason").value.trim() || null,
      });
      document.getElementById("points-form").reset();
      toast("Points updated!");
      loadRankings();
    } catch (err) { toast(err.message); }
  };

  try {
    const list = await api.get("/points/rankings");
    const tbody = document.getElementById("rankings-body");
    if (!list || list.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" style="text-align:center;color:var(--muted)">No ranking data yet.</td></tr>`;
      return;
    }
    tbody.innerHTML = list.map((m, i) => `
      <tr>
        <td>${i + 1}</td>
        <td>${m.first_name} ${m.last_name}</td>
        <td>#${String(m.member_number).padStart(3,"0")}</td>
        <td><strong>${m.total}</strong></td>
      </tr>
    `).join("");
  } catch (_) {}
}

// ═══════════════════════════════════════════════════════════════════
// CERTIFICATES
// ═══════════════════════════════════════════════════════════════════
async function loadCerts() {
  const r = currentUser.role;
  const isLeader = r === "president" || r === "vice_president";

  if (isLeader) {
    document.getElementById("manage-cert-form").classList.remove("hidden");
  }

  document.getElementById("cert-form").onsubmit = async e => {
    e.preventDefault();
    try {
      await api.post("/certificates/", {
        user_id:  parseInt(document.getElementById("cert-uid").value),
        category: document.getElementById("cert-cat").value.trim(),
        title:    document.getElementById("cert-title").value.trim() || null,
        notes:    document.getElementById("cert-notes").value.trim() || null,
      });
      document.getElementById("cert-form").reset();
      toast("Certificate issued!");
      loadCerts();
    } catch (err) { toast(err.message); }
  };

  const endpoint = isLeader ? "/certificates/all" : "/certificates/my";
  try {
    const certs = await api.get(endpoint);
    const el    = document.getElementById("certs-list");
    if (!certs || certs.length === 0) {
      el.innerHTML = `<div class="empty">No certificates yet.</div>`;
      return;
    }
    el.innerHTML = certs.map(c => `
      <div class="item">
        <div>
          <span class="tag">${c.category}</span>
          <h3>${c.title || c.category}</h3>
          <p>Issued ${new Date(c.issued_at).toLocaleDateString("en-GB")}</p>
          ${c.notes ? `<p style="font-size:12px;color:var(--muted);">${c.notes}</p>` : ""}
        </div>
        ${isLeader ? `<button class="btn btn-sm btn-danger" onclick="revokeCert(${c.id})">Revoke</button>` : ""}
      </div>
    `).join("");
  } catch (_) {}
}

async function revokeCert(id) {
  if (!confirm("Revoke this certificate?")) return;
  await api.delete(`/certificates/${id}`);
  toast("Certificate revoked.");
  loadCerts();
}

// ═══════════════════════════════════════════════════════════════════
// MEMBERS (leaders only)
// ═══════════════════════════════════════════════════════════════════
async function loadMembers() {
  try {
    membersList = await api.get("/users/");
    renderMembers(membersList);
  } catch (_) {}
}

function renderMembers(list) {
  const tbody = document.getElementById("members-body");
  if (!list || list.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:var(--muted)">No members found.</td></tr>`;
    return;
  }
  tbody.innerHTML = list.map(m => `
    <tr>
      <td>#${String(m.member_number).padStart(3,"0")}</td>
      <td>${m.first_name} ${m.last_name}</td>
      <td>${m.username}</td>
      <td>${m.grade || "—"}</td>
      <td><span class="tag">${roleLabel(m.role)}</span></td>
      <td><span class="tag ${m.status}">${m.status}</span></td>
      <td>
        ${m.status === "active" ? `<button class="btn btn-sm btn-danger" onclick="setStatus(${m.id},'suspended')">Suspend</button>` : ""}
        ${m.status === "suspended" ? `<button class="btn btn-sm btn-light" onclick="setStatus(${m.id},'active')">Restore</button>` : ""}
        <button class="btn btn-sm btn-danger" onclick="setStatus(${m.id},'deleted')">Remove</button>
      </td>
    </tr>
  `).join("");
}

function filterMembers() {
  const q = document.getElementById("member-search").value.toLowerCase();
  renderMembers(membersList.filter(m =>
    (m.first_name + " " + m.last_name + " " + m.username).toLowerCase().includes(q)
  ));
}

async function setStatus(uid, status) {
  if (status === "deleted" && !confirm("Permanently remove this account? The member number will NOT be reused.")) return;
  try {
    await api.patch(`/users/${uid}/status`, { status });
    toast("Member status updated.");
    loadMembers();
  } catch (err) { toast(err.message); }
}

// ═══════════════════════════════════════════════════════════════════
// APPLICATION REVIEW
// ═══════════════════════════════════════════════════════════════════
async function loadApplications() {
  try {
    const list = await api.get("/users/applicants");
    const el   = document.getElementById("applications-list");
    if (!list || list.length === 0) {
      el.innerHTML = `<div class="empty">No pending applications.</div>`;
      return;
    }
    el.innerHTML = list.map(a => `
      <div class="item">
        <div>
          <span class="tag ${a.app_status}">${a.app_status.toUpperCase()}</span>
          <h3>${a.first_name} ${a.last_name}</h3>
          <p>Grade ${a.grade} · Applied ${new Date(a.created_at || a.submitted_at || "").toLocaleDateString("en-GB")}</p>
          ${a.essay_filename ? `<p style="font-size:12px;margin-top:4px;">File: <strong>${a.essay_filename}</strong></p>` : `<p style="font-size:12px;color:var(--muted);margin-top:4px;">(No essay file submitted yet)</p>`}
        </div>
        <div class="item-actions">
          ${a.essay_url ? `<a class="btn btn-sm btn-light" href="${a.essay_url.startsWith('http') ? a.essay_url : API_BASE.replace('/api','') + a.essay_url}" target="_blank" rel="noopener">Read Essay 📄</a>` : ""}
          ${a.app_status === "submitted" || a.app_status === "pending" ? `
            <button class="btn btn-sm btn-gold" onclick="decideApp(${a.application_id},'pass')">PASS ✓</button>
            <button class="btn btn-sm btn-danger" onclick="decideApp(${a.application_id},'fail')">FAIL ✗</button>
          ` : ""}
        </div>
      </div>
    `).join("");
  } catch (err) {
    document.getElementById("applications-list").innerHTML = `<div class="empty error">${err.message}</div>`;
  }
}

async function decideApp(appId, decision) {
  const label = decision === "pass" ? "PASS (promote to Delegate)" : "FAIL (reject)";
  if (!confirm(`Mark this application as ${label}?`)) return;
  try {
    await api.post(`/users/application/${appId}/decide`, { decision });
    toast(`Application marked ${decision.toUpperCase()}.`);
    loadApplications();
  } catch (err) { toast(err.message); }
}

// ═══════════════════════════════════════════════════════════════════
// SETTINGS
// ═══════════════════════════════════════════════════════════════════
async function loadSettings() {
  try {
    const s = await api.get("/settings/");
    if (!s) return;
    document.getElementById("set-name").value        = s.club_name        || "";
    document.getElementById("set-motto").value       = s.motto            || "";
    document.getElementById("set-mission").value     = s.mission          || "";
    document.getElementById("set-vision").value      = s.vision           || "";
    document.getElementById("set-pres-ig").value     = s.president_instagram || "";
    document.getElementById("set-vp-ig").value       = s.vp_instagram     || "";
    document.getElementById("set-capacity").value    = s.delegate_capacity || 55;
    document.getElementById("set-trial-time").value  = s.mock_trial_time  || "15:00";
    document.getElementById("set-recruitment").checked = s.recruitment_open;
  } catch (_) {}

  document.getElementById("settings-form").onsubmit = async e => {
    e.preventDefault();
    try {
      await api.patch("/settings/", {
        club_name:            document.getElementById("set-name").value.trim(),
        motto:                document.getElementById("set-motto").value.trim(),
        mission:              document.getElementById("set-mission").value.trim(),
        vision:               document.getElementById("set-vision").value.trim(),
        president_instagram:  document.getElementById("set-pres-ig").value.trim(),
        vp_instagram:         document.getElementById("set-vp-ig").value.trim(),
        delegate_capacity:    parseInt(document.getElementById("set-capacity").value) || 55,
        mock_trial_time:      document.getElementById("set-trial-time").value,
        recruitment_open:     document.getElementById("set-recruitment").checked,
      });
      toast("Settings saved!");
    } catch (err) { toast(err.message); }
  };

  document.getElementById("code-form").onsubmit = async e => {
    e.preventDefault();
    const errEl = document.getElementById("code-error");
    errEl.textContent = "";
    const delegateCode = document.getElementById("code-delegate").value.trim();
    const leaderCode   = document.getElementById("code-leader").value.trim();
    try {
      if (delegateCode) await api.patch("/settings/access-codes", { role: "delegate", code: delegateCode });
      if (leaderCode)   await api.patch("/settings/access-codes", { role: "leader",   code: leaderCode });
      document.getElementById("code-form").reset();
      toast("Access codes updated!");
    } catch (err) { errEl.textContent = err.message; }
  };
}

// ═══════════════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════════════
function toast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  setTimeout(() => el.classList.add("hidden"), 3500);
}

function escHtml(str) {
  return String(str).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

async function logout() {
  try {
    await api.post("/auth/logout", {});
  } catch (_) {}

  // 1. Immediately wipe all in-memory state
  currentUser   = null;
  currentRoomId = null;
  membersList   = [];

  // 2. Wipe browser storage (preserves only dark/light theme setting)
  const savedTheme = localStorage.getItem("theme");
  try {
    localStorage.clear();
    sessionStorage.clear();
  } catch (_) {}
  if (savedTheme) {
    localStorage.setItem("theme", savedTheme);
  }

  // 3. Clear DOM elements so nothing remains visible
  const panelsEl = document.getElementById("panels");
  if (panelsEl) panelsEl.innerHTML = "<div class='empty'>Signed out.</div>";
  const navUser = document.getElementById("nav-username");
  if (navUser) navUser.textContent = "";
  const welcome = document.getElementById("welcome-msg");
  if (welcome) welcome.textContent = "";

  // 4. Replace location so the Back button cannot restore previous user data
  window.location.replace("login.html");
}

// Ensure back-forward cache revalidates authentication
window.addEventListener("pageshow", function (event) {
  if (event.persisted) {
    bootstrap();
  }
});

// ── START ──────────────────────────────────────────────────────────
bootstrap();
