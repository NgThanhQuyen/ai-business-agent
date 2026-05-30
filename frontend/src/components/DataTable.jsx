import { useEffect, useState } from "react";
import axiosClient from "../api/axiosClient";
import { BarChart, Bar, XAxis, YAxis, PieChart, Pie, Cell } from "recharts";

const STARS = (rating) => {
  if (!rating) return "—";
  const full  = Math.floor(rating);
  const half  = rating % 1 >= 0.5 ? 1 : 0;
  const empty = 5 - full - half;
  return "★".repeat(full) + (half ? "½" : "") + "☆".repeat(empty);
};

const RatingBadge = ({ rating }) => {
  if (!rating) return <span className="text-dim text-xs">Chưa có</span>;
  const color =
    rating >= 4.5 ? "#00FF94" :
    rating >= 4.0 ? "#A3E635" :
    rating >= 3.0 ? "#FACC15" : "#F87171";
  return (
    <span
      className="font-mono text-xs font-semibold px-2 py-0.5 rounded"
      style={{ color, background: `${color}18`, border: `1px solid ${color}40` }}
    >
      {rating.toFixed(1)}
    </span>
  );
};

const COLS = [
  { key: "name",         label: "Tên"          },
  { key: "address",      label: "Địa chỉ"      },
  { key: "phone",        label: "Số điện thoại" },
  { key: "rating",       label: "Đánh giá"      },
  { key: "review_count", label: "Số lượt đánh giá" },
  { key: "website",      label: "Trang web"      },
  { key: "ai_score",     label: "🔥 Điểm AI"  },
  { key: "ai_reason",    label: "Gợi ý AI"     },
];

// Bảng màu cho biểu đồ Recharts trong báo cáo
const CHART_COLORS = ["#00FF94", "#818CF8", "#FACC15", "#A3E635", "#F87171"];

function buildRatingDist(data) {
  const buckets = {
    "< 3.0": 0, "3.0–3.9": 0,
    "4.0–4.4": 0, "4.5–4.9": 0, "5.0": 0, "Chưa có đánh giá": 0,
  };
  data.forEach(({ rating }) => {
    if (!rating)         buckets["Chưa có đánh giá"]++;
    else if (rating < 3) buckets["< 3.0"]++;
    else if (rating < 4) buckets["3.0–3.9"]++;
    else if (rating < 4.5) buckets["4.0–4.4"]++;
    else if (rating < 5) buckets["4.5–4.9"]++;
    else                 buckets["5.0"]++;
  });
  return Object.entries(buckets)
    .filter(([, v]) => v > 0)
    .map(([name, count]) => ({ name, count }));
}

function buildReviewBuckets(data) {
  const b = { "0": 0, "1–50": 0, "51–200": 0, "201–500": 0, "500+": 0 };
  data.forEach(({ review_count: rc }) => {
    if (!rc || rc === 0)   b["0"]++;
    else if (rc <= 50)     b["1–50"]++;
    else if (rc <= 200)    b["51–200"]++;
    else if (rc <= 500)    b["201–500"]++;
    else                   b["500+"]++;
  });
  return Object.entries(b)
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ name, value }));
}

const renderSalesStrategy = (strategy) => {
  if (!strategy) return "—";
  if (typeof strategy === "string") {
    return <div className="whitespace-pre-line">{strategy}</div>;
  }
  if (Array.isArray(strategy)) {
    return (
      <div className="space-y-3">
        {strategy.map((item, idx) => {
          if (typeof item === "string") {
            return <p key={idx}>{item}</p>;
          }
          if (typeof item === "object" && item !== null) {
            return Object.entries(item).map(([key, val]) => (
              <div key={key} className="mb-2">
                <span className="font-bold text-slate-800">{key}: </span>
                <span className="text-slate-700">{String(val)}</span>
              </div>
            ));
          }
          return null;
        })}
      </div>
    );
  }
  return String(strategy);
};

const renderSafeText = (val) => {
  if (!val) return "—";
  if (typeof val === "string") return val;
  if (Array.isArray(val)) return val.join("\n");
  if (typeof val === "object") return JSON.stringify(val);
  return String(val);
};

