import axios from "axios";

const axiosClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30000,   // 30 s — Google Places chain can be slow
});

// Global response error interceptor
axiosClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.message ||
      "Đã xảy ra lỗi không mong muốn.";
    return Promise.reject(new Error(message));
  }
);

export default axiosClient;