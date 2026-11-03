import { useEffect, useRef, useState } from 'react'

import { MODE_LABELS, RUN_STATUS_LABELS, formatRunTime } from './meta'

/**
 * 左侧运行批次列表
 *
 * - 按批次号搜索（输入防抖 300ms）
 * - 列表项展示：批次号 / 模式 / 状态 / 项目 / 执行进度
 * - 底部提供上一页 / 下一页
 */
export default function RunListSidebar({
  runs,
  selectedId,
  keyword,
  onKeywordChange,
  total,
  page,
  pageSize,
  onPageChange,
  loading,
}) {
  const [text, setText] = useState(keyword)
  const timerRef = useRef(null)

  useEffect(() => {
    setText(keyword)
  }, [keyword])

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [])

  const handleKeywordChange = (e) => {
    const value = e.target.value
    setText(value)
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => onKeywordChange(value), 300)
  }

  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  return (
    <aside className="tr-sidebar">
      <div className="tr-sidebar-head">
        <div className="tr-sidebar-title">
          <h2>运行批次</h2>
          <span className="tr-count">{total}</span>
        </div>
        <input
          className="tr-search"
          type="text"
          placeholder="搜索批次号…"
          value={text}
          onChange={handleKeywordChange}
        />
      </div>

      <div className="tr-run-list">
        {loading && runs.length === 0 ? (
          <p className="tr-sidebar-empty">加载中…</p>
        ) : runs.length === 0 ? (
          <p className="tr-sidebar-empty">
            {keyword ? '没有匹配的批次' : '暂无运行批次，点击右上角「新建运行」开始'}
          </p>
        ) : (
          runs.map((run) => {
            const rate = Math.max(0, Math.min(100, Number(run.execution_rate) || 0))
            return (
              <button
                key={run.id}
                type="button"
                className={`tr-run-item${run.id === selectedId ? ' selected' : ''}`}
                onClick={() => onSelect(run.id)}
              >
                <div className="tr-run-item-top">
                  <span className="tr-run-no">{run.run_no}</span>
                  <span className={`tr-badge status-${run.status}`}>
                    {RUN_STATUS_LABELS[run.status] || run.status}
                  </span>
                </div>

                <div className="tr-run-item-meta">
                  <span className="tr-mode">{MODE_LABELS[run.mode] || run.mode}</span>
                  <span className="tr-project-name">{run.project_name}</span>
                </div>

                <div className="tr-run-item-foot">
                  <span>执行 {run.executed || 0}/{run.total || 0}</span>
                  <span>{rate}%</span>
                </div>
                <div className="tr-mini-bar">
                  <span style={{ width: `${rate}%` }} />
                </div>
                <span className="tr-run-time">{formatRunTime(run.created_at)}</span>
              </button>
            )
          })
        )}
      </div>

      <div className="tr-sidebar-foot">
        <span className="hint">
          共 {total} 条 · {page}/{totalPages}
        </span>
        <div className="tr-page-btns">
          <button
            type="button"
            className="btn small"
            disabled={page <= 1 || loading}
            onClick={() => onPageChange(page - 1)}
          >
            上一页
          </button>
          <button
            type="button"
            className="btn small"
            disabled={page >= totalPages || loading}
            onClick={() => onPageChange(page + 1)}
          >
            下一页
          </button>
        </div>
      </div>
    </aside>
  )
}