export default function DataTable({ data, selectedBusinessId, onSelectBusiness }) {
  const [sortKey,  setSortKey]  = useState("rating");
  const [sortDir,  setSortDir]  = useState("desc");
  const [page,     setPage]     = useState(1);
  const PER_PAGE = 10;

  // Trạng thái so sánh đối thủ
  const [isComparing, setIsComparing] = useState(false);
  const [selectedCompareIds, setSelectedCompareIds] = useState([]);
  const [comparisonResult, setComparisonResult] = useState(null);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [comparisonError, setComparisonError] = useState(null);

  const compBiz1 = selectedCompareIds[0] ? data.find(b => b.id === selectedCompareIds[0]) : null;
  const compBiz2 = selectedCompareIds[1] ? data.find(b => b.id === selectedCompareIds[1]) : null;

  // Trạng thái hộp thoại (modal) báo cáo PDF
  const [showReportModal, setShowReportModal] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportInsights, setReportInsights] = useState(null);

  useEffect(() => {
    setPage(1);
    setIsComparing(false);
    setSelectedCompareIds([]);
    setComparisonResult(null);
    setComparisonError(null);
  }, [data]);

  if (!data?.length) return null;

  // Sắp xếp
  const sorted = [...data].sort((a, b) => {
    const av = a[sortKey] ?? (typeof a[sortKey] === "number" ? -Infinity : "");
    const bv = b[sortKey] ?? (typeof b[sortKey] === "number" ? -Infinity : "");
    if (av < bv) return sortDir === "asc" ? -1 :  1;
    if (av > bv) return sortDir === "asc" ?  1 : -1;
    return 0;
  });

  // Phân trang
  const totalPages = Math.ceil(sorted.length / PER_PAGE);
  const paged      = sorted.slice((page - 1) * PER_PAGE, page * PER_PAGE);

  const toggleSort = (key) => {
    if (sortKey === key) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("desc"); }
    setPage(1);
  };

  const SortIcon = ({ k }) =>
    sortKey !== k ? (
      <span className="text-dim/40 ml-1">↕</span>
    ) : sortDir === "asc" ? (
      <span className="text-pulse ml-1">↑</span>
    ) : (
      <span className="text-pulse ml-1">↓</span>
    );

  // Các bộ xử lý so sánh đối thủ
  const toggleCompareMode = () => {
    setIsComparing(!isComparing);
    setSelectedCompareIds([]);
    setComparisonResult(null);
    setComparisonError(null);
  };

  const handleSelectCompare = (id) => {
    setSelectedCompareIds((prev) => {
      if (prev.includes(id)) {
        return prev.filter((item) => item !== id);
      }
      if (prev.length >= 2) {
        return prev;
      }
      return [...prev, id];
    });
  };

  const executeComparison = async () => {
    if (selectedCompareIds.length !== 2) return;
    setComparisonLoading(true);
    setComparisonError(null);
    setComparisonResult(null);
    try {
      const response = await axiosClient.post("/api/compare", {
        id1: selectedCompareIds[0],
        id2: selectedCompareIds[1],
      });
      setComparisonResult(response.data);
    } catch (err) {
      setComparisonError(err.message);
      alert("Lỗi khi so sánh: " + err.message);
    } finally {
      setComparisonLoading(false);
    }
  };

  // Các bộ xử lý xuất báo cáo PDF
  const handlePDFReport = async () => {
    setShowReportModal(true);
    if (reportInsights) return; // already loaded for this dataset
    
    setReportLoading(true);
    try {
      const ids = data.map((b) => b.id);
      const response = await axiosClient.post("/api/report-insights", { ids });
      setReportInsights(response.data);
    } catch (err) {
      alert("Lỗi khi tải insights báo cáo: " + err.message);
      setShowReportModal(false);
    } finally {
      setReportLoading(false);
    }
  };

  const downloadPDFDirect = () => {
    const element = document.getElementById("pdf-report-content");
    if (!element) return;
    
    const opt = {
      margin:       0.3,
      filename:     'baocao_leadspyai.pdf',
      image:        { type: 'jpeg', quality: 0.98 },
      html2canvas:  { 
        scale: 2, 
        useCORS: true,
        scrollY: 0,
        scrollX: 0
      },
      jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
    };
    
    if (window.html2pdf) {
      window.html2pdf().from(element).set(opt).save();
    } else {
      alert("Thư viện xuất PDF chưa tải xong, vui lòng thử lại sau.");
    }
  };

  const printPDF = () => {
    const content = document.getElementById("pdf-report-content").innerHTML;
    const printWindow = window.open("", "_blank");
    printWindow.document.write(`
      <html>
        <head>
          <title>Báo cáo LeadSpyAI</title>
          <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
          <style>
            body {
              font-family: 'DM Sans', sans-serif;
              color: #1e293b;
              padding: 40px;
              background-color: #ffffff;
            }
            h1, h2, h3 {
              color: #0f172a;
            }
            .section-title {
              border-bottom: 2px solid #e2e8f0;
              padding-bottom: 0.5rem;
              margin-bottom: 1rem;
              color: #1e293b;
              margin-top: 24px;
            }
            table {
              width: 100%;
              border-collapse: collapse;
              margin-top: 15px;
            }
            th, td {
              border: 1px solid #cbd5e1;
              padding: 8px;
              text-align: left;
            }
            th {
              background-color: #f1f5f9;
            }
            .grid {
              display: grid;
              grid-template-columns: repeat(4, 1fr);
              gap: 15px;
              margin-top: 15px;
              margin-bottom: 15px;
            }
            .bg-slate-50 {
              background-color: #f8fafc;
              padding: 15px;
              border-radius: 8px;
              border: 1px solid #e2e8f0;
              text-align: center;
            }
            .text-center { text-align: center; }
            .text-xs { font-size: 11px; }
            .text-slate-500 { color: #64748b; }
            .text-2xl { font-size: 24px; font-weight: bold; }
            .font-mono { font-family: monospace; }
            .font-semibold { font-weight: 600; }
            .border-b-4 { border-bottom: 4px solid #00FF94; }
            .pb-6 { padding-bottom: 24px; }
            .text-3xl { font-size: 28px; }
            .mt-2 { margin-top: 8px; }
            .mt-4 { margin-top: 16px; }
            .mt-8 { margin-top: 32px; }
            .pt-4 { padding-top: 16px; }
            .border-t { border-top: 1px solid #e2e8f0; }
            .text-slate-400 { color: #94a3b8; }
            .bg-slate-50 { background-color: #f8fafc; }
            .p-4 { padding: 16px; }
            .rounded-xl { border-radius: 12px; }
            .border-slate-100 { border-color: #f1f5f9; }
            .text-sm { font-size: 14px; }
            .leading-relaxed { line-height: 1.625; }
            .text-justify { text-align: justify; }
            .whitespace-pre-line { white-space: pre-line; }
          </style>
        </head>
        <body>
          ${content}
          <script>
            window.onload = function() {
              window.print();
              window.close();
            }
          </script>
        </body>
      </html>
    `);
    printWindow.document.close();
  };

  // Bộ xử lý xuất tệp CSV/Excel
  const handleExport = async (format) => {
    try {
      const idsParam = data.map((b) => b.id).join(",");
      const response = await axiosClient.get(`/api/export?format=${format}&ids=${idsParam}`, {
        responseType: "blob",
      });
      const blob = new Blob([response.data], {
        type:
          format === "excel"
            ? "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            : "text/csv",
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `export_${new Date().getTime()}.${format === "excel" ? "xlsx" : "csv"}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert("Lỗi khi xuất tệp dữ liệu: " + err.message);
    }
  };

  // Các biến phân nhóm thông tin chi tiết cho hộp thoại báo cáo
  const ratingDist = buildRatingDist(data);
  const reviewBuckets = buildReviewBuckets(data);

  return (
    <div
      className="animate-fade-up mt-10 rounded-xl border border-border"
      style={{ animationDelay: "0.2s", opacity: 0 }}
    >
      {/* Thanh tiêu đề bảng */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between px-5 py-3.5 border-b border-border bg-card gap-3">
        <div className="flex items-center gap-3">
          <span className="font-display font-bold text-sm tracking-wide text-white/80">
            Kết quả
            <span className="ml-2 font-mono text-pulse text-xs">
              [{data.length}]
            </span>
          </span>
          {isComparing && (
            <span className="text-xs text-amber-400 animate-pulse font-sans">
              (Chọn đúng 2 quán ở danh sách để tiến hành so sánh)
            </span>
          )}
        </div>

        {/* 3 nút ở góc trên bên phải */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Nút 1: So sánh */}
          <button
            onClick={toggleCompareMode}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 active:scale-95 ${
              isComparing
                ? "bg-amber-500 text-slate-950 hover:bg-amber-400"
                : "bg-slate-800 text-emerald-400 hover:bg-slate-700 border border-emerald-500/20"
            }`}
          >
            {isComparing ? "Hủy so sánh" : "⚖️ So sánh đối thủ"}
          </button>
          
          {isComparing && selectedCompareIds.length === 2 && (
            <button
              onClick={executeComparison}
              disabled={comparisonLoading}
              className="px-3 py-1.5 rounded-lg text-xs font-bold bg-[#00FF94] text-slate-950 hover:bg-[#00FF94]/90 animate-pulse transition-all duration-200 active:scale-95 disabled:opacity-50"
            >
              {comparisonLoading ? "Đang so sánh..." : "⚡ So sánh ngay (2)"}
            </button>
          )}

          {/* Nút 2: Báo cáo PDF */}
          <button
            onClick={handlePDFReport}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 text-cyan-400 hover:bg-slate-700 border border-cyan-500/20 transition-all duration-200 active:scale-95"
          >
            📋 Tải báo cáo PDF
          </button>

          {/* Nút 3: Tải dữ liệu */}
          <div className="relative group">
            <button
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 text-lime-400 hover:bg-slate-700 border border-lime-500/20 transition-all duration-200 active:scale-95 flex items-center gap-1"
            >
              📥 Tải Data ▾
            </button>
            <div className="absolute right-0 top-[calc(100%-4px)] pt-1 hidden group-hover:block z-20">
              <div className="bg-slate-900 border border-white/10 rounded-lg shadow-xl overflow-hidden min-w-[120px]">
                <button
                  onClick={() => handleExport("excel")}
                  className="w-full text-left px-4 py-2.5 text-xs text-slate-300 hover:bg-slate-800 hover:text-[#00FF94] transition-colors"
                >
                  Excel (.xlsx)
                </button>
                <button
                  onClick={() => handleExport("csv")}
                  className="w-full text-left px-4 py-2.5 text-xs text-slate-300 hover:bg-slate-800 hover:text-[#00FF94] transition-colors"
                >
                  CSV (.csv)
                </button>
              </div>
            </div>
          </div>

          <span className="font-mono text-xs text-dim ml-2 hidden lg:inline">
            trang {page}/{totalPages}
          </span>
        </div>
      </div>

      {/* Bảng có thể cuộn ngang */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm font-body border-collapse">
          <thead>
            <tr className="border-b border-border bg-lead/60">
              {isComparing && (
                <th className="px-4 py-3 text-left font-mono text-xs text-dim uppercase tracking-widest w-16 select-none">
                  Chọn
                </th>
              )}
              {COLS.map((col) => (
                <th
                  key={col.key}
                  onClick={() => toggleSort(col.key)}
                  className="
                    px-4 py-3 text-left font-mono text-xs text-dim
                    uppercase tracking-widest cursor-pointer select-none
                    hover:text-pulse transition-colors whitespace-nowrap
                  "
                >
                  {col.label}
                  <SortIcon k={col.key} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paged.map((biz, i) => (
              <tr
                key={biz.id}
                className="
                  border-b border-border/50 transition-colors duration-150
                  hover:bg-pulse/5 group cursor-pointer
                "
                onClick={() => {
                  if (isComparing) {
                    handleSelectCompare(biz.id);
                  } else {
                    onSelectBusiness?.(biz.id);
                  }
                }}
                style={{ animationDelay: `${i * 0.04}s` }}
                aria-selected={selectedBusinessId === biz.id}
              >
                {/* Cột hộp kiểm chọn so sánh */}
                {isComparing && (
                  <td className="px-4 py-3 align-top" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selectedCompareIds.includes(biz.id)}
                      onChange={() => handleSelectCompare(biz.id)}
                      disabled={!selectedCompareIds.includes(biz.id) && selectedCompareIds.length >= 2}
                      className="w-4 h-4 rounded border-slate-700 bg-slate-800 text-pulse focus:ring-pulse/30 cursor-pointer accent-[#00FF94]"
                    />
                  </td>
                )}

                {/* Tên */}
                <td
                  className={`px-4 py-3 font-semibold whitespace-normal break-words align-top ${
                    selectedBusinessId === biz.id ? "text-pulse" : "text-white/90"
                  }`}
                >
                  {biz.name}
                </td>

                {/* Địa chỉ */}
                <td className="px-4 py-3 text-dim whitespace-normal break-words align-top" title={biz.address}>
                  {biz.address || "—"}
                </td>

                {/* Số điện thoại */}
                <td className="px-4 py-3 font-mono text-xs text-white/70 whitespace-normal break-words align-top">
                  {biz.phone || "—"}
                </td>

                {/* Đánh giá */}
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <RatingBadge rating={biz.rating} />
                    {biz.rating && (
                      <span className="text-yellow-400/60 text-xs hidden xl:inline">
                        {STARS(biz.rating)}
                      </span>
                    )}
                  </div>
                </td>

                {/* Số lượng review */}
                <td className="px-4 py-3 font-mono text-xs text-white/60">
                  {biz.review_count != null
                    ? biz.review_count.toLocaleString()
                    : "—"}
                </td>

                {/* Website */}
                <td className="px-4 py-3 align-top">
                  {biz.website ? (
                    <a
                      href={biz.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="
                        font-mono text-xs text-pulse/80
                        hover:text-pulse underline underline-offset-2
                        transition-colors break-all
                      "
                      onClick={(e) => e.stopPropagation()}
                    >
                      {biz.website}
                    </a>
                  ) : (
                    <span className="text-dim text-xs">—</span>
                  )}
                </td>

                {/* Điểm AI */}
                <td className="px-4 py-3 font-mono font-bold text-pulse align-top">
                  {biz.ai_score != null ? biz.ai_score : "—"}
                </td>

                {/* Gợi ý AI */}
                <td className="px-4 py-3 text-xs text-dim whitespace-normal break-words align-top" title={biz.ai_reason}>
                  {biz.ai_reason || "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 px-5 py-3 border-t border-border bg-card">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 rounded font-mono text-xs border border-border text-dim hover:border-pulse hover:text-pulse disabled:opacity-30 transition-all"
          >
            ← Trước
          </button>
          {Array.from({ length: totalPages }, (_, i) => i + 1).map(n => (
            <button
              key={n}
              onClick={() => setPage(n)}
              className={`
                w-7 h-7 rounded font-mono text-xs border transition-all
                ${n === page
                  ? "bg-pulse text-ink border-pulse font-bold"
                  : "border-border text-dim hover:border-pulse hover:text-pulse"}
              `}
            >
              {n}
            </button>
          ))}
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1 rounded font-mono text-xs border border-border text-dim hover:border-pulse hover:text-pulse disabled:opacity-30 transition-all"
          >
            Sau →
          </button>
        </div>
      )}

      {/* Comparison Result Section (Below the Table) */}
      {comparisonResult && (
        <div className="animate-fade-up mt-8 mx-5 mb-8 rounded-2xl border border-white/10 bg-slate-900/60 p-6 shadow-2xl backdrop-blur-xl relative overflow-hidden group">
          <div className="pointer-events-none absolute -right-20 -top-20 w-48 h-48 rounded-full bg-amber-500/5 blur-3xl opacity-100" />
          
          <div className="flex items-center justify-between border-b border-white/10 pb-4 mb-6">
            <h3 className="text-base font-display font-bold text-transparent bg-clip-text bg-gradient-to-r from-amber-300 to-emerald-300 flex items-center gap-2">
              ⚖️ Phân tích so sánh đối thủ từ AI Agent
            </h3>
            <button
              onClick={() => setComparisonResult(null)}
              className="text-xs text-slate-400 hover:text-white transition-colors"
            >
              Đóng so sánh ×
            </button>
          </div>

          {/* Table comparing metadata */}
          {compBiz1 && compBiz2 && (
            <div className="mb-6 overflow-hidden rounded-xl border border-white/5 bg-slate-950/40">
              <table className="w-full text-sm text-left border-collapse">
                <thead>
                  <tr className="border-b border-white/10 bg-white/5">
                    <th className="px-4 py-2.5 font-mono text-[10px] text-slate-400 uppercase tracking-wider">Thông tin</th>
                    <th className="px-4 py-2.5 font-bold text-[#00FF94]">{compBiz1.name}</th>
                    <th className="px-4 py-2.5 font-bold text-cyan-300">{compBiz2.name}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-white/5 hover:bg-white/5 transition-colors">
                    <td className="px-4 py-2.5 font-semibold text-slate-300">🔥 Điểm AI</td>
                    <td className="px-4 py-2.5 font-mono font-bold text-[#00FF94]">{compBiz1.ai_score != null ? compBiz1.ai_score : "—"}</td>
                    <td className="px-4 py-2.5 font-mono font-bold text-cyan-300">{compBiz2.ai_score != null ? compBiz2.ai_score : "—"}</td>
                  </tr>
                  <tr className="border-b border-white/5 hover:bg-white/5 transition-colors">
                    <td className="px-4 py-2.5 font-semibold text-slate-300">Đánh giá</td>
                    <td className="px-4 py-2.5 text-slate-200">
                      <div className="flex items-center gap-1.5">
                        <span className="text-yellow-400">★</span>
                        <span className="font-mono">{(compBiz1.rating || 0).toFixed(1)}</span>
                        <span className="text-xs text-slate-400">({compBiz1.review_count?.toLocaleString() || 0} reviews)</span>
                      </div>
                    </td>
                    <td className="px-4 py-2.5 text-slate-200">
                      <div className="flex items-center gap-1.5">
                        <span className="text-yellow-400">★</span>
                        <span className="font-mono">{(compBiz2.rating || 0).toFixed(1)}</span>
                        <span className="text-xs text-slate-400">({compBiz2.review_count?.toLocaleString() || 0} reviews)</span>
                      </div>
                    </td>
                  </tr>
                  <tr className="border-b border-white/5 hover:bg-white/5 transition-colors">
                    <td className="px-4 py-2.5 font-semibold text-slate-300">Số điện thoại</td>
                    <td className="px-4 py-2.5 font-mono text-slate-200">{compBiz1.phone || "—"}</td>
                    <td className="px-4 py-2.5 font-mono text-slate-200">{compBiz2.phone || "—"}</td>
                  </tr>
                  <tr className="hover:bg-white/5 transition-colors">
                    <td className="px-4 py-2.5 font-semibold text-slate-300">Trang web</td>
                    <td className="px-4 py-2.5 text-slate-200">
                      {compBiz1.website ? (
                        <a href={compBiz1.website} target="_blank" rel="noopener noreferrer" className="text-pulse hover:underline break-all" onClick={(e) => e.stopPropagation()}>{compBiz1.website}</a>
                      ) : "—"}
                    </td>
                    <td className="px-4 py-2.5 text-slate-200">
                      {compBiz2.website ? (
                        <a href={compBiz2.website} target="_blank" rel="noopener noreferrer" className="text-pulse hover:underline break-all" onClick={(e) => e.stopPropagation()}>{compBiz2.website}</a>
                      ) : "—"}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Column for Business 1 */}
            <div className="bg-slate-950/40 border border-white/5 rounded-xl p-5 flex flex-col gap-4">
              <h4 className="text-base font-bold text-[#00FF94] flex items-center gap-2">
                🏢 {comparisonResult.biz1.name}
              </h4>
              <div className="space-y-3">
                <div>
                  <span className="text-[10px] font-mono text-slate-400 uppercase tracking-widest">Điểm mạnh</span>
                  <ul className="list-disc pl-5 text-sm text-emerald-200 mt-1 space-y-1">
                    {comparisonResult.biz1.strengths.map((s, idx) => <li key={idx}>{s}</li>)}
                  </ul>
                </div>
                <div>
                  <span className="text-[10px] font-mono text-slate-400 uppercase tracking-widest">Điểm yếu</span>
                  <ul className="list-disc pl-5 text-sm text-red-300 mt-1 space-y-1">
                    {comparisonResult.biz1.weaknesses.map((w, idx) => <li key={idx}>{w}</li>)}
                  </ul>
                </div>
              </div>
            </div>
            
            {/* Column for Business 2 */}
            <div className="bg-slate-950/40 border border-white/5 rounded-xl p-5 flex flex-col gap-4">
              <h4 className="text-base font-bold text-cyan-300 flex items-center gap-2">
                🏢 {comparisonResult.biz2.name}
              </h4>
              <div className="space-y-3">
                <div>
                  <span className="text-[10px] font-mono text-slate-400 uppercase tracking-widest">Điểm mạnh</span>
                  <ul className="list-disc pl-5 text-sm text-emerald-200 mt-1 space-y-1">
                    {comparisonResult.biz2.strengths.map((s, idx) => <li key={idx}>{s}</li>)}
                  </ul>
                </div>
                <div>
                  <span className="text-[10px] font-mono text-slate-400 uppercase tracking-widest">Điểm yếu</span>
                  <ul className="list-disc pl-5 text-sm text-red-300 mt-1 space-y-1">
                    {comparisonResult.biz2.weaknesses.map((w, idx) => <li key={idx}>{w}</li>)}
                  </ul>
                </div>
              </div>
            </div>
          </div>
          
          {/* Strategic Analysis & Verdict */}
          <div className="mt-6 pt-5 border-t border-white/10 space-y-4">
            <div className="space-y-1.5">
              <span className="text-[10px] font-mono text-slate-400 uppercase tracking-widest">Phân tích đối chiến lược</span>
              <p className="text-sm text-slate-300 leading-relaxed text-justify bg-slate-950/20 p-4 rounded-xl border border-white/5">
                {comparisonResult.analysis}
              </p>
            </div>
            
            <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 flex items-start gap-3 mt-2">
              <span className="text-2xl mt-0.5">🏆</span>
              <div>
                <span className="text-xs font-bold text-amber-400 uppercase tracking-wider">Đề xuất chuyên gia</span>
                <p className="text-sm text-amber-100 font-semibold mt-1 leading-relaxed">
                  {comparisonResult.verdict}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* PDF Report Modal */}
      {showReportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="bg-slate-900 border border-white/10 rounded-2xl w-full max-w-5xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-fade-up">
            {/* Control Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-slate-950/40">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                📊 Báo cáo phân tích thị trường & Insights AI
              </h3>
              <div className="flex items-center gap-2">
                {!reportLoading && reportInsights && (
                  <>
                    <button
                      onClick={downloadPDFDirect}
                      className="px-3.5 py-1.5 rounded-lg text-xs font-bold bg-[#00FF94] text-slate-950 hover:bg-[#00FF94]/90 flex items-center gap-1.5 transition-all active:scale-95"
                    >
                      📥 Tải PDF
                    </button>
                    <button
                      onClick={printPDF}
                      className="px-3.5 py-1.5 rounded-lg text-xs font-bold bg-slate-800 text-white hover:bg-slate-700 border border-white/10 flex items-center gap-1.5 transition-all active:scale-95"
                    >
                      🖨️ In / Lưu PDF
                    </button>
                  </>
                )}
                <button
                  onClick={() => setShowReportModal(false)}
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 text-slate-300 hover:bg-slate-700"
                >
                  Đóng
                </button>
              </div>
            </div>
            
            {/* Scrollable Report Content */}
            <div className="flex-1 overflow-y-auto p-6 bg-slate-950/20 text-slate-100">
              {reportLoading ? (
                <div className="flex flex-col items-center justify-center py-20 gap-4">
                  <svg className="animate-spin h-10 w-10 text-[#00FF94]" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  <p className="text-xs font-mono text-dim tracking-widest uppercase animate-pulse">
                    AI đang tổng hợp dữ liệu & lập báo cáo thị trường...
                  </p>
                </div>
              ) : (
                <div id="pdf-report-content" className="p-8 bg-white text-slate-900 rounded-xl shadow-xl flex flex-col gap-8 font-sans max-w-4xl mx-auto">
                  {/* Print custom styling overrides */}
                  <style dangerouslySetInnerHTML={{__html: `
                    #pdf-report-content h1, #pdf-report-content h2, #pdf-report-content h3 {
                      font-family: 'DM Sans', sans-serif;
                      font-weight: 700;
                    }
                    #pdf-report-content .section-title {
                      border-bottom: 2px solid #cbd5e1;
                      padding-bottom: 0.5rem;
                      margin-bottom: 1rem;
                      color: #0f172a;
                      margin-top: 1.5rem;
                    }
                  `}} />
                  
                  {/* Header */}
                  <div className="text-center border-b-4 border-[#00FF94] pb-6">
                    <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 uppercase">BÁO CÁO PHÂN TÍCH THỊ TRƯỜNG & LEAD INSIGHTS</h1>
                    <p className="text-xs text-slate-500 font-mono mt-2">Ngày lập: {new Date().toLocaleDateString('vi-VN')} | Tạo tự động bởi LeadSpyAI</p>
                  </div>
                  
                  {/* Key Statistics */}
                  <div>
                    <h2 className="text-base font-bold text-slate-800 section-title">📊 1. Số liệu thống kê tổng quan</h2>
                    <div className="grid grid-cols-4 gap-4 mt-4" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '15px' }}>
                      <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-center" style={{ backgroundColor: '#f8fafc', padding: '15px', borderRadius: '12px', border: '1px solid #e2e8f0', textAlign: 'center' }}>
                        <p className="text-[10px] text-slate-500 uppercase font-semibold">Tổng doanh nghiệp</p>
                        <p className="text-2xl font-extrabold text-slate-900 mt-1">{data.length}</p>
                      </div>
                      <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-center" style={{ backgroundColor: '#f8fafc', padding: '15px', borderRadius: '12px', border: '1px solid #e2e8f0', textAlign: 'center' }}>
                        <p className="text-[10px] text-slate-500 uppercase font-semibold">Điểm đánh giá TB</p>
                        <p className="text-2xl font-extrabold text-slate-900 mt-1">
                          {data.filter(b => b.rating).length 
                            ? (data.filter(b => b.rating).reduce((acc, curr) => acc + curr.rating, 0) / data.filter(b => b.rating).length).toFixed(2)
                            : "N/A"
                          }
                        </p>
                      </div>
                      <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-center" style={{ backgroundColor: '#f8fafc', padding: '15px', borderRadius: '12px', border: '1px solid #e2e8f0', textAlign: 'center' }}>
                        <p className="text-[10px] text-slate-500 uppercase font-semibold">Tổng lượt review</p>
                        <p className="text-2xl font-extrabold text-slate-900 mt-1">
                          {data.reduce((acc, curr) => acc + (curr.review_count || 0), 0).toLocaleString('vi-VN')}
                        </p>
                      </div>
                      <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-center" style={{ backgroundColor: '#f8fafc', padding: '15px', borderRadius: '12px', border: '1px solid #e2e8f0', textAlign: 'center' }}>
                        <p className="text-[10px] text-slate-500 uppercase font-semibold">Có Website (%)</p>
                        <p className="text-2xl font-extrabold text-slate-900 mt-1">
                          {data.length ? Math.round((data.filter(b => b.website).length / data.length) * 100) : 0}%
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Cohort Visual Charts */}
                  <div>
                    <h2 className="text-base font-bold text-slate-800 section-title">📈 2. Phân tích đồ thị dữ liệu</h2>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginTop: '15px' }}>
                      <div style={{ border: '1px solid #e2e8f0', borderRadius: '12px', padding: '15px', width: '100%' }}>
                        <h4 style={{ fontSize: '12px', fontWeight: 'bold', color: '#64748b', marginBottom: '15px', textTransform: 'uppercase', textAlign: 'center' }}>Phân bổ điểm đánh giá</h4>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          {ratingDist.map((item, idx) => {
                            const maxVal = Math.max(...ratingDist.map(r => r.count), 1);
                            const pct = Math.round((item.count / maxVal) * 100);
                            return (
                              <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                <span style={{ fontSize: '11px', color: '#475569', width: '90px', whiteSpace: 'nowrap' }}>{item.name}</span>
                                <div style={{ flex: 1, height: '8px', backgroundColor: '#f1f5f9', borderRadius: '4px', overflow: 'hidden' }}>
                                  <div style={{ width: `${pct}%`, height: '100%', backgroundColor: '#00FF94', borderRadius: '4px' }}></div>
                                </div>
                                <span style={{ fontSize: '11px', fontWeight: 'bold', color: '#1e293b', width: '25px', textAlign: 'right' }}>{item.count}</span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                      <div style={{ border: '1px solid #e2e8f0', borderRadius: '12px', padding: '15px', width: '100%' }}>
                        <h4 style={{ fontSize: '12px', fontWeight: 'bold', color: '#64748b', marginBottom: '15px', textTransform: 'uppercase', textAlign: 'center' }}>Phân bổ số lượng review</h4>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          {reviewBuckets.map((item, idx) => {
                            const totalVal = data.length || 1;
                            const pct = Math.round((item.value / totalVal) * 100);
                            const color = CHART_COLORS[idx % CHART_COLORS.length] || "#818CF8";
                            return (
                              <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                <span style={{ fontSize: '11px', color: '#475569', width: '60px', whiteSpace: 'nowrap' }}>{item.name} review</span>
                                <div style={{ flex: 1, height: '8px', backgroundColor: '#f1f5f9', borderRadius: '4px', overflow: 'hidden' }}>
                                  <div style={{ width: `${pct}%`, height: '100%', backgroundColor: color, borderRadius: '4px' }}></div>
                                </div>
                                <span style={{ fontSize: '11px', fontWeight: 'bold', color: '#1e293b', width: '45px', textAlign: 'right' }}>{pct}% ({item.value})</span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {/* AI Strategic Insights */}
                  {reportInsights && (
                    <div className="flex flex-col gap-6" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                      <div>
                        <h2 className="text-base font-bold text-slate-800 section-title">📉 3. Đánh giá thị trường tổng quan</h2>
                        <p className="text-sm leading-relaxed text-slate-700 text-justify bg-slate-50 p-4 rounded-xl border border-slate-100" style={{ backgroundColor: '#f8fafc', padding: '16px', borderRadius: '12px', border: '1px solid #f1f5f9', textAlign: 'justify', lineHeight: '1.6' }}>{renderSafeText(reportInsights.market_overview)}</p>
                      </div>
                      <div>
                        <h2 className="text-base font-bold text-slate-800 section-title">🔍 4. Cơ hội & Khoảng trống thị trường (Market Gaps)</h2>
                        <p className="text-sm leading-relaxed text-slate-700 text-justify bg-slate-50 p-4 rounded-xl border border-slate-100" style={{ backgroundColor: '#f8fafc', padding: '16px', borderRadius: '12px', border: '1px solid #f1f5f9', textAlign: 'justify', lineHeight: '1.6' }}>{renderSafeText(reportInsights.market_gaps)}</p>
                      </div>
                      <div>
                        <h2 className="text-base font-bold text-slate-800 section-title">🎯 5. Kịch bản tiếp cận Telesales đề xuất</h2>
                        <div className="text-sm leading-relaxed text-slate-700 bg-slate-50 p-4 rounded-xl border border-slate-100" style={{ backgroundColor: '#f8fafc', padding: '16px', borderRadius: '12px', border: '1px solid #f1f5f9', lineHeight: '1.6' }}>{renderSalesStrategy(reportInsights.sales_strategy)}</div>
                      </div>
                    </div>
                  )}
                  
                  {/* Lead Details Table */}
                  <div>
                    <h2 className="text-base font-bold text-slate-800 section-title">📋 6. Danh sách Lead chi tiết</h2>
                    <table className="w-full text-[10px] mt-3 border-collapse border border-slate-300" style={{ width: '100%', borderCollapse: 'collapse', marginTop: '15px' }}>
                      <thead>
                        <tr className="bg-slate-100 text-slate-700 font-bold border-b border-slate-300" style={{ backgroundColor: '#f1f5f9' }}>
                          <th className="border border-slate-300 px-2 py-2 text-left" style={{ border: '1px solid #cbd5e1', padding: '8px', textAlign: 'left' }}>Tên doanh nghiệp</th>
                          <th className="border border-slate-300 px-2 py-2 text-left" style={{ border: '1px solid #cbd5e1', padding: '8px', textAlign: 'left' }}>Điện thoại</th>
                          <th className="border border-slate-300 px-2 py-2 text-center" style={{ border: '1px solid #cbd5e1', padding: '8px', textAlign: 'center' }}>Đánh giá</th>
                          <th className="border border-slate-300 px-2 py-2 text-center" style={{ border: '1px solid #cbd5e1', padding: '8px', textAlign: 'center' }}>Số review</th>
                          <th className="border border-slate-300 px-2 py-2 text-center" style={{ border: '1px solid #cbd5e1', padding: '8px', textAlign: 'center' }}>Điểm AI</th>
                          <th className="border border-slate-300 px-2 py-2 text-left" style={{ border: '1px solid #cbd5e1', padding: '8px', textAlign: 'left' }}>Trang web</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.map((biz) => (
                          <tr key={biz.id} className="border-b border-slate-200">
                            <td className="border border-slate-300 px-2 py-2 font-semibold text-slate-900" style={{ border: '1px solid #cbd5e1', padding: '8px' }}>{biz.name}</td>
                            <td className="border border-slate-300 px-2 py-2 text-slate-700" style={{ border: '1px solid #cbd5e1', padding: '8px' }}>{biz.phone || "—"}</td>
                            <td className="border border-slate-300 px-2 py-2 text-center text-slate-800" style={{ border: '1px solid #cbd5e1', padding: '8px', textAlign: 'center' }}>{biz.rating ? `${biz.rating}/5` : "—"}</td>
                            <td className="border border-slate-300 px-2 py-2 text-center text-slate-800" style={{ border: '1px solid #cbd5e1', padding: '8px', textAlign: 'center' }}>{biz.review_count?.toLocaleString('vi-VN') || "0"}</td>
                            <td className="border border-slate-300 px-2 py-2 text-center font-bold text-emerald-600" style={{ border: '1px solid #cbd5e1', padding: '8px', textAlign: 'center', color: '#059669', fontWeight: 'bold' }}>{biz.ai_score || "—"}</td>
                            <td className="border border-slate-300 px-2 py-2 text-slate-600 break-all" style={{ border: '1px solid #cbd5e1', padding: '8px', wordBreak: 'break-all' }}>{biz.website || "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  
                  {/* Footer */}
                  <div className="text-center text-[10px] text-slate-400 mt-8 pt-4 border-t border-slate-100" style={{ textAlign: 'center', fontSize: '10px', color: '#94a3b8', marginTop: '32px', paddingTop: '16px', borderTop: '1px solid #e2e8f0' }}>
                    Báo cáo phân tích chuyên sâu được sinh tự động bởi giải pháp AI LeadSpyAI.
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}