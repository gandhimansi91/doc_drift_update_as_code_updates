import React from 'react';
import { RadialBarChart, RadialBar, PolarAngleAxis } from 'recharts';

interface Props {
  score: number; // 0-100
}

function getFreshColor(score: number) {
  if (score >= 75) return '#34d399';
  if (score >= 50) return '#fbbf24';
  if (score >= 25) return '#f97316';
  return '#f87171';
}

export const FreshnessGauge: React.FC<Props> = ({ score }) => {
  const color = getFreshColor(score);
  const data = [{ value: score, fill: color }];

  return (
    <div className="relative flex items-center justify-center" style={{ width: 180, height: 180 }}>
      <RadialBarChart
        width={180}
        height={180}
        cx={90}
        cy={90}
        innerRadius={60}
        outerRadius={84}
        barSize={14}
        data={data}
        startAngle={220}
        endAngle={-40}
      >
        <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
        <RadialBar
          background={{ fill: 'rgba(255,255,255,0.05)' }}
          dataKey="value"
          angleAxisId={0}
          cornerRadius={7}
        />
      </RadialBarChart>
      {/* Centre overlay */}
      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
        <span className="font-mono text-3xl font-bold" style={{ color }}>
          {score.toFixed(0)}
        </span>
        <span className="text-xs tracking-widest text-white/40 uppercase mt-0.5">Health</span>
      </div>
    </div>
  );
};
