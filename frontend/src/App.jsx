import { useState, useEffect } from "react";
import axiosClient from "./api/axiosClient";
import SearchForm  from "./components/SearchForm";
import DataTable   from "./components/DataTable";
import Dashboard   from "./components/Dashboard";

import AIInsights  from "./components/AIInsights";

export default function App() {
  const [businesses, setBusinesses] = useState([]);
  const [insights,   setInsights]   = useState([]);
  const [loading,    setLoading]    = useState(false);
  const [error,      setError]      = useState(null);
  const [searched,   setSearched]   = useState(false);
  const [query,      setQuery]      = useState(null);
  const [exportFormat, setExportFormat] = useState("csv");
  
  const [taskId, setTaskId] = useState(null);
  const [progress, setProgress] = useState(0);
  const [loadingMessage, setLoadingMessage] = useState("");

  useEffect(() => {
    let intervalId;
    if (taskId) {
      intervalId = setInterval(async () => {
        try {
          const { data } = await axiosClient.get(`/api/tasks/${taskId}`);
          setProgress(data.progress || 0);
          setLoadingMessage(data.message || "");
          
          if (data.status === "completed") {
            setBusinesses(data.data?.businesses || []);
            setInsights(data.data?.insights || []);
            setLoading(false);
            setTaskId(null); // Stop polling
          } else if (data.status === "failed") {
            setError(data.message || "Pipeline failed");
            setLoading(false);
            setTaskId(null); // Stop polling
          }
        } catch (err) {
          setError(err.message);
          setLoading(false);
          setTaskId(null); // Stop polling
        }
      }, 1500);
    }
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [taskId]);

  const handleSearch = async ({ keyword, location, min_rating, result_limit }) => {
    setLoading(true);
    setError(null);
    setBusinesses([]);
    setInsights([]);
    setQuery({ keyword, location, min_rating, result_limit });
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
    } finally {
      setSearched(true);
    }
  };

  return (
    <div className="min-h-screen" style={{ background: "#0D0F1A" }}>
      {/* Ambient background glow */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 overflow-hidden"
      >
        <div
          className="absolute -top-40 left-1/2 -translate-x-1/2 w-[700px] h-[400px] rounded-full opacity-10 blur-3xl"
          style={{ background: "radial-gradient(ellipse, #00FF94 0%, transparent 70%)" }}
        />
        <div
          className="absolute bottom-0 right-0 w-[400px] h-[400px] rounded-full opacity-5 blur-3xl"
          style={{ background: "radial-gradient(ellipse, #818CF8 0%, transparent 70%)" }}
        />
      </div>

      {/* Content */}
      <div className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6 py-16">

        <SearchForm onSearch={handleSearch} loading={loading} />

        {/* Loading state */}
        {loading && (
          <div className="mt-16 max-w-xl mx-auto flex flex-col items-center gap-4 text-dim">
            <div className="w-full bg-card rounded-full h-4 border border-border overflow-hidden relative shadow-inner">
              <div 
                className="h-full transition-all duration-500 ease-out bg-[#00FF94]" 
                style={{ 
                  width: `${progress}%`, 
                  boxShadow: "0 0 15px #00FF94, 0 0 30px #00FF94" 
                }}
              />
            </div>
            <p className="font-mono text-xs tracking-widest uppercase text-[#00FF94] animate-pulse">
              {loadingMessage || "Đang xử lý..."} ({progress}%)
            </p>
          </div>
        )}

        {/* Error state */}
        {error && !loading && (
          <div className="mt-8 max-w-xl mx-auto rounded-lg border border-red-500/30 bg-red-500/10 px-5 py-4">
            <p className="font-mono text-xs text-red-400 uppercase tracking-wider mb-1">
              Lỗi
            </p>
            <p className="font-body text-sm text-red-300">{error}</p>
          </div>
        )}

        {/* Empty state */}
        {searched && !loading && !error && businesses.length === 0 && (
          <div className="mt-16 text-center">
            <p className="font-display text-2xl text-white/20 font-bold">
              Không tìm thấy kết quả
            </p>
            <p className="font-body text-sm text-dim mt-2">
              Hãy thử từ khóa hoặc khu vực khác.
            </p>
          </div>
        )}

        {/* Results */}
        {!loading && businesses.length > 0 && (
          <>
            {/* Query context & Export */}
            <div className="mt-8 flex items-center justify-between">
              <div className="flex items-center gap-2 font-mono text-xs text-dim">
                <span className="text-pulse">◆</span>
                Hiển thị{" "}
                <span className="text-white">{businesses.length} doanh nghiệp</span>
                {" "}cho{" "}
                <span className="text-white">"{query?.keyword}"</span>
                {" "}tại{" "}
                <span className="text-white">"{query?.location}"</span>
                {query?.min_rating != null && (
                  <>
                    {" "}- lọc &gt; <span className="text-white">{query.min_rating}</span> sao
                  </>
                )}
                {query?.result_limit != null && (
                  <>
                    {" "}- giới hạn <span className="text-white">{query.result_limit}</span> kết quả
                  </>
                )}
              </div>
              <div className="flex items-center gap-2">
                <label className="font-mono text-xs text-dim uppercase tracking-wider">
                  Định dạng
                </label>
                <select
                  value={exportFormat}
                  onChange={(e) => setExportFormat(e.target.value)}
                  className="rounded-lg border border-border bg-card px-3 py-2 text-sm text-white focus:outline-none focus:border-pulse/60"
                >
                  <option value="csv">CSV</option>
                  <option value="excel">Excel</option>
                </select>
                <a
                  href={`${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/api/export?format=${exportFormat}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="bg-pulse/10 text-pulse hover:bg-pulse hover:text-ink font-bold py-2 px-4 rounded transition-colors text-sm flex items-center gap-2"
                >
                  📥 Tải dữ liệu
                </a>
              </div>
            </div>

            <AIInsights insights={insights} />
            <DataTable   businesses={businesses} />
            <Dashboard   businesses={businesses} />

            {/* Footer spacer */}
            <div className="mt-16 flex items-center gap-3">
              <div className="flex-1 h-px bg-border" />
              <span className="font-mono text-xs text-dim/40">LeadSpyAI</span>
              <div className="flex-1 h-px bg-border" />
            </div>
          </>
        )}
      </div>
    </div>
  );
}