import axios from "axios";

const API = axios.create({
  baseURL:
    //import.meta.env.VITE_API_BASE_URL || "http://192.168.29.236:8000/api/",
      import.meta.env.VITE_API_BASE_URL || "http://192.168.4.101:8000/api/",
    //import.meta.env.VITE_API_BASE_URL || "http://10.240.23.101:8000/api/",
});

// API.interceptors.request.use((req) => {
//   const token = localStorage.getItem("access");

//   if (token) {
//     req.headers.Authorization = `Bearer ${token}`;
//   }

//   return req;
// });

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

    if (error.response?.status === 401) {

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