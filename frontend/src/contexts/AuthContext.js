import { createContext, useContext, useState, useEffect } from "react";
import axios from "axios";
import { toast } from "sonner";

const AuthContext = createContext(null);

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const AuthProvider = ({ children }) => {
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem("access_token"));

  // Initialize - check if we have a token and fetch user
  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem("access_token");

      if (storedToken) {
        try {
          // Configure axios default headers
          axios.defaults.headers.common["Authorization"] = `Bearer ${storedToken}`;

          // Fetch current user
          const response = await axios.get(`${API}/auth/me`);
          setCurrentUser(response.data);
          setToken(storedToken);
        } catch (error) {
          console.error("Failed to fetch user:", error);
          // Token might be expired or invalid
          localStorage.removeItem("access_token");
          delete axios.defaults.headers.common["Authorization"];
          setCurrentUser(null);
          setToken(null);
        }
      }

      setLoading(false);
    };

    initAuth();
  }, []);

  const login = async (email, password) => {
    try {
      // Login request
      const response = await axios.post(`${API}/auth/login`, {
        email,
        password,
      });

      const { access_token } = response.data;

      // Store token
      localStorage.setItem("access_token", access_token);
      setToken(access_token);

      // Configure axios
      axios.defaults.headers.common["Authorization"] = `Bearer ${access_token}`;

      // Fetch user data
      const userResponse = await axios.get(`${API}/auth/me`);
      setCurrentUser(userResponse.data);

      toast.success("Login successful!");
      return true;
    } catch (error) {
      console.error("Login failed:", error);
      const message =
        error.response?.data?.detail || error.response?.data?.error || "Login failed";
      toast.error(message);
      return false;
    }
  };

  const register = async (email, password, confirmPassword, username) => {
    try {
      const response = await axios.post(`${API}/auth/register`, {
        email,
        password,
        confirm_password: confirmPassword,
        username,
      });

      toast.success("Registration successful! Please login.");
      return true;
    } catch (error) {
      console.error("Registration failed:", error);
      const message =
        error.response?.data?.detail || error.response?.data?.error || "Registration failed";
      toast.error(message);
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    delete axios.defaults.headers.common["Authorization"];
    setCurrentUser(null);
    setToken(null);
    toast.info("Logged out successfully");
  };

  const value = {
    currentUser,
    token,
    loading,
    isAuthenticated: !!currentUser,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
