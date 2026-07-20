// Login: envía credenciales a /api/auth/login. El backend setea las cookies
// HttpOnly; aquí solo redirigimos al dashboard si todo sale bien.
document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errorEl = document.getElementById("login-error");
  errorEl.hidden = true;

  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      errorEl.textContent = data.error || "No se pudo iniciar sesión";
      errorEl.hidden = false;
      return;
    }
    window.location.href = "/dashboard";
  } catch (err) {
    errorEl.textContent = "Error de red. Intenta de nuevo.";
    errorEl.hidden = false;
  }
});
