import { useState, useEffect } from "react";
import axios from "axios";
import { Search, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const AnalyzePage = () => {
  const [contacts, setContacts] = useState([]);
  const [filterStatus, setFilterStatus] = useState("all");
  const [analyzing, setAnalyzing] = useState(null);

  useEffect(() => {
    loadContacts();
  }, []);

  const loadContacts = async () => {
    try {
      const res = await axios.get(`${API}/categories`);
      const allContacts = res.data.flatMap((cat) => 
        cat.contacts.map(c => ({ ...c, category: cat.name }))
      );
      setContacts(allContacts.filter(c => c.status === "sent"));
    } catch (err) {
      toast.error("Failed to load contacts");
    }
  };

  const analyzeMessage = async (contact) => {
    if (!contact.last_message) {
      toast.error("No message to analyze");
      return;
    }

    setAnalyzing(contact.id);
    try {
      const res = await axios.post(`${API}/messages/analyze`, {
        contact_id: contact.id,
        message: contact.last_message,
      });

      toast.success(`Classified as ${res.data.classification} (${res.data.score}/100)`);
      loadContacts();
    } catch (err) {
      toast.error("Analysis failed: " + (err.response?.data?.detail || err.message));
    } finally {
      setAnalyzing(null);
    }
  };

  const exportToExcel = () => {
    toast.info("Export functionality coming soon");
  };

  const filteredContacts = contacts.filter((c) => {
    if (filterStatus !== "all" && c.classification !== filterStatus) return false;
    return true;
  });

  return (
    <div className="p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-3xl font-bold">Response Analysis</h2>
          <Button
            onClick={exportToExcel}
            data-testid="export-excel-btn"
            className="gradient-accent text-white"
          >
            <Download size={18} className="mr-2" />
            Export to Excel
          </Button>
        </div>

        {/* Filters */}
        <div className="flex gap-4 mb-6">
          <div className="flex-1">
            <label className="block text-sm font-medium mb-2">Filter by Status</label>
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger data-testid="filter-status" className="w-full bg-[#2C2C2E] border-[#3A3A3C]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#2C2C2E] border-[#3A3A3C]">
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="positive">✅ Positive</SelectItem>
                <SelectItem value="negative">❌ Negative</SelectItem>
                <SelectItem value="neutral">⚪ Neutral</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex-1">
            <label className="block text-sm font-medium mb-2">Platform</label>
            <div className="px-4 py-3 bg-[#2C2C2E] border border-[#3A3A3C] rounded-lg">
              <span className="font-medium text-[#C13584]">📱 Instagram Only</span>
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="bg-[#2C2C2E] rounded-lg border border-[#3A3A3C] overflow-hidden">
          <table className="w-full">
            <thead className="bg-[#3A3A3C]">
              <tr>
                <th className="px-4 py-3 text-left font-semibold">Instagram User</th>
                <th className="px-4 py-3 text-left font-semibold">Message</th>
                <th className="px-4 py-3 text-left font-semibold">Classification</th>
                <th className="px-4 py-3 text-left font-semibold">Interest Score</th>
                <th className="px-4 py-3 text-left font-semibold">Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredContacts.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-400">
                    No responses to analyze yet
                  </td>
                </tr>
              ) : (
                filteredContacts.map((contact) => (
                  <tr
                    key={contact.id}
                    data-testid={`contact-row-${contact.username}`}
                    className="border-t border-[#3A3A3C] hover:bg-[#3A3A3C] transition-colors"
                  >
                    <td className="px-4 py-3">@{contact.username}</td>
                    <td className="px-4 py-3 max-w-xs truncate" title={contact.last_message}>
                      {contact.last_message || "-"}
                    </td>
                    <td className="px-4 py-3">
                      {contact.classification ? (
                        <span className={`status-${contact.classification}`}>
                          {" "}{contact.classification}
                        </span>
                      ) : (
                        <span className="text-gray-500">Not analyzed</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {contact.interest_score !== null && contact.interest_score !== undefined ? (
                        <span className="font-semibold">{contact.interest_score}/100</span>
                      ) : (
                        "-"
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <Button
                        onClick={() => analyzeMessage(contact)}
                        disabled={analyzing === contact.id || !contact.last_message}
                        data-testid={`analyze-btn-${contact.username}`}
                        size="sm"
                        className="bg-[#C13584] hover:bg-[#E1306C] text-white"
                      >
                        {analyzing === contact.id ? (
                          <>Analyzing...</>
                        ) : (
                          <>
                            <Search size={14} className="mr-1" />
                            Analyze
                          </>
                        )}
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default AnalyzePage;