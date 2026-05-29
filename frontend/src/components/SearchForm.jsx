import { useEffect, useState } from "react";

export default function SearchForm({ onSearchComplete, loading, initialValues }) {
  const [keyword, setKeyword] = useState("");
  const [location, setLocation] = useState("");
  const [minRating, setMinRating] = useState("");
  const [resultLimit, setResultLimit] = useState("");

  useEffect(() => {
    if (!initialValues) return;
    setKeyword(initialValues.keyword || "");
    setLocation(initialValues.location || "");
    setMinRating(initialValues.min_rating || "");
    setResultLimit(initialValues.result_limit || "");
  }, [initialValues]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!keyword.trim() || !location.trim()) return;

    const parsedLimit = resultLimit.trim() ? Number(resultLimit) : undefined;
    const parsedRating = minRating.trim() ? Number(minRating) : undefined;

    onSearchComplete({
      keyword: keyword.trim(),
      location: location.trim(),
      min_rating: Number.isFinite(parsedRating) ? parsedRating : undefined,
      result_limit: Number.isFinite(parsedLimit) ? parsedLimit : undefined,
    });
  };

  return (
    <div className="animate-fade-up" style={{ animationDelay: "0.1s", opacity: 0 }}>
      <div className="mb-10 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-pulse/30 bg-pulse/5 mb-4">
          <span className="w-1.5 h-1.5 rounded-full bg-pulse animate-pulse-dot" />
          <span className="font-sans text-xs text-pulse tracking-widest uppercase font-semibold">
            GOOGLE MAPS DATA COLLECTION
          </span>
        </div>
        <h2 className="text-3xl font-sans font-extrabold tracking-tight text-white">
          Bổ sung dữ liệu còn thiếu
        </h2>
        <p className="mt-3 text-white/80 font-sans text-sm max-w-xl mx-auto leading-relaxed">
          AI đã kiểm tra kho nội bộ trước. Nếu chưa đủ dữ liệu, form này được điền sẵn để
          cào thêm kết quả từ Google Maps theo đúng tham số trong câu hỏi.
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 max-w-5xl mx-auto"
      >
        <div className="relative group">
          <label className="absolute -top-5 left-1 font-mono text-xs text-dim tracking-wider uppercase">
            Từ khóa
          </label>
          <input
            type="text"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="VD: quán cà phê"
            disabled={loading}
            className="w-full px-4 py-3 rounded-lg font-body text-sm bg-card border border-border text-white placeholder-dim/50 focus:outline-none focus:border-pulse/60 focus:ring-1 focus:ring-pulse/30 disabled:opacity-40 transition-all duration-200"
          />
        </div>

        <div className="relative group">
          <label className="absolute -top-5 left-1 font-mono text-xs text-dim tracking-wider uppercase">
            Khu vực
          </label>
          <input
            type="text"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="VD: Gò Vấp"
            disabled={loading}
            className="w-full px-4 py-3 rounded-lg font-body text-sm bg-card border border-border text-white placeholder-dim/50 focus:outline-none focus:border-pulse/60 focus:ring-1 focus:ring-pulse/30 disabled:opacity-40 transition-all duration-200"
          />
        </div>

        <div className="relative group">
          <label className="absolute -top-5 left-1 font-mono text-xs text-dim tracking-wider uppercase">
            Lọc sao
          </label>
          <select
            value={minRating}
            onChange={(e) => setMinRating(e.target.value)}
            disabled={loading}
            className="w-full px-4 py-3 rounded-lg font-body text-sm bg-card border border-border text-white focus:outline-none focus:border-pulse/60 focus:ring-1 focus:ring-pulse/30 disabled:opacity-40 transition-all duration-200"
          >
            <option value="">Không lọc</option>
            <option value="3">&gt; 3.0 sao</option>
            <option value="3.5">&gt; 3.5 sao</option>
            <option value="4">&gt; 4.0 sao</option>
            <option value="4.5">&gt; 4.5 sao</option>
          </select>
        </div>

        <div className="relative group">
          <label className="absolute -top-5 left-1 font-mono text-xs text-dim tracking-wider uppercase">
            Số lượng cần có
          </label>
          <input
            type="number"
            min="1"
            max="100"
            value={resultLimit}
            onChange={(e) => setResultLimit(e.target.value)}
            placeholder="VD: 20"
            disabled={loading}
            className="w-full px-4 py-3 rounded-lg font-body text-sm bg-card border border-border text-white placeholder-dim/50 focus:outline-none focus:border-pulse/60 focus:ring-1 focus:ring-pulse/30 disabled:opacity-40 transition-all duration-200"
          />
        </div>

        <button
          type="submit"
          className="sm:col-span-2 lg:col-span-4 mt-2 px-8 py-3 rounded-lg font-display font-bold text-sm tracking-wide uppercase bg-pulse text-ink hover:bg-pulse/90 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200"
          disabled={loading || !keyword.trim() || !location.trim()}
          style={{ minWidth: "180px" }}
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Đang xử lý...
            </span>
          ) : (
            "Cào thêm từ Google Maps →"
          )}
        </button>
      </form>
    </div>
  );
}
