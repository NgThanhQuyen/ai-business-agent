import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, ScatterChart, Scatter,
  CartesianGrid,
} from "recharts";

import BusinessMap from "./BusinessMap";

// ── Bảng màu ───────────────────────────────────────────────────────────────────
const COLORS = ["#00FF94", "#A3E635", "#FACC15", "#818CF8", "#F87171"];
const GRADIENTS = [
  "url(#gradGreen)",
  "url(#gradLime)",
  "url(#gradYellow)",
  "url(#gradIndigo)",
  "url(#gradRed)"
];

const tooltipStyle = {
  backgroundColor: "rgba(15, 23, 42, 0.95)",
  border: "1px solid rgba(255, 255, 255, 0.08)",
  borderRadius: "12px",
  fontFamily: "'DM Sans', sans-serif",
  fontSize: "12px",
  color: "#E8E6F0",
  boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.5)",
  backdropFilter: "blur(6px)",
};

const tooltipItemStyle = {
  color: "#E8E6F0",
};

const tooltipLabelStyle = {
  color: "#FFFFFF",
  fontWeight: "bold",
};

// ── Thành phần con ────────────────────────────────────────────────────────────
const ChartCard = ({ title, subtitle, children }) => (
  <div className="relative overflow-hidden rounded-2xl border border-white/5 bg-slate-900/40 backdrop-blur-md p-6 shadow-xl transition-all duration-300 hover:border-white/10 hover:shadow-2xl hover:shadow-black/20 group">
    {/* Hiệu ứng hào quang nền khi di chuột qua */}
    <div className="pointer-events-none absolute -right-20 -top-20 w-48 h-48 rounded-full bg-[#00FF94]/5 blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
    
    <p className="font-display font-bold text-base text-white tracking-wide mb-0.5">{title}</p>
    {subtitle && <p className="font-body text-xs text-slate-400 mb-6">{subtitle}</p>}
    {children}
  </div>
);

const StatCard = ({ label, value, icon, accent = "#00FF94" }) => (
  <div
    className="relative overflow-hidden rounded-2xl border bg-slate-900/40 backdrop-blur-md p-6 flex flex-col gap-2 transition-all duration-300 hover:border-white/15 hover:shadow-[0_8px_30px_rgba(0,255,148,0.06)] hover:-translate-y-0.5 group"
    style={{ borderColor: `${accent}20` }}
  >
    {/* Thanh gradient trên cùng làm điểm nhấn */}
    <div
      className="absolute top-0 left-0 w-full h-[3px] opacity-70 group-hover:opacity-100 transition-opacity duration-300"
      style={{ background: `linear-gradient(90deg, ${accent}, transparent)` }}
    />
    
    <div className="flex items-center justify-between text-dim">
      <span className="font-mono text-[10px] tracking-[0.15em] uppercase text-white/50">{label}</span>
      <div style={{ color: accent }} className="opacity-80 group-hover:opacity-100 transition-all duration-300">
        {icon}
      </div>
    </div>
    
    <div className="flex items-baseline gap-1 mt-1">
      <span
        className="font-display font-extrabold text-3xl sm:text-4xl tracking-tight text-white group-hover:scale-[1.02] transition-transform duration-300 origin-left"
        style={{ textShadow: `0 0 20px ${accent}25` }}
      >
        {value}
      </span>
    </div>
  </div>
);

// ── Hàm trợ giúp ───────────────────────────────────────────────────────────────────
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

function buildTop10(data) {
  return [...data]
    .filter(b => b.review_count)
    .sort((a, b) => b.review_count - a.review_count)
    .slice(0, 10)
    .map(b => ({ name: b.name.length > 22 ? b.name.slice(0, 20) + "…" : b.name, reviews: b.review_count }));
}

function buildScatter(data) {
  return data
    .filter(b => b.rating && b.review_count)
    .map(b => ({ x: b.rating, y: b.review_count, name: b.name }));
}

