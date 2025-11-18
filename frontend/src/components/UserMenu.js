import { useState, useRef, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { LogOut, User, ChevronDown } from "lucide-react";

const UserMenu = () => {
  const { currentUser, logout } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef(null);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  if (!currentUser) return null;

  const getUserDisplay = () => {
    if (currentUser.username) return currentUser.username;
    if (currentUser.email) return currentUser.email.split("@")[0];
    return "User";
  };

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-[#3A3A3C] transition-colors text-left"
      >
        <div className="w-8 h-8 rounded-full gradient-accent flex items-center justify-center text-sm font-semibold">
          {getUserDisplay().charAt(0).toUpperCase()}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">{getUserDisplay()}</p>
          <p className="text-xs text-gray-400 truncate">{currentUser.email}</p>
        </div>
        <ChevronDown
          size={16}
          className={`text-gray-400 transition-transform ${isOpen ? "rotate-180" : ""}`}
        />
      </button>

      {/* Dropdown menu */}
      {isOpen && (
        <div className="absolute bottom-full left-0 right-0 mb-2 bg-[#2C2C2E] border border-[#3A3A3C] rounded-lg shadow-lg overflow-hidden">
          <div className="p-3 border-b border-[#3A3A3C]">
            <p className="text-xs text-gray-400">Signed in as</p>
            <p className="text-sm font-medium mt-1 truncate">{currentUser.email}</p>
            {currentUser.roles && currentUser.roles.length > 0 && (
              <div className="flex gap-1 mt-2">
                {currentUser.roles.map((role) => (
                  <span
                    key={role}
                    className="text-xs px-2 py-1 bg-[#3A3A3C] rounded text-[#C13584]"
                  >
                    {role}
                  </span>
                ))}
              </div>
            )}
          </div>

          <button
            onClick={() => {
              logout();
              setIsOpen(false);
            }}
            className="w-full flex items-center gap-3 px-4 py-3 hover:bg-[#3A3A3C] transition-colors text-left"
          >
            <LogOut size={16} className="text-gray-400" />
            <span className="text-sm">Logout</span>
          </button>
        </div>
      )}
    </div>
  );
};

export default UserMenu;
