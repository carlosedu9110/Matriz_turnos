// Cliente mínimo de la API (mismo origen que el frontend).
const Api = {
  token: sessionStorage.getItem("token"),

  setToken(t) {
    this.token = t;
    t ? sessionStorage.setItem("token", t) : sessionStorage.removeItem("token");
  },

  async request(method, path, body) {
    const headers = {};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (this.token) headers["Authorization"] = `Bearer ${this.token}`;
    const res = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
    if (res.status === 401 && this.token) {
      this.setToken(null);
      location.reload();
    }
    if (!res.ok) {
      let msg = `Error ${res.status}`;
      let detail = null;
      try {
        detail = (await res.json()).detail;
        msg = typeof detail === "string" ? detail : Array.isArray(detail) ? detail.map((e) => e.msg).join("; ") : detail?.mensaje || msg;
      } catch (_) { /* sin cuerpo */ }
      const err = new Error(msg);
      err.status = res.status;
      err.detail = detail;
      throw err;
    }
    return res.status === 204 ? null : res.json();
  },

  get: (p) => Api.request("GET", p),
  post: (p, b) => Api.request("POST", p, b),
  patch: (p, b) => Api.request("PATCH", p, b),
  del: (p) => Api.request("DELETE", p),
};
