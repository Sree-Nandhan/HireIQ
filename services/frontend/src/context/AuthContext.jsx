import { createContext, useContext, useState } from "react";
import api from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [user, setUser] = useState(null);

  const fetchMe = async () => {
    try {
      const res = await api.get("/me");
      setUser(res.data);
    } catch { /* ignore */ }
  };

  const login = async (email, password) => {
    const res = await api.post("/login", { email, password });
    localStorage.setItem("token", res.data.access_token);
    setToken(res.data.access_token);
    await fetchMe();
  };

  const register = async (email, password, firstName, lastName) => {
    const res = await api.post("/register", { email, password, first_name: firstName, last_name: lastName });
    localStorage.setItem("token", res.data.access_token);
    setToken(res.data.access_token);
    await fetchMe();
  };

  const logout = () => {
    localStorage.removeItem("token");
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ token, user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
