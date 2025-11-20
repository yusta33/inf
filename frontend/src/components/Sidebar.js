import { NavLink } from "react-router-dom";
import { Send, BarChart3, MessageCircle, TrendingUp } from "lucide-react";
import UserMenu from "./UserMenu";

const Sidebar = () => {
  const navItems = [
    { path: "/send", icon: Send, label: "📤 Send" },
    { path: "/analyze", icon: BarChart3, label: "📊 Analyze" },
    { path: "/chat", icon: MessageCircle, label: "💬 Chat" },
    { path: "/analytics", icon: TrendingUp, label: "📈 Analytics" },
  ];

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

      <div className="border-t border-[#3A3A3C]">
        <div className="p-4">
          <UserMenu />
        </div>
        <div className="px-4 pb-4 text-xs text-gray-500">
          <p>Emergent.ai CRM v2.0</p>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;