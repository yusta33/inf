import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { LogIn, UserPlus } from "lucide-react";

const LoginPage = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [username, setUsername] = useState("");
  const [loading, setLoading] = useState(false);

  const { login, register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    let success = false;

    if (isLogin) {
      success = await login(email, password);
      if (success) {
        navigate("/send");
      }
    } else {
      success = await register(email, password, confirmPassword, username);
      if (success) {
        // After successful registration, switch to login mode
        setIsLogin(true);
        setPassword("");
        setConfirmPassword("");
      }
    }

    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-[#1C1C1E] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo/Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold gradient-text mb-2">InboxHub</h1>
          <p className="text-gray-400">Instagram CRM Platform</p>
        </div>

        {/* Login/Register Card */}
        <div className="bg-[#2C2C2E] rounded-lg border border-[#3A3A3C] p-8">
          <div className="flex gap-2 mb-6">
            <button
              onClick={() => setIsLogin(true)}
              className={`flex-1 py-2 rounded-lg font-medium transition-colors ${
                isLogin
                  ? "gradient-accent text-white"
                  : "bg-[#3A3A3C] text-gray-300 hover:bg-[#48484A]"
              }`}
            >
              Login
            </button>
            <button
              onClick={() => setIsLogin(false)}
              className={`flex-1 py-2 rounded-lg font-medium transition-colors ${
                !isLogin
                  ? "gradient-accent text-white"
                  : "bg-[#3A3A3C] text-gray-300 hover:bg-[#48484A]"
              }`}
            >
              Register
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {!isLogin && (
              <div>
                <label className="block text-sm font-medium mb-2">Username (optional)</label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="johndoe"
                  className="w-full px-4 py-2 bg-[#1C1C1E] border border-[#3A3A3C] rounded-lg focus:outline-none focus:border-[#C13584] transition-colors"
                />
              </div>
            )}

            <div>
              <label className="block text-sm font-medium mb-2">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="you@example.com"
                className="w-full px-4 py-2 bg-[#1C1C1E] border border-[#3A3A3C] rounded-lg focus:outline-none focus:border-[#C13584] transition-colors"
                autoComplete="email"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="••••••••"
                className="w-full px-4 py-2 bg-[#1C1C1E] border border-[#3A3A3C] rounded-lg focus:outline-none focus:border-[#C13584] transition-colors"
                autoComplete={isLogin ? "current-password" : "new-password"}
              />
            </div>

            {!isLogin && (
              <div>
                <label className="block text-sm font-medium mb-2">Confirm Password</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  placeholder="••••••••"
                  className="w-full px-4 py-2 bg-[#1C1C1E] border border-[#3A3A3C] rounded-lg focus:outline-none focus:border-[#C13584] transition-colors"
                  autoComplete="new-password"
                />
              </div>
            )}

            {!isLogin && (
              <div className="bg-[#3A3A3C] p-3 rounded-lg text-xs text-gray-400">
                Password must:
                <ul className="list-disc list-inside mt-1 space-y-1">
                  <li>Be at least 8 characters long</li>
                  <li>Contain uppercase and lowercase letters</li>
                  <li>Contain at least one number</li>
                </ul>
              </div>
            )}

            <Button
              type="submit"
              disabled={loading}
              className="w-full gradient-accent text-white py-3 text-base font-semibold"
            >
              {loading ? (
                "Please wait..."
              ) : isLogin ? (
                <>
                  <LogIn size={18} className="mr-2" />
                  Login
                </>
              ) : (
                <>
                  <UserPlus size={18} className="mr-2" />
                  Create Account
                </>
              )}
            </Button>
          </form>

          <div className="mt-6 text-center text-sm text-gray-400">
            {isLogin ? (
              <>
                Don't have an account?{" "}
                <button
                  onClick={() => setIsLogin(false)}
                  className="text-[#C13584] hover:text-[#E1306C] font-medium"
                >
                  Register here
                </button>
              </>
            ) : (
              <>
                Already have an account?{" "}
                <button
                  onClick={() => setIsLogin(true)}
                  className="text-[#C13584] hover:text-[#E1306C] font-medium"
                >
                  Login here
                </button>
              </>
            )}
          </div>
        </div>

        {/* Note about security */}
        <div className="mt-6 text-center text-xs text-gray-500">
          <p>
            🔒 Secure authentication with JWT tokens
            <br />
            Note: For production, consider using HttpOnly cookies
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
