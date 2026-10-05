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
      try {
        const d = (await res.json()).detail;
        msg = typeof d === "string" ? d : Array.isArray(d) ? d.map((e) => e.msg).join("; ") : msg;
      } catch (_) { /* sin cuerpo */ }
      throw new Error(msg);
    }
    return res.status === 204 ? null : res.json();
  },

  get: (p) => Api.request("GET", p),
  post: (p, b) => Api.request("POST", p, b),
  del: (p) => Api.request("DELETE", p),
};
