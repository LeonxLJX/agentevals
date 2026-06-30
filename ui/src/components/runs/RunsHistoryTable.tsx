import React from 'react';
import { css } from '@emotion/react';
import { Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { Run } from '../../lib/types';
import {
  STATUS_COLORS,
  evalSetGroup,
  formatDuration,
  formatTimestamp,
  passRate,
  runDurationMs,
} from './runHistory';

interface RunsHistoryTableProps {
  runs: Run[];
}

export const RunsHistoryTable: React.FC<RunsHistoryTableProps> = ({ runs }) => {
  const rows = [...runs].sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt));

  const columns: ColumnsType<Run> = [
    {
      title: 'When',
      dataIndex: 'createdAt',
      key: 'when',
      render: (value: string) => <span css={monoStyle}>{formatTimestamp(value)}</span>,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: Run['status']) => (
        <span css={statusStyle}>
          <span css={dotStyle} style={{ background: STATUS_COLORS[status] }} />
          {status}
        </span>
      ),
    },
    {
      title: 'Eval set',
      key: 'evalSet',
      render: (_: unknown, run: Run) => (
        <span css={evalSetCellStyle}>{evalSetGroup(run).label}</span>
      ),
    },
    {
      title: 'Traces',
      key: 'traces',
      align: 'right',
      render: (_: unknown, run: Run) => (
        <span css={monoStyle}>{run.summary?.trace_count ?? '-'}</span>
      ),
    },
    {
      title: 'Results',
      key: 'results',
      render: (_: unknown, run: Run) => {
        const counts = run.summary?.result_counts;
        if (!counts) return <span css={mutedStyle}>-</span>;
        return (
          <span css={countsStyle}>
            <span style={{ color: 'var(--status-success)' }}>{counts.passed}P</span>
            <span style={{ color: 'var(--status-failure)' }}>{counts.failed}F</span>
            {counts.errored > 0 && (
              <span style={{ color: 'var(--status-warning)' }}>{counts.errored}E</span>
            )}
            {counts.skipped > 0 && (
              <span style={{ color: 'var(--text-tertiary)' }}>{counts.skipped}S</span>
            )}
          </span>
        );
      },
    },
    {
      title: 'Pass rate',
      key: 'passRate',
      render: (_: unknown, run: Run) => {
        const rate = passRate(run);
        if (rate === null) return <span css={mutedStyle}>-</span>;
        const pct = Math.round(rate * 100);
        return (
          <div css={barCellStyle}>
            <div css={barTrackStyle}>
              <div
                css={barFillStyle}
                style={{
                  width: `${pct}%`,
                  background: rate >= 0.5 ? 'var(--status-success)' : 'var(--status-failure)',
                }}
              />
            </div>
            <span css={monoStyle}>{pct}%</span>
          </div>
        );
      },
    },
    {
      title: 'Duration',
      key: 'duration',
      align: 'right',
      render: (_: unknown, run: Run) => (
        <span css={monoStyle}>{formatDuration(runDurationMs(run))}</span>
      ),
    },
    {
      title: 'Models',
      key: 'models',
      render: (_: unknown, run: Run) => {
        const models = run.summary?.performance_metrics?.models;
        if (!Array.isArray(models) || models.length === 0) return <span css={mutedStyle}>-</span>;
        return <span css={modelsStyle}>{models.join(', ')}</span>;
      },
    },
  ];

  return (
    <div css={tableStyle}>
      <Table<Run>
        rowKey="runId"
        columns={columns}
        dataSource={rows}
        pagination={{ pageSize: 10, hideOnSinglePage: true }}
        size="small"
      />
    </div>
  );
};

const tableStyle = css`
  .ant-table {
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: 8px;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  }

  .ant-table-thead > tr > th {
    background: var(--bg-elevated);
    color: var(--text-primary);
    font-weight: 600;
    border-bottom: 2px solid var(--border-default);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 12px 16px;
  }

  .ant-table-tbody > tr > td {
    background: var(--bg-surface);
    color: var(--text-secondary);
    border-bottom: 1px solid var(--border-subtle);
    padding: 12px 16px;
  }

  .ant-table-tbody > tr:hover > td {
    background: var(--bg-elevated);
  }

  .ant-pagination .ant-pagination-item a,
  .ant-pagination .ant-pagination-item-link {
    color: var(--text-secondary);
  }

  .ant-pagination .ant-pagination-item-active {
    background: var(--bg-elevated);
    border-color: var(--accent-primary);
  }

  .ant-pagination .ant-pagination-item-active a {
    color: var(--accent-primary);
  }
`;

const monoStyle = css`
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  color: var(--text-secondary);
`;

const statusStyle = css`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  text-transform: capitalize;
  font-size: 0.8125rem;
  color: var(--text-primary);
`;

const dotStyle = css`
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
`;

const evalSetCellStyle = css`
  color: var(--text-primary);
  font-size: 0.8125rem;
`;

const countsStyle = css`
  display: inline-flex;
  gap: 8px;
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  font-weight: 600;
`;

const barCellStyle = css`
  display: flex;
  align-items: center;
  gap: 8px;
`;

const barTrackStyle = css`
  width: 64px;
  height: 6px;
  border-radius: 3px;
  background: var(--bg-elevated);
  overflow: hidden;
`;

const barFillStyle = css`
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
`;

const mutedStyle = css`
  color: var(--text-tertiary);
`;

const modelsStyle = css`
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--text-tertiary);
`;
