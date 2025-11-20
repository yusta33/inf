import { NavLink, useNavigate } from "react-router-dom";
import { LayoutDashboard, Send, BarChart3, MessageCircle, TrendingUp, LogOut, User } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";

const Sidebar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const navItems = [
    { path: "/dashboard", icon: LayoutDashboard, label: "🏠 Dashboard" },
    { path: "/send", icon: Send, label: "📤 Send" },
    { path: "/analyze", icon: BarChart3, label: "📊 Analyze" },
    { path: "/chat", icon: MessageCircle, label: "💬 Chat" },
    { path: "/analytics", icon: TrendingUp, label: "📈 Analytics" },
  ];

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <aside className="w-64 bg-[#2C2C2E] border-r border-[#3A3A3C] flex flex-col">
      <div className="p-6 border-b border-[#3A3A3C]">
        <h1 className="text-2xl font-bold gradient-text">InboxHub</h1>
        <p className="text-sm text-gray-400 mt-1">Multi-Platform CRM</p>
      </div>

      <nav className="flex-1 p-4">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            data-testid={`nav-${item.path.slice(1)}`}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg mb-2 transition-colors ${
                isActive
                  ? "gradient-accent text-white"
                  : "text-gray-300 hover:bg-[#3A3A3C]"
              }`
            }
          >
            <item.icon size={20} />
            <span className="font-medium">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-[#3A3A3C] space-y-3">
        {user && (
          <div className="flex items-center gap-2 px-3 py-2 bg-[#3A3A3C] rounded-lg">
            <User size={16} className="text-gray-400" />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-[#EAEAEA] truncate">{user.full_name || user.email}</p>
              <p className="text-xs text-gray-500 truncate">{user.email}</p>
            </div>
          </div>
        )}

        <Button
          onClick={handleLogout}
          variant="ghost"
          className="w-full justify-start text-gray-300 hover:bg-[#3A3A3C] hover:text-white"
        >
          <LogOut size={16} className="mr-2" />
          Logout
        </Button>

        <div className="text-xs text-gray-500 pt-2">
          <p>Emergent.ai CRM v1.0</p>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;