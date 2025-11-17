import { useState, useEffect } from "react";
import axios from "axios";
import { Upload, Send as SendIcon, RefreshCw, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { ChevronRight } from "lucide-react";
import ResetStatusModal from "@/components/ResetStatusModal";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const SendPage = () => {
  const [categories, setCategories] = useState([]);
  const [selectedContacts, setSelectedContacts] = useState([]);
  const [message, setMessage] = useState("");
  const [instaUsername, setInstaUsername] = useState("");
  const [instaPassword, setInstaPassword] = useState("");
  const [sending, setSending] = useState(false);
  const [openCategories, setOpenCategories] = useState([]);
  const [showResetModal, setShowResetModal] = useState(false);

  useEffect(() => {
    loadCategories();
  }, []);

  const loadCategories = async () => {
    try {
      const res = await axios.get(`${API}/categories`);
      setCategories(res.data);
    } catch (err) {
      toast.error("Failed to load categories");
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      toast.loading("Importing contacts...");
      await axios.post(`${API}/excel/import`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success("Contacts imported successfully!");
      loadCategories();
    } catch (err) {
      toast.error("Import failed: " + (err.response?.data?.detail || err.message));
    }
  };

  const toggleContact = (contactId) => {
    setSelectedContacts((prev) =>
      prev.includes(contactId)
        ? prev.filter((id) => id !== contactId)
        : [...prev, contactId]
    );
  };

  const selectUnsent = () => {
    const unsent = [];
    categories.forEach((cat) => {
      cat.contacts.forEach((c) => {
        if (c.status === "pending") unsent.push(c.id);
      });
    });
    setSelectedContacts(unsent);
    toast.success(`Selected ${unsent.length} unsent contacts`);
  };

  const handleResetStatus = async (scope) => {
    try {
      toast.loading("Resetting status...");
      
      const payload = {
        scope,
        category_id: scope === "category" ? currentCategory?.id : undefined,
        contact_ids: scope === "selected" ? selectedContacts : undefined,
      };

      const res = await axios.post(`${API}/contacts/reset-status`, payload);
      
      // Clear selections
      setSelectedContacts([]);
      
      // Reload categories to refresh UI
      await loadCategories();
      
      toast.dismiss();
      toast.success(res.data.message || "Statuses reset successfully");
    } catch (err) {
      toast.dismiss();
      toast.error("Failed to reset status: " + (err.response?.data?.detail || err.message));
    }
  };

  const openResetModal = () => {
    setShowResetModal(true);
  };

  const sendMessages = async () => {
    if (selectedContacts.length === 0) {
      toast.error("Please select contacts");
      return;
    }
    if (!message.trim()) {
      toast.error("Please enter a message");
      return;
    }
    if (!instaUsername || !instaPassword) {
      toast.error("Please enter Instagram credentials");
      return;
    }

    setSending(true);
    try {
      const res = await axios.post(`${API}/messages/send`, {
        contact_ids: selectedContacts,
        platform: "instagram",
        message,
        instagram_username: instaUsername,
        instagram_password: instaPassword,
      });

      const successful = res.data.results.filter((r) => r.status === "success" || r.status === "queued").length;
      toast.success(`Queued ${successful}/${selectedContacts.length} messages`);
      setSelectedContacts([]);
      loadCategories();
    } catch (err) {
      toast.error("Failed to send messages: " + (err.response?.data?.error || err.message));
    } finally {
      setSending(false);
    }
  };

  const toggleCategory = (catId) => {
    setOpenCategories(prev => 
      prev.includes(catId) ? prev.filter(id => id !== catId) : [...prev, catId]
    );
  };

  const totalSent = categories.reduce((sum, cat) => sum + cat.sent_count, 0);
  const totalContacts = categories.reduce((sum, cat) => sum + cat.total_contacts, 0);

  return (
    <div className="flex h-full">
      {/* Left Panel - Categories */}
      <div className="w-80 bg-[#2C2C2E] border-r border-[#3A3A3C] p-4 overflow-auto">
        <div className="mb-4">
          <label
            htmlFor="file-upload"
            className="flex items-center gap-2 px-4 py-2 gradient-accent text-white rounded-lg cursor-pointer justify-center"
            data-testid="upload-excel-btn"
          >
            <Upload size={18} />
            <span>Import Excel</span>
          </label>
          <input
            id="file-upload"
            type="file"
            accept=".xlsx,.xls"
            onChange={handleFileUpload}
            className="hidden"
          />
        </div>

        <div className="space-y-2">
          {categories.map((cat) => (
            <div key={cat.id} className="bg-[#3A3A3C] rounded-lg">
              <button
                onClick={() => toggleCategory(cat.id)}
                className="w-full flex items-center justify-between p-3 hover:bg-[#48484A] rounded-lg transition-colors"
                data-testid={`category-${cat.name}`}
              >
                <div className="flex items-center gap-2">
                  <ChevronRight 
                    size={16} 
                    className={`transition-transform ${openCategories.includes(cat.id) ? 'rotate-90' : ''}`}
                  />
                  <span className="font-medium">📂 {cat.name}</span>
                </div>
                <span className="text-sm text-gray-400">
                  {cat.sent_count}/{cat.total_contacts}
                </span>
              </button>

              {openCategories.includes(cat.id) && (
                <div className="px-3 pb-3 space-y-1">
                  {cat.contacts?.map((contact) => (
                    <label
                      key={contact.id}
                      className="flex items-center gap-2 p-2 hover:bg-[#48484A] rounded cursor-pointer"
                      data-testid={`contact-${contact.username}`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedContacts.includes(contact.id)}
                        onChange={() => toggleContact(contact.id)}
                        className="w-4 h-4"
                      />
                      <span className={`status-${contact.status} mr-1`}></span>
                      <span className="text-sm">@{contact.username}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Right Panel - Message Composer */}
      <div className="flex-1 p-6 overflow-auto">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold mb-6">📱 Instagram Bulk Messaging</h2>

          {/* Controls */}
          <div className="flex gap-3 mb-6">
            <Button
              onClick={selectUnsent}
              variant="outline"
              data-testid="select-unsent-btn"
              className="border-gray-600 hover:bg-[#3A3A3C]"
            >
              <Filter size={16} className="mr-2" />
              Select Unsent
            </Button>
            <Button
              onClick={openResetModal}
              variant="outline"
              data-testid="reset-status-btn"
              className="border-gray-600 hover:bg-[#3A3A3C]"
            >
              <RefreshCw size={16} className="mr-2" />
              Reset Status
            </Button>
          </div>

          {/* Instagram Credentials */}
          <div className="bg-[#2C2C2E] p-4 rounded-lg mb-4 border border-[#3A3A3C]">
            <h3 className="text-sm font-semibold mb-3 text-[#C13584]">Instagram Credentials</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Username</label>
                <input
                  type="text"
                  value={instaUsername}
                  onChange={(e) => setInstaUsername(e.target.value)}
                  data-testid="instagram-username"
                  placeholder="your_username"
                  className="w-full"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Password</label>
                <input
                  type="password"
                  value={instaPassword}
                  onChange={(e) => setInstaPassword(e.target.value)}
                  data-testid="instagram-password"
                  placeholder="••••••••"
                  className="w-full"
                />
              </div>
            </div>
          </div>

          {/* Message */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Direct Message</label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              data-testid="message-body"
              placeholder="Type your Instagram DM here..."
              rows={10}
              className="w-full resize-none"
            />
          </div>

          {/* Progress */}
          <div className="mb-4 p-4 bg-[#3A3A3C] rounded-lg">
            <div className="flex justify-between text-sm mb-2">
              <span>Progress</span>
              <span className="font-semibold">
                {totalSent}/{totalContacts} sent
              </span>
            </div>
            <div className="w-full bg-[#2C2C2E] rounded-full h-2">
              <div
                className="gradient-accent h-2 rounded-full transition-all"
                style={{ width: `${totalContacts > 0 ? (totalSent / totalContacts) * 100 : 0}%` }}
              />
            </div>
          </div>

          {/* Send Button */}
          <Button
            onClick={sendMessages}
            disabled={sending || selectedContacts.length === 0}
            data-testid="send-messages-btn"
            className="w-full gradient-accent text-white py-4 text-lg font-semibold"
          >
            {sending ? (
              <>Sending...</>
            ) : (
              <>
                <SendIcon size={20} className="mr-2" />
                Send to {selectedContacts.length} contact(s)
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Reset Status Modal */}
      <ResetStatusModal
        open={showResetModal}
        onClose={() => setShowResetModal(false)}
        onConfirm={handleResetStatus}
        selectedCount={selectedContacts.length}
        currentCategory={null}
      />
    </div>
  );
};

export default SendPage;