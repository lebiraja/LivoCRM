import axios from "axios";

// Vite env var — falls back to relative /api for production (proxied by nginx)
const API_URL = import.meta.env.VITE_API_URL || "/api";

const client = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

// On 401 the browser session is invalid or expired; return to the login page.
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (
        !window.location.pathname.includes("/login") &&
        !window.location.pathname.includes("/register")
      ) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export default client;
