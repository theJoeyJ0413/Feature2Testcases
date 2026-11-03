/**
 * 需求卡片：头部始终显示，点击切换展开/收起
 * 头部：模块徽标 + 编号 FEATURE-001 + 标题 + 优先级徽标 + 状态徽标
 * 展开后：描述、功能性（逐条）、非功能性（按维度分组）、底部操作行
 */

// 需求状态中文标签（对应后端 STATUS_VALUES: open / analyzed / closed）
const STATUS_LABELS = {
  open: '未分析',
  analyzed: '已分析',
  closed: '已关闭',
}

// 需求优先级中文标签（对应后端 PRIORITY_VALUES: P0 / P1 / P2 / P3）
const PRIORITY_LABELS = {
  P0: 'P0 核心',
  P1: 'P1 重要',
  P2: 'P2 一般',
  P3: 'P3 低',
}

// 非功能性维度中文标签（键对应 Agent 输出的 JSON 字段名）
const NON_FUNCTIONAL_LABELS = {
  performance: '性能',
  security: '安全',
  usability: '易用性',
  reliability: '可靠性',
  compatibility: '兼容性',
}

export default function FeatureCard({
  feature,
  expanded,
  onToggle,
  onEdit,
  onDelete,
  onGenerate,
  generating,
  onGoTestcases,
}) {
  return (
    <div className={`feature-card ${expanded ? 'expanded' : ''}`}>
      {/* 卡片头：点击切换展开/收起 */}
      <div className="feature-card-head" onClick={onToggle}>
        <div className="feature-head-left">
          {feature.module && <span className="feature-module">{feature.module}</span>}
          <span className="feature-no">{feature.feature_no}</span>
          <span className="feature-title">{feature.title}</span>
          <span className={`feature-priority priority-${feature.priority || 'P2'}`}>
            {PRIORITY_LABELS[feature.priority] || feature.priority || 'P2'}
          </span>
          <span className={`feature-status status-${feature.status}`}>
            {STATUS_LABELS[feature.status] || feature.status}
          </span>
        </div>
        <span className="feature-toggle">{expanded ? '收起 ▲' : '展开 ▼'}</span>
      </div>

      {/* 卡片体：仅展开时渲染 */}
      {expanded && (
        <div className="feature-card-body">
          {/* 描述 */}
          <p className="feature-desc">{feature.description || '暂无描述'}</p>

          {/* 功能性需求：逐条展示 */}
          <div className="feature-section">
            <h4 className="feature-section-title">功能性</h4>
            {(feature.functional || []).length === 0 ? (
              <p className="hint">暂无功能性需求</p>
            ) : (
              <ul className="functional-list">
                {feature.functional.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            )}
          </div>

          {/* 非功能性需求：按维度分组，无内容的维度不展示 */}
          <div className="feature-section">
            <h4 className="feature-section-title">非功能性</h4>
            {Object.entries(feature.non_functional || {}).filter(
              ([, items]) => Array.isArray(items) && items.length > 0
            ).length === 0 ? (
              <p className="hint">暂无非功能性需求</p>
            ) : (
              <div className="nf-groups">
                {Object.entries(feature.non_functional || {})
                  .filter(([, items]) => Array.isArray(items) && items.length > 0)
                  .map(([key, items]) => (
                    <div className="nf-group" key={key}>
                      <span className="nf-label">{NON_FUNCTIONAL_LABELS[key] || key}</span>
                      <ul className="nf-list">
                        {items.map((item, idx) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  ))}
              </div>
            )}
          </div>

          {/* 底部操作行 */}
          <div className="feature-card-actions">
            <button className="btn small" onClick={onGoTestcases}>
              关联用例（{feature.testcases_count ?? 0}）
            </button>
            <button className="btn small" onClick={onEdit}>
              编辑
            </button>
            <button className="btn small" onClick={onGenerate} disabled={generating}>
              {generating ? '生成中...' : '生成测试用例'}
            </button>
            <button className="btn small danger" onClick={onDelete}>
              删除
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
