import TestcaseRow from './TestcaseRow'

/**
 * 测试用例表格
 *
 * 列：编号 / 模块 / 优先级 / 场景 / 维度 / 阶段 / 标题 / 关联需求 / 状态 / 操作
 * 点击行展开详情：前置条件 / 操作步骤 / 预期结果（见 TestcaseRow.jsx）
 */
export default function TestcaseTable({
  items,
  expandedIds,
  updatingIds,
  onToggleRow,
  onStatusChange,
  onEdit,
  onDelete,
}) {
  return (
    <table className="testcase-table">
      <thead>
        <tr>
          <th className="col-no">编号</th>
          <th className="col-module">模块</th>
          <th className="col-priority">优先级</th>
          <th className="col-scenario">场景</th>
          <th className="col-dimension">维度</th>
          <th className="col-stage">阶段</th>
          <th className="col-title">标题</th>
          <th className="col-feature">关联需求</th>
          <th className="col-status">状态</th>
          <th className="col-actions">操作</th>
        </tr>
      </thead>
      <tbody>
        {items.map((t) => (
          <TestcaseRow
            key={t.id}
            testcase={t}
            expanded={expandedIds.includes(t.id)}
            updating={updatingIds.includes(t.id)}
            onToggle={() => onToggleRow(t.id)}
            onStatusChange={() => onStatusChange(t)}
            onEdit={() => onEdit(t)}
            onDelete={() => onDelete(t)}
          />
        ))}
      </tbody>
    </table>
  )
}
