/**
 * 运行统计卡：执行率 / 通过率 / 批次数 / 用例总数
 *
 * 统计口径（与后端一致）：
 * - 执行率 = 已执行 / 应执行
 * - 通过率 = 通过 / 已执行（待执行不计入分母）
 */

function clampPercent(value) {
  const num = Number(value) || 0
  return Math.max(0, Math.min(100, num))
}

export default function RunStatsCards({ stats, loading }) {
  const data = stats || {}
  const executionRate = clampPercent(data.execution_rate)
  const passRate = clampPercent(data.pass_rate)
  const days = data.days || 30

  return (
    <div className={`tr-stats${loading ? ' is-loading' : ''}`}>
      <div className="tr-stat-card">
        <span className="tr-stat-label">执行率</span>
        <strong className="tr-stat-value">{executionRate}%</strong>
        <span className="tr-stat-sub">
          已执行 {data.executed || 0} / 共 {data.total || 0}
        </span>
        <div className="tr-stat-bar">
          <span className="tr-stat-bar-fill rate" style={{ width: `${executionRate}%` }} />
        </div>
      </div>

      <div className="tr-stat-card">
        <span className="tr-stat-label">通过率</span>
        <strong className="tr-stat-value">{passRate}%</strong>
        <span className="tr-stat-sub">
          通过 {data.passed || 0} / 已执行 {data.executed || 0}
        </span>
        <div className="tr-stat-bar">
          <span className="tr-stat-bar-fill pass" style={{ width: `${passRate}%` }} />
        </div>
      </div>

      <div className="tr-stat-card">
        <span className="tr-stat-label">运行批次</span>
        <strong className="tr-stat-value">{data.run_count || 0}</strong>
        <span className="tr-stat-sub">近 {days} 天</span>
        <div className="tr-stat-chips">
          <span className="tr-chip result-pass">通过 {data.passed || 0}</span>
          <span className="tr-chip result-fail">失败 {data.failed || 0}</span>
        </div>
      </div>

      <div className="tr-stat-card">
        <span className="tr-stat-label">用例总数</span>
        <strong className="tr-stat-value">{data.total || 0}</strong>
        <span className="tr-stat-sub">已执行 {data.executed || 0}</span>
        <div className="tr-stat-chips">
          <span className="tr-chip result-open">待执行 {data.open || 0}</span>
          <span className="tr-chip result-blocked">阻塞 {data.blocked || 0}</span>
        </div>
      </div>
    </div>
  )
}
