import axios from "axios";

/**
 * Local dev: Vite proxies /api → Django (see vite.config.js).
 * Docker UAT: nginx serves same-origin /api/.
 */
const API = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api/",
});

// ==========================
// REQUEST INTERCEPTOR
// ==========================

API.interceptors.request.use(

  (config) => {

    const token =
      localStorage.getItem("access");

    if (token) {

      config.headers.Authorization =
        `Bearer ${token}`;
    }

    return config;
  },

  (error) => Promise.reject(error)
);


// ==========================
// RESPONSE INTERCEPTOR
// ==========================

API.interceptors.response.use(

  (response) => response,

  (error) => {

    const status = error.response?.status;
    const url = String(error.config?.url ?? "");
    const isAuthEndpoint =
      /(^|\/)login\/?(\?|$)/.test(url) || /(^|\/)token\/refresh\/?(\?|$)/.test(url);

    if (status === 401 && !isAuthEndpoint) {

      // Clear tokens
      localStorage.removeItem("access");

      localStorage.removeItem("refresh");

      // Redirect login
      alert("Session expired. Please login again.");
      window.location.href = "/login";
    }

    return Promise.reject(error);
  }
);

export default API;