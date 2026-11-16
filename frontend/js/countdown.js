// js/countdown.js
// Calculates the next monthly mock trial (last day of each month)
// and displays a live countdown.

function getNextMockTrialDate() {
  const now  = new Date();
  let   year = now.getFullYear();
  let   month= now.getMonth();   // 0-indexed

  // Last day of THIS month
  let lastDay = new Date(year, month + 1, 0); // day 0 of next month = last day of this month

  // If we're past the last day of this month (or today IS the last day), move to next month
  if (now.getDate() >= lastDay.getDate()) {
    month++;
    if (month > 11) { month = 0; year++; }
    lastDay = new Date(year, month + 1, 0);
  }

  // Set to 15:00 (default trial time — matches club_settings.mock_trial_time)
  lastDay.setHours(15, 0, 0, 0);
  return lastDay;
}

function updateCountdown() {
  const target  = getNextMockTrialDate();
  const now     = new Date();
  const diff    = target - now;

  if (diff <= 0) {
    // Reset for the next month
    setTimeout(updateCountdown, 1000);
    return;
  }

  const days    = Math.floor(diff / 86400000);
  const hours   = Math.floor((diff % 86400000) / 3600000);
  const minutes = Math.floor((diff % 3600000)  / 60000);
  const seconds = Math.floor((diff % 60000)    / 1000);

  const set = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = String(val).padStart(2, "0");
  };

  set("cd-days",    days);
  set("cd-hours",   hours);
  set("cd-minutes", minutes);
  set("cd-seconds", seconds);

  const label = document.getElementById("cd-date-label");
  if (label) {
    label.textContent = target.toLocaleDateString("en-GB", {
      weekday: "long", day: "numeric", month: "long", year: "numeric"
    });
  }
}

// Start ticking
if (document.getElementById("cd-seconds")) {
  updateCountdown();
  setInterval(updateCountdown, 1000);
}
