import { useEffect, useState } from 'react'

import { RESULT_LABELS, RESULT_OPTIONS, formatRunTime } from './meta'

/**
 * 单条运行用例：快照详情 + 结果记录 + 实际结果/备注
 *
 * 结果按钮四态切换；实际结果与备注在失焦时保存（有变化才请求）。
 * 批次结束后所有记录控件禁用。
 */
export default function RunItemCard({
  item,
  disabled,
  updating,
  onResult,
  onFieldSave,
}) {
  const [actual, setActual] = useState(item.actual || '')
  const [remark, setRemark] = useState(item.remark || '')

  useEffect(() => {
    setActual(item.actual || '')
    setRemark(item.remark || '')
  }, [item.actual, item.remark])

  const locked = disabled || updating

  const handleBlur = (field, value, original) => {
    if (locked) return
    const next = value.trim()
    if (next !== (original || '').trim()) onFieldSave(field, next)
  }

  return (
    <article className={`tr-item${item.result !== 'open' ? ` is-${item.result}` : ''}`}>
      <header className="tr-item-top">
        <span className="tr-item-no">{item.testcase_no}</span>
        <span className="tr-item-title">{item.title}</span>
        <span className={`tr-priority priority-${item.priority || 'P2'}`}>
          {item.priority || 'P2'}
        </span>
        {item.scenario && <span className="tr-tag">{item.scenario}</span>}
        {item.dimension && <span className="tr-tag">{item.dimension}</span>}
        {(item.stages || []).map((s) => (
          <span key={s} className="tr-tag stage">
            {s}
          </span>
        ))}
      </header>

      <div className="tr-item-detail">
        <div className="tr-detail-line">
          <span className="tr-detail-label">前置条件</span>
          <span className="tr-detail-text">{item.precondition || '无'}</span>
        </div>

        <div className="tr-detail-line">
          <span className="tr-detail-label">操作步骤</span>
          {(item.steps || []).length === 0 ? (
            <span className="tr-detail-text">无</span>
          ) : (
            <ol className="tr-detail-steps">
              {item.steps.map((step, idx) => (
                <li key={idx}>{step}</li>
              ))}
            </ol>
          )}
        </div>

        <div className="tr-detail-line">
          <span className="tr-detail-label">预期结果</span>
          <span className="tr-detail-text">{item.expected || '无'}</span>
        </div>
      </div>

      <div className="tr-item-actions">
        <span className="tr-result-label">结果</span>
        <div className="tr-result-group">
          {RESULT_OPTIONS.map((value) => (
            <button
              key={value}
              type="button"
              className={`tr-result-btn result-${value}${item.result === value ? ' active' : ''}`}
              disabled={locked}
              onClick={() => {
                if (item.result !== value) onResult(value)
              }}
            >
              {RESULT_LABELS[value]}
            </button>
          ))}
        </div>
        {item.executed_at && (
          <span className="tr-executed-at">执行于 {formatRunTime(item.executed_at)}</span>
        )}
      </div>

      <div className="tr-item-notes">
        <label className="tr-note">
          <span>实际结果</span>
          <textarea
            rows={2}
            value={actual}
            placeholder="记录实际执行情况"
            disabled={locked}
            onChange={(e) => setActual(e.target.value)}
            onBlur={() => handleBlur('actual', actual, item.actual)}
          />
        </label>
        <label className="tr-note">
          <span>备注</span>
          <input
            type="text"
            value={remark}
            placeholder="补充说明（可选）"
            disabled={locked}
            onChange={(e) => setRemark(e.target.value)}
            onBlur={() => handleBlur('remark', remark, item.remark)}
          />
        </label>
      </div>
    </article>
  )
}
