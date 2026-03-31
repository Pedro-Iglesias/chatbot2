import api from "./api";

export const authService = {
  async login(username, password) {
    const response = await api.post("/api/token/", { username, password });
    localStorage.setItem("access_token", response.data.access);
    localStorage.setItem("refresh_token", response.data.refresh);
    return response.data;
  },

  logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  },

  isAuthenticated() {
    return !!localStorage.getItem("access_token");
  },
};