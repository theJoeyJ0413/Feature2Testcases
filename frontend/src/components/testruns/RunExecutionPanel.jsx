import { useEffect, useMemo, useState } from 'react'

import RunItemCard from './RunItemCard'
import { MODE_LABELS, RUN_STATUS_LABELS } from './meta'

/**
 * 右侧执行工作台
 *
 * - 批次头部：编号 / 模式 / 状态 / 范围 / 优先级 / 阶段 / 统计
 * - 工具条：全部展开收起、仅看未执行、结束运行
 * - 用例按需求分组，逐条记录结果；结束后锁定
 */
export default function RunExecutionPanel({
  detail,
  loading,
  updatingItemId,
  finishing,
  onSelectResult,
  onFieldSave,
  onFinish,
}) {
  const [collapsedKeys, setCollapsedKeys] = useState([])
  const [onlyUnexecuted, setOnlyUnexecuted] = useState(false)

  useEffect(() => {
    setCollapsedKeys([])
    setOnlyUnexecuted(false)
  }, [detail?.id])

  const groups = useMemo(() => {
    if (!detail?.items) return []
    const map = new Map()
    detail.items.forEach((item) => {
      const key =
        item.feature_id != null
          ? `f-${item.feature_id}`
          : `x-${item.feature_no || 'orphan'}`
      if (!map.has(key)) {
        map.set(key, {
          key,
          featureNo: item.feature_no || '未关联需求',
          featureTitle: item.feature_title || '',
          items: [],
        })
      }
      map.get(key).items.push(item)
    })
    return Array.from(map.values())
  }, [detail])

  if (loading && !detail) {
    return (
      <section className="tr-panel">
        <div className="tr-panel-empty">加载运行详情…</div>
      </section>
    )
  }

  if (!detail) {
    return (
      <section className="tr-panel">
        <div className="tr-panel-empty">
          从左侧选择一个运行批次，或点击右上角「新建运行」开始
        </div>
      </section>
    )
  }

  const running = detail.status === 'running'
  const scope = detail.scope || {}
  const scopeText =
    scope.type === 'features'
      ? `指定 ${(scope.feature_ids || []).length} 个需求`
      : '全部用例'

  const visibleGroups = groups
    .map((group) => ({
      ...group,
      visibleItems: onlyUnexecuted
        ? group.items.filter((item) => item.result === 'open')
        : group.items,
    }))
    .filter((group) => group.visibleItems.length > 0)

  const allCollapsed =
    visibleGroups.length > 0 &&
    visibleGroups.every((group) => collapsedKeys.includes(group.key))

  const toggleGroup = (key) => {
    setCollapsedKeys((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    )
  }

  const toggleAll = () => {
    if (allCollapsed) {
      setCollapsedKeys([])
    } else {
      setCollapsedKeys(visibleGroups.map((group) => group.key))
    }
  }

  const rate = Math.max(0, Math.min(100, Number(detail.execution_rate) || 0))

  return (
    <section className="tr-panel">
      <header className="tr-run-head">
        <div className="tr-run-title">
          <div className="tr-run-title-line">
            <h2>{detail.run_no}</h2>
            <span className="tr-mode-badge">{MODE_LABELS[detail.mode] || detail.mode}</span>
            <span className={`tr-badge status-${detail.status}`}>
              {RUN_STATUS_LABELS[detail.status] || detail.status}
            </span>
          </div>
          <p className="tr-run-meta">
            项目：{detail.project_name} · 范围：{scopeText}
            {detail.priority ? ` · 优先级：${detail.priority}` : ''}
            {detail.stage ? ` · 阶段：${detail.stage}` : ''}
          </p>
        </div>

        <div className="tr-run-actions">
          <button type="button" className="btn small" onClick={toggleAll}>
            {allCollapsed ? '全部展开' : '全部收起'}
          </button>
          <label className="tr-check">
            <input
              type="checkbox"
              checked={onlyUnexecuted}
              onChange={(e) => setOnlyUnexecuted(e.target.checked)}
            />
            仅看未执行
          </label>
          {running && (
            <button
              type="button"
              className="btn primary small"
              onClick={onFinish}
              disabled={finishing}
            >
              {finishing ? '结束中…' : '结束运行'}
            </button>
          )}
        </div>
      </header>

      <div className="tr-run-progress">
        <div className="tr-progress-line">
          <span>
            执行率 <strong>{detail.execution_rate}%</strong> · 已执行{' '}
            {detail.executed}/{detail.total}
          </span>
          <span className="tr-progress-chips">
            <span className="tr-chip result-pass">通过 {detail.passed}</span>
            <span className="tr-chip result-fail">失败 {detail.failed}</span>
            <span className="tr-chip result-blocked">阻塞 {detail.blocked}</span>
            <span className="tr-chip result-open">待执行 {detail.open}</span>
          </span>
        </div>
        <div className="tr-progress-bar">
          <span style={{ width: `${rate}%` }} />
        </div>
      </div>

      <div className="tr-groups">
        {visibleGroups.length === 0 ? (
          <div className="tr-panel-empty small">
            {onlyUnexecuted ? '该批次已没有待执行用例' : '该批次暂无用例快照'}
          </div>
        ) : (
          visibleGroups.map((group) => {
            const collapsed = collapsedKeys.includes(group.key)
            const executed = group.items.filter((item) => item.result !== 'open').length
            return (
              <div className="tr-group" key={group.key}>
                <button
                  type="button"
                  className="tr-group-head"
                  onClick={() => toggleGroup(group.key)}
                >
                  <span className="tr-group-title">
                    <span className="tr-chevron">{collapsed ? '▶' : '▼'}</span>
                    <span className="tr-feature-no">{group.featureNo}</span>
                    <span>{group.featureTitle}</span>
                  </span>
                  <span className="tr-group-count">
                    {executed}/{group.items.length} 已执行
                  </span>
                </button>

                {!collapsed &&
                  group.visibleItems.map((item) => (
                    <RunItemCard
                      key={item.id}
                      item={item}
                      disabled={!running}
                      updating={updatingItemId === item.id}
                      onResult={(result) => onSelectResult(item, result)}
                      onFieldSave={(field, value) => onFieldSave(item, field, value)}
                    />
                  ))}
              </div>
            )
          })
        )}
      </div>
    </section>
  )
}
