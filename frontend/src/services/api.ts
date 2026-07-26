import axios from "axios"

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
  timeout: 30000,
})

api.interceptors.response.use(
  (res) => res,
  (error) => {
    console.error("API Error:", error)
    return Promise.reject(error)
  },
)

export default api
