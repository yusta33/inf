import { useState } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "@/components/Sidebar";
import SendPage from "@/pages/SendPage";
import AnalyzePage from "@/pages/AnalyzePage";
import ChatPage from "@/pages/ChatPage";
import AnalyticsPage from "@/pages/AnalyticsPage";
import { Toaster } from "@/components/ui/sonner";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <div className="flex h-screen bg-[#1C1C1E] text-[#EAEAEA]">
          <Sidebar />
          <main className="flex-1 overflow-auto">
            <Routes>
              <Route path="/" element={<Navigate to="/send" replace />} />
              <Route path="/send" element={<SendPage />} />
              <Route path="/analyze" element={<AnalyzePage />} />
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/analytics" element={<AnalyticsPage />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
      <Toaster position="top-right" />
    </div>
  );
}

export default App;