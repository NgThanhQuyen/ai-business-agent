export default function AIInsights({ insights }) {
  if (!insights || insights.length === 0) return null;

  return (
    <div className="mt-8 rounded-xl overflow-hidden border border-border bg-card p-6 animate-fade-up">
      <h2 className="font-display font-bold text-lg text-white mb-4 flex items-center gap-2">
        <span role="img" aria-label="brain">🧠</span> Phân tích từ AI
      </h2>
      <ul className="space-y-3">
        {insights.map((insight, idx) => (
          <li key={idx} className="flex gap-3 text-sm text-dim leading-relaxed">
            <span className="text-pulse font-bold mt-0.5">•</span>
            <span>{insight}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
