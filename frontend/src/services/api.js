import axios from "axios";

const api = axios.create({
  baseURL: "https://topsis-backend.onrender.com",
});

export default api;
