import { useEffect, useState } from "react";

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

export default function DataTable({ data, selectedBusinessId, onSelectBusiness }) {
  const [sortKey,  setSortKey]  = useState("rating");
  const [sortDir,  setSortDir]  = useState("desc");
  const [page,     setPage]     = useState(1);
  const PER_PAGE = 10;

  useEffect(() => {
    setPage(1);
  }, [data]);

  if (!data?.length) return null;

  // Sort
  const sorted = [...data].sort((a, b) => {
    const av = a[sortKey] ?? (typeof a[sortKey] === "number" ? -Infinity : "");
    const bv = b[sortKey] ?? (typeof b[sortKey] === "number" ? -Infinity : "");
    if (av < bv) return sortDir === "asc" ? -1 :  1;
    if (av > bv) return sortDir === "asc" ?  1 : -1;
    return 0;
  });

  // Paginate
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

  return (
    <div
      className="animate-fade-up mt-10 rounded-xl overflow-hidden border border-border"
      style={{ animationDelay: "0.2s", opacity: 0 }}
    >
      {/* Table header bar */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-border bg-card">
        <span className="font-display font-bold text-sm tracking-wide text-white/80">
          Kết quả
          <span className="ml-2 font-mono text-pulse text-xs">
            [{data.length}]
          </span>
        </span>
        <span className="font-mono text-xs text-dim">
          trang {page}/{totalPages}
        </span>
      </div>

      {/* Scrollable table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm font-body border-collapse">
          <thead>
            <tr className="border-b border-border bg-lead/60">
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
                onClick={() => onSelectBusiness?.(biz.id)}
                style={{ animationDelay: `${i * 0.04}s` }}
                aria-selected={selectedBusinessId === biz.id}
              >
                {/* Name */}
                <td
                  className={`px-4 py-3 font-semibold whitespace-normal break-words align-top ${
                    selectedBusinessId === biz.id ? "text-pulse" : "text-white/90"
                  }`}
                >
                  {biz.name}
                </td>

                {/* Address */}
                <td className="px-4 py-3 text-dim whitespace-normal break-words align-top" title={biz.address}>
                  {biz.address || "—"}
                </td>

                {/* Phone */}
                <td className="px-4 py-3 font-mono text-xs text-white/70 whitespace-normal break-words align-top">
                  {biz.phone || "—"}
                </td>

                {/* Rating */}
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

                {/* Review count */}
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
                    >
                      {biz.website}
                    </a>
                  ) : (
                    <span className="text-dim text-xs">—</span>
                  )}
                </td>

                {/* AI Score */}
                <td className="px-4 py-3 font-mono font-bold text-pulse align-top">
                  {biz.ai_score != null ? biz.ai_score : "—"}
                </td>

                {/* AI Reason */}
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
    </div>
  );
}