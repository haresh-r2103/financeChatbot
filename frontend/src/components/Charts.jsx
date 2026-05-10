import {
  ResponsiveContainer,
  ComposedChart,
  BarChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  Area,
  AreaChart,
} from "recharts";
import "./Charts.css";

const fmt = (v) =>
  v >= 1_000_000
    ? `$${(v / 1_000_000).toFixed(1)}M`
    : v >= 1_000
    ? `$${(v / 1_000).toFixed(0)}K`
    : `$${v}`;

const COLORS = {
  revenue: "#6366f1",
  expenses: "#f43f5e",
  profit: "#4ade80",
  fitted: "#a78bfa",
};

function StatCard({ label, value, sub, color }) {
  return (
    <div className="stat-card" style={{ borderTopColor: color }}>
      <p className="stat-label">{label}</p>
      <p className="stat-value">{value}</p>
      {sub && <p className="stat-sub">{sub}</p>}
    </div>
  );
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="tooltip">
      <p className="tooltip-label">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}: {fmt(p.value)}
        </p>
      ))}
    </div>
  );
};

export default function Charts({ data }) {
  const months = data.monthly_trends?.months ?? [];
  const totals = data.totals ?? {};
  const anomalies = data.anomalies ?? {};

  // Chart data
  const chartData = months.map((m) => ({
    name: m.month.slice(0, 3),
    Revenue: m.revenue,
    Expenses: m.expenses,
    Profit: m.profit,
    Margin: m.profit_margin_pct,
  }));

  const profitMarginData = months.map((m) => ({
    name: m.month.slice(0, 3),
    Margin: m.profit_margin_pct,
    MoM: m.revenue_mom_pct,
  }));

  return (
    <div className="charts-root">
      {/* KPI row */}
      <div className="stat-row">
        <StatCard
          label="Total Revenue"
          value={fmt(totals.revenue?.total ?? 0)}
          sub={`avg ${fmt(totals.revenue?.mean ?? 0)} / mo`}
          color={COLORS.revenue}
        />
        <StatCard
          label="Total Expenses"
          value={fmt(totals.expenses?.total ?? 0)}
          sub={`avg ${fmt(totals.expenses?.mean ?? 0)} / mo`}
          color={COLORS.expenses}
        />
        <StatCard
          label="Net Profit"
          value={fmt(totals.profit?.total ?? 0)}
          sub={`avg ${fmt(totals.profit?.mean ?? 0)} / mo`}
          color={COLORS.profit}
        />
        <StatCard
          label="Profit Margin"
          value={`${totals.profit_margin_pct ?? 0}%`}
          sub={`expense ratio ${totals.expense_ratio_pct ?? 0}%`}
          color="#f59e0b"
        />
      </div>

      {/* Revenue vs Expenses bar chart */}
      <div className="card">
        <p className="card-title">Revenue vs Expenses</p>
        <ResponsiveContainer width="100%" height={260}>
          <ComposedChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2a45" />
            <XAxis dataKey="name" tick={{ fill: "#64748b", fontSize: 12 }} />
            <YAxis tickFormatter={fmt} tick={{ fill: "#64748b", fontSize: 12 }} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: 13, color: "#94a3b8" }} />
            <Bar dataKey="Revenue" fill={COLORS.revenue} radius={[4, 4, 0, 0]} />
            <Bar dataKey="Expenses" fill={COLORS.expenses} radius={[4, 4, 0, 0]} />
            <Line
              type="monotone"
              dataKey="Profit"
              stroke={COLORS.profit}
              strokeWidth={2}
              dot={{ r: 4, fill: COLORS.profit }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Profit area chart */}
      <div className="card">
        <p className="card-title">Profit Trend</p>
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="profitGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={COLORS.profit} stopOpacity={0.25} />
                <stop offset="95%" stopColor={COLORS.profit} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2a45" />
            <XAxis dataKey="name" tick={{ fill: "#64748b", fontSize: 12 }} />
            <YAxis tickFormatter={fmt} tick={{ fill: "#64748b", fontSize: 12 }} />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine y={0} stroke="#334155" strokeDasharray="4 4" />
            <Area
              type="monotone"
              dataKey="Profit"
              stroke={COLORS.profit}
              strokeWidth={2}
              fill="url(#profitGrad)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Profit margin % line */}
      <div className="card">
        <p className="card-title">Profit Margin % (monthly)</p>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={profitMarginData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="marginGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2a45" />
            <XAxis dataKey="name" tick={{ fill: "#64748b", fontSize: 12 }} />
            <YAxis unit="%" tick={{ fill: "#64748b", fontSize: 12 }} />
            <Tooltip formatter={(v) => `${v}%`} contentStyle={{ background: "#1e2433", border: "1px solid #2d3f6b", borderRadius: 8 }} />
            <Area
              type="monotone"
              dataKey="Margin"
              stroke="#f59e0b"
              strokeWidth={2}
              fill="url(#marginGrad)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Anomalies */}
      {anomalies.total_anomalies_found > 0 && (
        <div className="card anomaly-card">
          <p className="card-title">⚠ Anomalies detected — {anomalies.total_anomalies_found} total</p>
          <div className="anomaly-list">
            {Object.entries(anomalies.by_metric ?? {}).map(([metric, items]) =>
              items.map((a, i) => (
                <div key={`${metric}-${i}`} className={`anomaly-item ${a.direction}`}>
                  <span className="anomaly-metric">{metric}</span>
                  <span className="anomaly-row">{a.row}</span>
                  <span className="anomaly-value">{fmt(a.value)}</span>
                  <span className={`anomaly-dir ${a.direction}`}>
                    {a.direction === "high" ? "▲ HIGH" : "▼ LOW"}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
