// Lógica compartida de las páginas internas.

// Logout: revoca el refresh token en el backend y vuelve al login.
const logoutBtn = document.getElementById("logout-btn");
if (logoutBtn) {
  logoutBtn.addEventListener("click", async () => {
    await fetch("/api/auth/logout", { method: "POST" });
    window.location.href = "/login";
  });
}

// Helper: fetch a la API que, si el access token expiró (401), intenta
// refrescarlo una vez y reintenta la petición original.
async function apiFetch(url, options = {}) {
  let res = await fetch(url, options);
  if (res.status === 401) {
    const r = await fetch("/api/auth/refresh", { method: "POST" });
    if (r.ok) {
      res = await fetch(url, options);
    } else {
      window.location.href = "/login";
    }
  }
  return res;
}

window.apiFetch = apiFetch;
