import { useState, useEffect } from "react";
import axiosClient from "./api/axiosClient";
import SearchForm from "./components/SearchForm";
import DataTable from "./components/DataTable";
import Dashboard from "./components/Dashboard";
import ChatAgent from "./components/ChatAgent";

export default function App() {
  const [showSearchForm, setShowSearchForm] = useState(false);
  const [showDashboard, setShowDashboard] = useState(false);
  const [businesses, setBusinesses] = useState([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [taskId, setTaskId] = useState(null);
  const [progress, setProgress] = useState(0);
  const [loadingMessage, setLoadingMessage] = useState("");

  const handleChatResponse = (status, data) => {
    if (status === "need_more_data") {
      setShowSearchForm(true);
      setShowDashboard(false);
      return;
    }

    if (status === "success_enough_data") {
      setBusinesses(Array.isArray(data) ? data : []);
      setShowDashboard(true);
      setShowSearchForm(false);
    }
  };

  const handleSearchComplete = (data) => {
    setBusinesses(Array.isArray(data) ? data : []);
    setShowDashboard(true);
    setShowSearchForm(false);
  };

  useEffect(() => {
    let intervalId;
    if (taskId) {
      intervalId = setInterval(async () => {
        try {
          const { data } = await axiosClient.get(`/api/tasks/${taskId}`);
          setProgress(data.progress || 0);
          setLoadingMessage(data.message || "");

          if (data.status === "completed") {
            handleSearchComplete(data.data?.businesses || []);
            setLoading(false);
            setTaskId(null);
          } else if (data.status === "failed") {
            setError(data.message || "Pipeline failed");
            setLoading(false);
            setTaskId(null);
          }
        } catch (err) {
          setError(err.message);
          setLoading(false);
          setTaskId(null);
        }
      }, 1500);
    }
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [taskId]);

  const handleSearchRequest = async ({ keyword, location, min_rating, result_limit }) => {
    setLoading(true);
    setError(null);
    setProgress(0);
    setLoadingMessage("Khởi tạo task...");

    try {
      const payload = { keyword, location };
      if (min_rating !== undefined) payload.min_rating = min_rating;
      if (result_limit !== undefined) payload.result_limit = result_limit;

      const { data } = await axiosClient.post("/api/search", payload);
      setTaskId(data.task_id);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen" style={{ background: "#0D0F1A" }}>
      <div aria-hidden className="pointer-events-none fixed inset-0 overflow-hidden">
        <div
          className="absolute -top-40 left-1/2 -translate-x-1/2 w-[700px] h-[400px] rounded-full opacity-10 blur-3xl"
          style={{ background: "radial-gradient(ellipse, #00FF94 0%, transparent 70%)" }}
        />
        <div
          className="absolute bottom-0 right-0 w-[400px] h-[400px] rounded-full opacity-5 blur-3xl"
          style={{ background: "radial-gradient(ellipse, #818CF8 0%, transparent 70%)" }}
        />
      </div>

      <div className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6 py-14">
        <header className="mb-10 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-pulse/30 bg-pulse/10">
            <span className="w-2 h-2 rounded-full bg-pulse animate-pulse-dot" />
            <span className="font-mono text-xs text-pulse tracking-[0.3em] uppercase font-semibold">
              AI-FIRST LEAD GENERATION
            </span>
          </div>
          <h1 className="mt-6 text-5xl font-display font-extrabold tracking-tight text-white">
            LeadSpy<span className="text-pulse">AI</span>
          </h1>
          <p className="mt-3 text-sm text-dim font-body max-w-xl mx-auto">
            Dat cau hoi truoc, AI se dieu huong ban lay du lieu va dua ra thong ke nhanh.
          </p>
        </header>

        <ChatAgent onChatResponse={handleChatResponse} />

        {showSearchForm && (
          <div className="mt-10 animate-fade-up" style={{ animationDelay: "0.05s", opacity: 0 }}>
            <SearchForm onSearchComplete={handleSearchRequest} loading={loading} />

            {loading && (
              <div className="mt-10 max-w-xl mx-auto flex flex-col items-center gap-4 text-dim">
                <div className="w-full bg-card rounded-full h-4 border border-border overflow-hidden relative shadow-inner">
                  <div
                    className="h-full transition-all duration-500 ease-out bg-[#00FF94]"
                    style={{
                      width: `${progress}%`,
                      boxShadow: "0 0 15px #00FF94, 0 0 30px #00FF94",
                    }}
                  />
                </div>
                <p className="font-mono text-xs tracking-widest uppercase text-[#00FF94] animate-pulse">
                  {loadingMessage || "Dang xu ly..."} ({progress}%)
                </p>
              </div>
            )}

            {error && !loading && (
              <div className="mt-6 max-w-xl mx-auto rounded-lg border border-red-500/30 bg-red-500/10 px-5 py-4">
                <p className="font-mono text-xs text-red-400 uppercase tracking-wider mb-1">Loi</p>
                <p className="font-body text-sm text-red-300">{error}</p>
              </div>
            )}
          </div>
        )}

        {showDashboard && (
          <div className="mt-12 animate-fade-up" style={{ animationDelay: "0.08s", opacity: 0 }}>
            <Dashboard data={businesses} />
            <DataTable data={businesses} />
          </div>
        )}
      </div>
    </div>
  );
}