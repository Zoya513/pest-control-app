import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

const api = axios.create({ baseURL: API });

api.interceptors.request.use((cfg) => {
  const t = localStorage.getItem("pest_token");
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401 && !window.location.pathname.startsWith("/login")) {
      localStorage.removeItem("pest_token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export function fileUrl(path) {
  const t = localStorage.getItem("pest_token");
  return `${API}/files/${path}?auth=${encodeURIComponent(t || "")}`;
}

export default api;
