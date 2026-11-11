import axios from "axios";

export const TOKEN_KEY = "credential_access_token";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1",
  headers: { "Content-Type": "application/json" },
  timeout: 15000,
});

api.interceptors.request.use((config) => {
  const token = window.localStorage.getItem(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && window.localStorage.getItem(TOKEN_KEY)) {
      window.localStorage.removeItem(TOKEN_KEY);
      window.dispatchEvent(new CustomEvent("credential:unauthorized"));
    }
    return Promise.reject(error);
  },
);

export function getErrorMessage(error) {
  const status = error.response?.status;
  const detail = error.response?.data?.detail;
  if (status === 401) return "Your session has expired or your sign-in details are incorrect. Please sign in again.";
  if (status === 403) return "Your account does not have permission to perform this action.";
  if (status === 404) return typeof detail === "string" ? detail : "The requested record was not found.";
  if (status === 409) return typeof detail === "string" ? detail : "This change conflicts with an existing record.";
  if (status === 422) return typeof detail === "string" ? detail : "Check the submitted values and try again.";
  if (status >= 500) return "The service could not complete the request. Please try again later.";
  if (!error.response) return "Could not reach the API. Check that the backend is running and try again.";
  return typeof detail === "string" ? detail : "The request could not be completed.";
}

export default api;
