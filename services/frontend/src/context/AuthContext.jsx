import { createContext, useContext, useState } from "react";
import api from "../api/client";

const LOG = "[AuthContext]";
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [user, setUser]   = useState(null);

  const fetchMe = async () => {
    try {
      const res = await api.get("/me");
      setUser(res.data);
      console.log(`${LOG} Fetched user profile:`, res.data.email);
    } catch (err) {
      console.warn(`${LOG} fetchMe failed — likely no token yet:`, err.message);
    }
  };

  const login = async (email, password) => {
    console.log(`${LOG} Attempting login for:`, email);
    const res = await api.post("/login", { email, password });
    localStorage.setItem("token", res.data.access_token);
    setToken(res.data.access_token);
    console.log(`${LOG} Login successful`);
    await fetchMe();
  };

  const register = async (email, password, firstName, lastName) => {
    console.log(`${LOG} Registering new user:`, email);
    const res = await api.post("/register", {
      email,
      password,
      first_name: firstName,
      last_name: lastName,
    });
    localStorage.setItem("token", res.data.access_token);
    setToken(res.data.access_token);
    console.log(`${LOG} Registration successful`);
    await fetchMe();
  };

  const logout = () => {
    console.log(`${LOG} Logging out`);
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
