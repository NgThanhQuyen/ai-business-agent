import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, ScatterChart, Scatter,
  CartesianGrid,
} from "recharts";

import BusinessMap from "./BusinessMap";

// ── Palette ───────────────────────────────────────────────────────────────────
const COLORS = ["#00FF94", "#A3E635", "#FACC15", "#F87171", "#818CF8"];

const tooltipStyle = {
  backgroundColor: "#16213E",
  border: "1px solid #2A2A4A",
  borderRadius: "8px",
  fontFamily: "'DM Mono', monospace",
  fontSize: "12px",
  color: "#E8E6F0",
};

// ── Sub-components ────────────────────────────────────────────────────────────
const ChartCard = ({ title, subtitle, children }) => (
  <div className="rounded-xl border border-border bg-card p-5">
    <p className="font-display font-bold text-sm text-white/80 mb-0.5">{title}</p>
    {subtitle && <p className="font-mono text-xs text-dim mb-4">{subtitle}</p>}
    {children}
  </div>
);

const StatCard = ({ label, value, accent = "#00FF94" }) => (
  <div
    className="rounded-xl border bg-card p-5 flex flex-col gap-1"
    style={{ borderColor: `${accent}30` }}
  >
    <span className="font-mono text-xs text-dim uppercase tracking-widest">{label}</span>
    <span
      className="font-display font-extrabold text-3xl"
      style={{ color: accent }}
    >
      {value}
    </span>
  </div>
);

// ── Helpers ───────────────────────────────────────────────────────────────────
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
    .map(b => ({ name: b.name.length > 20 ? b.name.slice(0, 18) + "…" : b.name, reviews: b.review_count }));
}

function buildScatter(data) {
  return data
    .filter(b => b.rating && b.review_count)
    .map(b => ({ x: b.rating, y: b.review_count, name: b.name }));
}

// ── Main Component ────────────────────────────────────────────────────────────
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
      {/* Section label */}
      <div className="flex items-center gap-3">
        <span className="font-display font-bold text-base text-white/80 tracking-wide">
          Bảng điều khiển phân tích
        </span>
        <div className="flex-1 h-px bg-border" />
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Tổng doanh nghiệp" value={data.length} accent="#00FF94" />
        <StatCard label="Điểm trung bình"   value={avgRating}         accent="#A3E635" />
        <StatCard label="Tổng lượt đánh giá" value={totalReviews}      accent="#FACC15" />
        <StatCard label="Có trang web"      value={`${websitePct}%`}  accent="#818CF8" />
      </div>

      {/* Charts row 1 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

        {/* Rating distribution bar chart */}
        <ChartCard title="Phân bố điểm đánh giá" subtitle="Số doanh nghiệp theo từng mức điểm">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={ratingDist} barCategoryGap="35%">
              <CartesianGrid strokeDasharray="3 3" stroke="#2A2A4A" vertical={false} />
              <XAxis dataKey="name" tick={{ fill: "#6B7280", fontSize: 11, fontFamily: "DM Mono" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "#6B7280", fontSize: 11, fontFamily: "DM Mono" }} axisLine={false} tickLine={false} allowDecimals={false} />
              <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "#00FF9410" }} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {ratingDist.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Review volume pie chart */}
        <ChartCard title="Phân bố số lượng review" subtitle="Doanh nghiệp được nhóm theo số review">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={reviewBuckets}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={85}
                paddingAngle={3}
              >
                {reviewBuckets.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} stroke="transparent" />
                ))}
              </Pie>
              <Tooltip contentStyle={tooltipStyle} />
              <Legend
                iconType="circle"
                iconSize={8}
                wrapperStyle={{ fontFamily: "DM Mono", fontSize: "11px", color: "#6B7280" }}
              />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Charts row 2 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

        {/* Top 10 by reviews */}
        <ChartCard title="Top 10 theo số review" subtitle="Doanh nghiệp có nhiều review nhất">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={top10} layout="vertical" barCategoryGap="30%">
              <CartesianGrid strokeDasharray="3 3" stroke="#2A2A4A" horizontal={false} />
              <XAxis type="number" tick={{ fill: "#6B7280", fontSize: 10, fontFamily: "DM Mono" }} axisLine={false} tickLine={false} />
              <YAxis dataKey="name" type="category" width={110}
                tick={{ fill: "#9CA3AF", fontSize: 10, fontFamily: "DM Mono" }}
                axisLine={false} tickLine={false} />
              <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "#00FF9410" }} />
              <Bar dataKey="reviews" fill="#00FF94" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Rating vs Reviews scatter */}
        <ChartCard title="Tương quan điểm và số review" subtitle="Xác định nhóm nổi bật: điểm cao + nhiều review">
          <ResponsiveContainer width="100%" height={240}>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" stroke="#2A2A4A" />
              <XAxis
                dataKey="x" name="Đánh giá" type="number"
                domain={[1, 5]} tickCount={5}
                tick={{ fill: "#6B7280", fontSize: 10, fontFamily: "DM Mono" }}
                axisLine={false} tickLine={false}
                label={{ value: "Đánh giá", position: "insideBottom", offset: -2, fill: "#6B7280", fontSize: 10 }}
              />
              <YAxis
                dataKey="y" name="Số review" type="number"
                tick={{ fill: "#6B7280", fontSize: 10, fontFamily: "DM Mono" }}
                axisLine={false} tickLine={false}
              />
              <Tooltip
                contentStyle={tooltipStyle}
                cursor={{ strokeDasharray: "3 3" }}
                content={({ payload }) =>
                  payload?.length ? (
                    <div style={tooltipStyle} className="px-3 py-2 text-xs">
                      <p className="text-pulse mb-1">{payload[0]?.payload?.name}</p>
                      <p>Đánh giá: {payload[0]?.payload?.x}</p>
                      <p>Số review: {payload[0]?.payload?.y?.toLocaleString()}</p>
                    </div>
                  ) : null
                }
              />
              <Scatter data={scatterData} fill="#00FF94" fillOpacity={0.7} r={5} />
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