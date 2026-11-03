/**
 * 测试用例行：主行 + 可展开的详情行
 *
 * 主行：编号 + 模块徽标 + 优先级徽标 + 场景 + 维度 + 标题 + 关联需求
 *       + 状态徽标（点击直接切换）+ 操作（编辑/删除）
 * 详情行：前置条件 / 操作步骤 / 预期结果
 */

// 用例状态中文标签（对应后端 STATUS_VALUES: open / pass / fail / blocked）
const STATUS_LABELS = {
  open: '待执行',
  pass: '通过',
  fail: '失败',
  blocked: '阻塞',
}

export default function TestcaseRow({
  testcase,
  expanded,
  updating,
  onToggle,
  onStatusChange,
  onEdit,
  onDelete,
}) {
  return (
    <>
      {/* 主行：点击切换展开/收起 */}
      <tr className="testcase-row" onClick={onToggle}>
        <td className="col-no">{testcase.testcase_no}</td>

        <td className="col-module">
          {testcase.module && <span className="tc-module">{testcase.module}</span>}
        </td>

        <td className="col-priority">
          <span className={`tc-priority priority-${testcase.priority || 'P2'}`}>
            {testcase.priority || 'P2'}
          </span>
        </td>

        <td className="col-scenario">{testcase.scenario || '—'}</td>
        <td className="col-dimension">{testcase.dimension || '—'}</td>

        <td className="col-stage">
          {/* 阶段为多值列表：逐个渲染小徽标，空值显示 — */}
          {(testcase.stages || []).length === 0
            ? '—'
            : testcase.stages.map((s) => (
                <span key={s} className="tc-stage">{s}</span>
              ))}
        </td>

        <td className="col-title">
          <span className="tc-title">{testcase.title}</span>
          <span className="tc-toggle">{expanded ? '▲' : '▼'}</span>
        </td>

        <td className="col-feature">{testcase.feature_ref || '—'}</td>

        <td className="col-status">
          {/* 状态徽标：点击切换（四态循环，逻辑在 view 的 handleStatusChange 中）；更新中禁用防连点 */}
          <span
            className={`tc-status status-${testcase.status}${updating ? ' updating' : ''}`}
            title="点击切换状态"
            onClick={(e) => {
              e.stopPropagation()
              if (!updating) onStatusChange()
            }}
          >
            {STATUS_LABELS[testcase.status] || testcase.status}
          </span>
        </td>

        <td className="col-actions">
          <button
            className="btn small"
            onClick={(e) => {
              e.stopPropagation()
              onEdit()
            }}
          >
            编辑
          </button>
          <button
            className="btn small danger"
            onClick={(e) => {
              e.stopPropagation()
              onDelete()
            }}
          >
            删除
          </button>
        </td>
      </tr>

      {/* 详情行：前置条件 / 操作步骤 / 预期结果 */}
      {expanded && (
        <tr className="testcase-detail-row">
          <td colSpan={10}>
            <div className="testcase-detail">
              <div className="detail-item">
                <span className="detail-label">前置条件</span>
                <p className="detail-text">{testcase.precondition || '无'}</p>
              </div>

              <div className="detail-item">
                <span className="detail-label">操作步骤</span>
                {(testcase.steps || []).length === 0 ? (
                  <p className="detail-text">无</p>
                ) : (
                  <ol className="detail-steps">
                    {testcase.steps.map((step, idx) => (
                      <li key={idx}>{step}</li>
                    ))}
                  </ol>
                )}
              </div>

              <div className="detail-item">
                <span className="detail-label">预期结果</span>
                <p className="detail-text">{testcase.expected || '无'}</p>
              </div>

              <div className="detail-item">
                <span className="detail-label">实际结果</span>
                <p className="detail-text">{testcase.actual || '无'}</p>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}
