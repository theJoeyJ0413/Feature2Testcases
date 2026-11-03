/**
 * 需求页左侧项目列表：搜索框 + 项目列表（名称 + 需求数徽标）
 *
 * 只做浏览与选择，项目的新建/编辑/删除在项目管理页完成
 */

export default function ProjectListSidebar({
  projects,
  keyword,
  onKeywordChange,
  selectedId,
  onSelect,
}) {
  return (
    <aside className="features-sidebar">
      <div className="features-search">
        <input
          type="text"
          placeholder="搜索项目…"
          value={keyword}
          onChange={(e) => onKeywordChange(e.target.value)}
        />
      </div>

      {projects.length === 0 ? (
        <p className="hint">暂无项目</p>
      ) : (
        <ul className="project-list">
          {projects.map((p) => (
            <li
              key={p.id}
              className={selectedId === p.id ? 'project-item active' : 'project-item'}
              onClick={() => onSelect(p)}
            >
              <span className="project-item-name">{p.name}</span>
              <span className="project-item-count">{p.feature_count ?? 0}</span>
            </li>
          ))}
        </ul>
      )}
    </aside>
  )
}
