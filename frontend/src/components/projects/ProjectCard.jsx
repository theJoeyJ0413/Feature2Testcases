/**
 * 项目卡片：展示项目名称、修改日期、来源、状态
 *
 * 点击卡片任意位置 → 打开编辑弹窗
 * 编辑/删除按钮 → stopPropagation 阻止冒泡，不触发卡片点击
 */

const SOURCE_LABELS = { agent: 'Agent 生成', manual: '手动创建' }
const STATUS_LABELS = { active: '进行中', archived: '已归档' }

function formatDate(iso) {
  if (!iso) return '-'
  const d = new Date(iso)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export default function ProjectCard({project, onEdit, onDelete}) {
    return (
        <div className="project-card" onClick={onEdit}>
            <div className="project-card-head">
                <h3 className="project-name">{project.name}</h3>
                <span className={`project-status status-${project.status}`}>
                    {STATUS_LABELS[project.status] || project.status}
                </span>
            </div>

            <div className="project-meta">
                <span className="meta-item">
                    <span className="meta-label">来源</span>
                    <span className={`project-source source-${project.source}`}>
                        {SOURCE_LABELS[project.source] || project.source}
                    </span>
                </span>
                <span className="meta-item">
                    <span className="meta-label">修改日期</span>
                    {formatDate(project.updated_at)}
                </span>
            </div>

            <div className="project-stats">
                <span className="stat-item">
                    <span className="stat-num">{project.feature_count ?? 0}</span>个需求
                </span>
                <span className="stat-item">
                    <span className="stat-num">{project.testcase_count ?? 0}</span>条测试用例
                </span>
            </div>

            <div className="project-card-actions">
                <button className="btn small" onClick={(e) => { e.stopPropagation(); onEdit(); }}>
                    编辑
                </button>
                <button className="btn small" onClick={(e) => { e.stopPropagation(); onDelete(); }}>
                    删除
                </button>
            </div>
        </div>
    )
}