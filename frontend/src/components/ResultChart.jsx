import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { compactNumber, formatCell, titleCase } from "../lib/format";

const SERIES = ["#1f8f88", "#2a3a6b", "#c98a12"];
const SLICES = ["#1f8f88", "#2a3a6b", "#c98a12", "#7a8bbf", "#5cc8c0", "#c0442e"];
const AXIS = { fontSize: 12, fill: "#5b6684" };

export default function ResultChart({ chart, columns, rows }) {
  if (!chart || chart.type === "none" || !rows?.length) return null;
  const data = rows.map((r) => Object.fromEntries(columns.map((c, i) => [c, r[i]])));
  const { x, y = [] } = chart;
  if (!columns.includes(x) || !y.length) return null;
  const tip = (v, name) => [formatCell(v, name), titleCase(name)];

  let body;
  if (chart.type === "pie") {
    body = (
      <PieChart>
        <Pie data={data} dataKey={y[0]} nameKey={x} innerRadius="45%" outerRadius="80%" paddingAngle={2}
          label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false}>
          {data.map((_, i) => <Cell key={i} fill={SLICES[i % SLICES.length]} />)}
        </Pie>
        <Tooltip formatter={tip} />
      </PieChart>
    );
  } else if (chart.type === "line") {
    body = (
      <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="#e4e8f0" vertical={false} />
        <XAxis dataKey={x} tick={AXIS} tickLine={false} axisLine={false} minTickGap={16} />
        <YAxis tick={AXIS} tickLine={false} axisLine={false} tickFormatter={compactNumber} width={56} />
        <Tooltip formatter={tip} />
        {y.length > 1 && <Legend formatter={titleCase} iconType="circle" wrapperStyle={{ fontSize: 13 }} />}
        {y.map((k, i) => <Line key={k} type="monotone" dataKey={k} stroke={SERIES[i]} strokeWidth={2.5} dot={{ r: 3 }} />)}
      </LineChart>
    );
  } else {
    const horizontal = data.length > 6 && String(data[0][x]).length > 8;
    body = (
      <BarChart data={data} layout={horizontal ? "vertical" : "horizontal"} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="#e4e8f0" vertical={horizontal} horizontal={!horizontal} />
        {horizontal ? (
          <>
            <XAxis type="number" tick={AXIS} tickLine={false} axisLine={false} tickFormatter={compactNumber} />
            <YAxis type="category" dataKey={x} tick={AXIS} tickLine={false} axisLine={false} width={130} />
          </>
        ) : (
          <>
            <XAxis dataKey={x} tick={AXIS} tickLine={false} axisLine={false} interval={0} />
            <YAxis tick={AXIS} tickLine={false} axisLine={false} tickFormatter={compactNumber} width={56} />
          </>
        )}
        <Tooltip formatter={tip} cursor={{ fill: "#f5f7fb" }} />
        {y.length > 1 && <Legend formatter={titleCase} iconType="circle" wrapperStyle={{ fontSize: 13 }} />}
        {y.map((k, i) => <Bar key={k} dataKey={k} fill={SERIES[i]} radius={horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0]} maxBarSize={48} />)}
      </BarChart>
    );
  }

  const height = chart.type !== "pie" && data.length > 6 && String(data[0][x]).length > 8 ? Math.max(260, data.length * 30) : 300;
  return (
    <figure>
      {chart.title && <figcaption className="mb-2 text-sm font-semibold text-ink-2">{chart.title}</figcaption>}
      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">{body}</ResponsiveContainer>
      </div>
    </figure>
  );
}