// ── Thành phần chính ────────────────────────────────────────────────────────────
export default function Dashboard({ data, selectedBusinessId, onSelectBusiness }) {
  if (!data?.length) return null;

  const rated      = data.filter(b => b.rating);
  const avgRating  = rated.length
    ? (rated.reduce((s, b) => s + b.rating, 0) / rated.length).toFixed(2)
    : "Chưa có";
  const totalReviews = data
    .reduce((s, b) => s + (b.review_count || 0), 0)
    .toLocaleString();
  const withWebsite = data.filter(b => b.website).length;
  const websitePct  = Math.round((withWebsite / data.length) * 100);

  const ratingDist   = buildRatingDist(data);
  const reviewBuckets = buildReviewBuckets(data);
  const top10        = buildTop10(data);
  const scatterData  = buildScatter(data);

  return (
    <div
      className="animate-fade-up mt-10 space-y-6"
      style={{ animationDelay: "0.35s", opacity: 0 }}
    >
      {/* Nhãn phân đoạn */}
      <div className="flex items-center gap-3">
        <span className="font-display font-bold text-base text-white/80 tracking-wide">
          Bảng điều khiển phân tích
        </span>
        <div className="flex-1 h-px bg-border" />
      </div>

      {/* Thẻ chỉ số thống kê */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard
          label="Tổng doanh nghiệp"
          value={data.length}
          accent="#00FF94"
          icon={
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
              <path d="m2 7 4.41-4.41A2 2 0 0 1 7.83 2h8.34a2 2 0 0 1 1.42.59L22 7" />
              <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
              <path d="M15 22v-4a2 2 0 0 0-2-2h-2a2 2 0 0 0-2 2v4" />
              <path d="M2 7h20" />
            </svg>
          }
        />
        <StatCard
          label="Điểm trung bình"
          value={avgRating}
          accent="#A3E635"
          icon={
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
            </svg>
          }
        />
        <StatCard
          label="Tổng lượt đánh giá"
          value={totalReviews}
          accent="#FACC15"
          icon={
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          }
        />
        <StatCard
          label="Có trang web"
          value={`${websitePct}%`}
          accent="#818CF8"
          icon={
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
              <circle cx="12" cy="12" r="10" />
              <line x1="2" y1="12" x2="22" y2="12" />
              <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
            </svg>
          }
        />
      </div>

      {/* Hàng biểu đồ thứ nhất */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

        {/* Biểu đồ cột phân bổ điểm đánh giá */}
        <ChartCard title="Phân bổ điểm đánh giá" subtitle="Số doanh nghiệp theo từng mức điểm">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={ratingDist} barCategoryGap="30%">
              <defs>
                <linearGradient id="gradGreen" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#00FF94" stopOpacity={0.9} />
                  <stop offset="100%" stopColor="#00FF94" stopOpacity={0.15} />
                </linearGradient>
                <linearGradient id="gradLime" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#A3E635" stopOpacity={0.9} />
                  <stop offset="100%" stopColor="#A3E635" stopOpacity={0.15} />
                </linearGradient>
                <linearGradient id="gradYellow" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#FACC15" stopOpacity={0.9} />
                  <stop offset="100%" stopColor="#FACC15" stopOpacity={0.15} />
                </linearGradient>
                <linearGradient id="gradIndigo" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#818CF8" stopOpacity={0.9} />
                  <stop offset="100%" stopColor="#818CF8" stopOpacity={0.15} />
                </linearGradient>
                <linearGradient id="gradRed" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#F87171" stopOpacity={0.9} />
                  <stop offset="100%" stopColor="#F87171" stopOpacity={0.15} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#2A2A4A" opacity={0.4} vertical={false} />
              <XAxis dataKey="name" tick={{ fill: "#9CA3AF", fontSize: 11, fontFamily: "DM Mono" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "#9CA3AF", fontSize: 11, fontFamily: "DM Mono" }} axisLine={false} tickLine={false} allowDecimals={false} />
              <Tooltip contentStyle={tooltipStyle} itemStyle={tooltipItemStyle} labelStyle={tooltipLabelStyle} cursor={{ fill: "rgba(255, 255, 255, 0.03)", radius: 6 }} />
              <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                {ratingDist.map((_, i) => (
                  <Cell key={i} fill={GRADIENTS[i % GRADIENTS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Biểu đồ tròn phân bổ số lượng review */}
        <ChartCard title="Phân bổ số lượng review" subtitle="Doanh nghiệp được nhóm theo số review">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={reviewBuckets}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="43%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={4}
              >
                {reviewBuckets.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} stroke="transparent" />
                ))}
              </Pie>
              {/* Tóm tắt ở tâm biểu đồ tròn (donut) */}
              <text x="50%" y="43%" textAnchor="middle" dominantBaseline="middle">
                <tspan x="50%" dy="-2" fill="#9CA3AF" fontSize="10" fontFamily="DM Sans" fontWeight="600" letterSpacing="0.15em">TỔNG LEAD</tspan>
                <tspan x="50%" dy="22" fill="#FFFFFF" fontSize="24" fontFamily="DM Sans" fontWeight="800">{data.length}</tspan>
              </text>
              <Tooltip contentStyle={tooltipStyle} itemStyle={tooltipItemStyle} labelStyle={tooltipLabelStyle} />
              <Legend
                iconType="circle"
                iconSize={8}
                wrapperStyle={{ fontFamily: "DM Sans", fontSize: "11px", color: "#9CA3AF", paddingTop: "10px" }}
              />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Hàng biểu đồ thứ hai */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

        {/* Top 10 theo số review */}
        <ChartCard title="Top 10 theo số review" subtitle="Doanh nghiệp có nhiều review nhất">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={top10} layout="vertical" barCategoryGap="30%">
              <defs>
                <linearGradient id="gradHorizontal" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#4f46e5" stopOpacity={0.15} />
                  <stop offset="60%" stopColor="#818CF8" stopOpacity={0.7} />
                  <stop offset="100%" stopColor="#00FF94" stopOpacity={1} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#2A2A4A" opacity={0.4} horizontal={false} />
              <XAxis type="number" tick={{ fill: "#9CA3AF", fontSize: 10, fontFamily: "DM Mono" }} axisLine={false} tickLine={false} />
              <YAxis dataKey="name" type="category" width={140}
                tick={{ fill: "#D1D5DB", fontSize: 10, fontFamily: "DM Sans" }}
                axisLine={false} tickLine={false} />
              <Tooltip contentStyle={tooltipStyle} itemStyle={tooltipItemStyle} labelStyle={tooltipLabelStyle} cursor={{ fill: "rgba(255, 255, 255, 0.03)", radius: 6 }} />
              <Bar dataKey="reviews" fill="url(#gradHorizontal)" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Biểu đồ phân tán giữa số review và điểm đánh giá */}
        <ChartCard title="Tương quan điểm và số review" subtitle="Xác định nhóm nổi bật: điểm cao + nhiều review">
          <ResponsiveContainer width="100%" height={240}>
            <ScatterChart>
              <defs>
                <linearGradient id="gradScatter" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#00FF94" stopOpacity={1} />
                  <stop offset="100%" stopColor="#A3E635" stopOpacity={0.7} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#2A2A4A" opacity={0.4} />
              <XAxis
                dataKey="x" name="Đánh giá" type="number"
                domain={["auto", "auto"]}
                tick={{ fill: "#9CA3AF", fontSize: 10, fontFamily: "DM Mono" }}
                axisLine={false} tickLine={false}
                label={{ value: "Đánh giá", position: "insideBottom", offset: -2, fill: "#9CA3AF", fontSize: 10 }}
              />
              <YAxis
                dataKey="y" name="Số review" type="number"
                tick={{ fill: "#9CA3AF", fontSize: 10, fontFamily: "DM Mono" }}
                axisLine={false} tickLine={false}
              />
              <Tooltip
                contentStyle={tooltipStyle}
                cursor={{ strokeDasharray: "3 3", stroke: "rgba(255, 255, 255, 0.2)" }}
                content={({ payload }) =>
                  payload?.length ? (
                    <div style={tooltipStyle} className="px-3 py-2 text-xs">
                      <p className="text-pulse mb-1 font-semibold">{payload[0]?.payload?.name}</p>
                      <p>Đánh giá: <span className="text-white font-mono">{payload[0]?.payload?.x}</span></p>
                      <p>Số review: <span className="text-white font-mono">{payload[0]?.payload?.y?.toLocaleString()}</span></p>
                    </div>
                  ) : null
                }
              />
              <Scatter data={scatterData} fill="url(#gradScatter)" r={7} />
            </ScatterChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <BusinessMap
        data={data}
        selectedBusinessId={selectedBusinessId}
        onSelectBusiness={onSelectBusiness}
      />
    </div>
  );
}