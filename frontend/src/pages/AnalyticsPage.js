import { useState, useEffect } from "react";
import axios from "axios";
import { BarChart3, PieChart, TrendingUp, Users } from "lucide-react";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const AnalyticsPage = () => {
  const [analytics, setAnalytics] = useState(null);

  useEffect(() => {
    loadAnalytics();
  }, []);

  const loadAnalytics = async () => {
    try {
      const res = await axios.get(`${API}/analytics`);
      setAnalytics(res.data);
    } catch (err) {
      toast.error("Failed to load analytics");
    }
  };

  if (!analytics) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-gray-400">Loading analytics...</p>
      </div>
    );
  }

  const sentPercent = analytics.total_contacts > 0
    ? (analytics.sent_count / analytics.total_contacts) * 100
    : 0;

  const totalClassified = analytics.positive_count + analytics.negative_count + analytics.neutral_count;
  const positivePercent = totalClassified > 0 ? (analytics.positive_count / totalClassified) * 100 : 0;
  const negativePercent = totalClassified > 0 ? (analytics.negative_count / totalClassified) * 100 : 0;
  const neutralPercent = totalClassified > 0 ? (analytics.neutral_count / totalClassified) * 100 : 0;

  return (
    <div className="p-6">
      <div className="max-w-7xl mx-auto">
        <h2 className="text-3xl font-bold mb-6">Analytics Dashboard</h2>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-[#2C2C2E] p-6 rounded-lg border border-[#3A3A3C]">
            <div className="flex items-center justify-between mb-3">
              <Users size={24} className="text-[#C13584]" />
              <span className="text-sm text-gray-400">Total</span>
            </div>
            <p className="text-3xl font-bold">{analytics.total_contacts}</p>
            <p className="text-sm text-gray-400 mt-1">Contacts</p>
          </div>

          <div className="bg-[#2C2C2E] p-6 rounded-lg border border-[#3A3A3C]">
            <div className="flex items-center justify-between mb-3">
              <TrendingUp size={24} className="text-green-400" />
              <span className="text-sm text-gray-400">Sent</span>
            </div>
            <p className="text-3xl font-bold">{analytics.sent_count}</p>
            <p className="text-sm text-gray-400 mt-1">{sentPercent.toFixed(1)}% of total</p>
          </div>

          <div className="bg-[#2C2C2E] p-6 rounded-lg border border-[#3A3A3C]">
            <div className="flex items-center justify-between mb-3">
              <BarChart3 size={24} className="text-blue-400" />
              <span className="text-sm text-gray-400">Pending</span>
            </div>
            <p className="text-3xl font-bold">{analytics.pending_count}</p>
            <p className="text-sm text-gray-400 mt-1">Not sent yet</p>
          </div>

          <div className="bg-[#2C2C2E] p-6 rounded-lg border border-[#3A3A3C]">
            <div className="flex items-center justify-between mb-3">
              <PieChart size={24} className="text-yellow-400" />
              <span className="text-sm text-gray-400">Analyzed</span>
            </div>
            <p className="text-3xl font-bold">{totalClassified}</p>
            <p className="text-sm text-gray-400 mt-1">Responses</p>
          </div>
        </div>

        {/* Sentiment Chart */}
        <div className="bg-[#2C2C2E] p-6 rounded-lg border border-[#3A3A3C] mb-8">
          <h3 className="text-xl font-bold mb-6">Response Sentiment</h3>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between mb-2">
                <span className="flex items-center gap-2">
                  <span className="status-positive"></span>
                  Positive
                </span>
                <span className="font-semibold">{analytics.positive_count} ({positivePercent.toFixed(1)}%)</span>
              </div>
              <div className="w-full bg-[#3A3A3C] rounded-full h-3">
                <div
                  className="bg-green-500 h-3 rounded-full transition-all"
                  style={{ width: `${positivePercent}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-2">
                <span className="flex items-center gap-2">
                  <span className="status-neutral"></span>
                  Neutral
                </span>
                <span className="font-semibold">{analytics.neutral_count} ({neutralPercent.toFixed(1)}%)</span>
              </div>
              <div className="w-full bg-[#3A3A3C] rounded-full h-3">
                <div
                  className="bg-gray-400 h-3 rounded-full transition-all"
                  style={{ width: `${neutralPercent}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-2">
                <span className="flex items-center gap-2">
                  <span className="status-negative"></span>
                  Negative
                </span>
                <span className="font-semibold">{analytics.negative_count} ({negativePercent.toFixed(1)}%)</span>
              </div>
              <div className="w-full bg-[#3A3A3C] rounded-full h-3">
                <div
                  className="bg-red-500 h-3 rounded-full transition-all"
                  style={{ width: `${negativePercent}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Categories */}
        <div className="bg-[#2C2C2E] p-6 rounded-lg border border-[#3A3A3C]">
          <h3 className="text-xl font-bold mb-4">Categories Progress</h3>
          <div className="space-y-3">
            {analytics.categories.map((cat) => (
              <div key={cat.id} className="flex items-center justify-between p-3 bg-[#3A3A3C] rounded-lg">
                <span className="font-medium">📂 {cat.name}</span>
                <span className="text-sm text-gray-400">
                  {cat.sent_count}/{cat.total_contacts} sent
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsPage;