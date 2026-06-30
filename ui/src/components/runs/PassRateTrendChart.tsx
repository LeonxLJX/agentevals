import React from 'react';
import { css } from '@emotion/react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js';
import type { Run } from '../../lib/types';
import { CHART_COLORS, formatTimestamp, passRate } from './runHistory';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

interface PassRateTrendChartProps {
  runs: Run[];
}

export const PassRateTrendChart: React.FC<PassRateTrendChartProps> = ({ runs }) => {
  const points = runs
    .map(run => ({ run, rate: passRate(run) }))
    .filter((p): p is { run: Run; rate: number } => p.rate !== null);

  if (points.length === 0) {
    return (
      <div css={cardStyle}>
        <h3>Pass rate over time</h3>
        <p css={emptyStyle}>No decided (pass/fail) results yet in this eval.</p>
      </div>
    );
  }

  const data = {
    labels: points.map(p => formatTimestamp(p.run.createdAt)),
    datasets: [
      {
        label: 'Pass rate',
        data: points.map(p => Math.round(p.rate * 1000) / 10),
        borderColor: CHART_COLORS.passRate,
        backgroundColor: CHART_COLORS.passRateFill,
        fill: true,
        tension: 0.25,
        pointRadius: 3,
        pointHoverRadius: 5,
        borderWidth: 2,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.9)',
        titleColor: '#fff',
        bodyColor: '#fff',
        padding: 12,
        cornerRadius: 6,
        callbacks: {
          label: (ctx: { parsed: { y: number } }) => `Pass rate: ${ctx.parsed.y}%`,
        },
      },
    },
    scales: {
      y: {
        min: 0,
        max: 100,
        ticks: {
          color: CHART_COLORS.text,
          font: { size: 12 },
          callback: (value: string | number) => `${value}%`,
        },
        grid: { color: CHART_COLORS.grid },
      },
      x: {
        ticks: { color: CHART_COLORS.text, font: { size: 11 }, maxRotation: 0, autoSkip: true },
        grid: { color: CHART_COLORS.grid },
      },
    },
  };

  return (
    <div css={cardStyle}>
      <h3>Pass rate over time</h3>
      <div css={chartWrapperStyle}>
        <Line data={data} options={options} />
      </div>
    </div>
  );
};

const cardStyle = css`
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  padding: 20px;

  h3 {
    margin: 0 0 16px 0;
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-primary);
  }
`;

const chartWrapperStyle = css`
  height: 300px;
  position: relative;
`;

const emptyStyle = css`
  color: var(--text-tertiary);
  font-size: 0.875rem;
  margin: 0;
`;
