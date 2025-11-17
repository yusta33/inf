import { useState, useEffect } from "react";
import axios from "axios";
import { Send as SendIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { ScrollArea } from "@/components/ui/scroll-area";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ChatPage = () => {
  const [conversations, setConversations] = useState([]);
  const [selectedContact, setSelectedContact] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState("");
  const [sending, setSending] = useState(false);

  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    try {
      const res = await axios.get(`${API}/conversations`);
      setConversations(res.data);
    } catch (err) {
      toast.error("Failed to load conversations");
    }
  };

  const loadConversation = async (contactId) => {
    try {
      const res = await axios.get(`${API}/conversations/${contactId}`);
      setSelectedContact(res.data.contact);
      setMessages(res.data.messages);
    } catch (err) {
      toast.error("Failed to load conversation");
    }
  };

  const sendMessage = async () => {
    if (!newMessage.trim() || !selectedContact) return;

    setSending(true);
    try {
      await axios.post(`${API}/conversations/${selectedContact.id}/message`, {
        contact_id: selectedContact.id,
        message: newMessage,
      });

      setNewMessage("");
      loadConversation(selectedContact.id);
      toast.success("Message sent");
    } catch (err) {
      toast.error("Failed to send message");
    } finally {
      setSending(false);
    }
  };

  const highlightPhone = (text) => {
    const phoneRegex = /\b\d{10,}\b/g;
    if (!phoneRegex.test(text)) return text;

    return text.split(phoneRegex).reduce((acc, part, i, arr) => {
      if (i === arr.length - 1) return acc + part;
      const match = text.match(phoneRegex)[i];
      return acc + part + `<span class="phone-highlight">${match}</span>`;
    }, "");
  };

  return (
    <div className="flex h-full">
      {/* Left - User List */}
      <div className="w-80 bg-[#2C2C2E] border-r border-[#3A3A3C] p-4 overflow-auto">
        <h3 className="text-xl font-bold mb-4">Active Leads</h3>
        <div className="space-y-2">
          {conversations.length === 0 ? (
            <p className="text-gray-400 text-sm">No conversations yet</p>
          ) : (
            conversations.map((contact) => (
              <button
                key={contact.id}
                onClick={() => loadConversation(contact.id)}
                data-testid={`conversation-${contact.username}`}
                className={`w-full text-left p-3 rounded-lg transition-colors ${
                  selectedContact?.id === contact.id
                    ? "gradient-accent text-white"
                    : "bg-[#3A3A3C] hover:bg-[#48484A]"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold">@{contact.username}</span>
                  <span className={`text-xs status-${contact.classification}`}></span>
                </div>
                <p className="text-xs text-gray-300 truncate">
                  {contact.last_message || "No messages"}
                </p>
                {contact.interest_score !== null && contact.interest_score !== undefined && (
                  <p className="text-xs mt-1">⭐ {contact.interest_score}%</p>
                )}
              </button>
            ))
          )}
        </div>
      </div>

      {/* Center - Chat */}
      <div className="flex-1 flex flex-col">
        {!selectedContact ? (
          <div className="flex-1 flex items-center justify-center text-gray-400">
            <p>Select a conversation to start chatting</p>
          </div>
        ) : (
          <>
            {/* Chat Header */}
            <div className="bg-[#2C2C2E] border-b border-[#3A3A3C] p-4">
              <h3 className="text-xl font-bold">@{selectedContact.username}</h3>
              <p className="text-sm text-gray-400">
                {selectedContact.platform === "instagram" ? "📱 Instagram" : "📧 Email"}
              </p>
            </div>

            {/* Messages */}
            <ScrollArea className="flex-1 p-4" data-testid="chat-messages">
              <div className="space-y-4">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${msg.direction === "outbound" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`chat-bubble ${
                        msg.direction === "outbound" ? "chat-bubble-admin" : "chat-bubble-user"
                      }`}
                      dangerouslySetInnerHTML={{ __html: highlightPhone(msg.content) }}
                    />
                  </div>
                ))}
              </div>
            </ScrollArea>

            {/* Input */}
            <div className="bg-[#2C2C2E] border-t border-[#3A3A3C] p-4">
              <div className="flex gap-3">
                <input
                  type="text"
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && sendMessage()}
                  placeholder="Type your message..."
                  data-testid="chat-input"
                  className="flex-1"
                />
                <Button
                  onClick={sendMessage}
                  disabled={sending || !newMessage.trim()}
                  data-testid="chat-send-btn"
                  className="gradient-accent text-white px-6"
                >
                  <SendIcon size={18} />
                </Button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Right - User Card */}
      {selectedContact && (
        <div className="w-80 bg-[#2C2C2E] border-l border-[#3A3A3C] p-6">
          <div className="text-center mb-6">
            <div className="w-20 h-20 rounded-full gradient-accent mx-auto mb-4 flex items-center justify-center text-3xl">
              👤
            </div>
            <h3 className="text-xl font-bold">@{selectedContact.username}</h3>
            <p className="text-sm text-gray-400 mt-1">
              {selectedContact.platform === "instagram" ? "📱 Instagram" : "📧 Email"}
            </p>
          </div>

          <div className="space-y-4">
            <div className="bg-[#3A3A3C] p-4 rounded-lg">
              <p className="text-sm text-gray-400 mb-1">💬 Last Message</p>
              <p className="text-sm">{selectedContact.last_message || "-"}</p>
            </div>

            <div className="bg-[#3A3A3C] p-4 rounded-lg">
              <p className="text-sm text-gray-400 mb-1">⭐ Interest Level</p>
              <p className="text-2xl font-bold">
                {selectedContact.interest_score !== null && selectedContact.interest_score !== undefined
                  ? `${selectedContact.interest_score}%`
                  : "-"}
              </p>
            </div>

            <div className="bg-[#3A3A3C] p-4 rounded-lg">
              <p className="text-sm text-gray-400 mb-1">📅 Last Contact</p>
              <p className="text-sm">
                {selectedContact.sent_at
                  ? new Date(selectedContact.sent_at).toLocaleDateString()
                  : "-"}
              </p>
            </div>

            {selectedContact.classification && (
              <div className="bg-[#3A3A3C] p-4 rounded-lg">
                <p className="text-sm text-gray-400 mb-1">🏷️ Status</p>
                <p className="text-sm capitalize">
                  <span className={`status-${selectedContact.classification}`}></span>{" "}
                  {selectedContact.classification}
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatPage;