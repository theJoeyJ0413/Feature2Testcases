import { useEffect, useRef, useState } from 'react'

/**
 * 测试用例页筛选栏
 *
 * 八个筛选维度：项目 / 需求 / 优先级 / 场景 / 维度 / 阶段 / 状态 / 关键字搜索 + 新建按钮
 * 依据 DESIGN.md「测试用例管理页面」：
 *   项目: [全部▼]  需求: [全部▼]  优先级: [全部▼]  场景: [全部▼]
 *   维度: [全部▼]  阶段: [全部▼]  状态: [全部▼]   搜索: [________]     [+ 新建用例]
 *
 * 联动：项目筛选变化后，需求下拉只显示该项目下的需求（加载逻辑在 view 中处理）
 */

// 场景选项（对应后端 scenario 字段的常用取值）
const SCENARIO_OPTIONS = ['正向', '边界', '异常']

// 维度选项（对应后端 dimension 字段的常用取值）
const DIMENSION_OPTIONS = ['功能', '性能', '安全', '易用性', '可靠性', '兼容性']

// 阶段选项（对应后端 stages 字段的枚举值，单选、包含匹配）
const STAGE_OPTIONS = ['冒烟', '通道', '灰度', '系统', '回归', '验收']

export default function FilterBar({
  filters,
  projects,
  features,
  onChange,
  onCreate,
}) {

  const [keyword, setKeyword] = useState(filters.keyword)
  const keywordTimerRef = useRef(null)

  // view 侧的keyword变化时，同步到输入框
  useEffect(() => {
    setKeyword(filters.keyword)
  }, [filters.keyword])

  // 卸载时清理防抖 timer，避免对已卸载组件触发 onChange
  useEffect(() => {
    return () => {
      if (keywordTimerRef.current) clearTimeout(keywordTimerRef.current)
    }
  }, [])

  // 单个筛选字段变化：由 view 统一处理「筛选变化 → 回到第一页重新加载」
  const handleChange = (key, value) => {
    onChange(key, value)
  }

  // 关键字搜索：输入防抖后更新 filters.keyword（避免每敲一个字就请求）
  const handleKeywordChange = (e) => {
    const value = e.target.value
    setKeyword(value)
    if (keywordTimerRef.current) clearTimeout(keywordTimerRef.current)
    keywordTimerRef.current = setTimeout(() => {
      onChange('keyword', value)
    }, 300)
  }

  return (
    <div className="filter-bar">
      <select
        className="filter-select"
        value={filters.project_id}
        onChange={(e) => handleChange('project_id', e.target.value)}
      >
        <option value="">项目：全部</option>
        {projects.map((p) => (
          <option key={p.id} value={String(p.id)}>
            {p.name}
          </option>
        ))}
      </select>

      <select
        className="filter-select"
        value={filters.feature_id}
        onChange={(e) => handleChange('feature_id', e.target.value)}
      >
        <option value="">需求：全部</option>
        {features.map((f) => (
          <option key={f.id} value={String(f.id)}>
            {f.feature_no} {f.title}
          </option>
        ))}
      </select>

      <select
        className="filter-select"
        value={filters.priority}
        onChange={(e) => handleChange('priority', e.target.value)}
      >
        <option value="">优先级：全部</option>
        <option value="P0">P0 核心</option>
        <option value="P1">P1 重要</option>
        <option value="P2">P2 一般</option>
        <option value="P3">P3 低</option>
      </select>

      <select
        className="filter-select"
        value={filters.scenario}
        onChange={(e) => handleChange('scenario', e.target.value)}
      >
        <option value="">场景：全部</option>
        {SCENARIO_OPTIONS.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>

      <select
        className="filter-select"
        value={filters.dimension}
        onChange={(e) => handleChange('dimension', e.target.value)}
      >
        <option value="">维度：全部</option>
        {DIMENSION_OPTIONS.map((d) => (
          <option key={d} value={d}>
            {d}
          </option>
        ))}
      </select>

      <select
        className="filter-select"
        value={filters.stage}
        onChange={(e) => handleChange('stage', e.target.value)}
      >
        <option value="">阶段：全部</option>
        {STAGE_OPTIONS.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>

      <select
        className="filter-select"
        value={filters.status}
        onChange={(e) => handleChange('status', e.target.value)}
      >
        <option value="">状态：全部</option>
        <option value="open">待执行</option>
        <option value="pass">通过</option>
        <option value="fail">失败</option>
        <option value="blocked">阻塞</option>
      </select>

      <input
        className="filter-keyword"
        type="text"
        placeholder="搜索用例标题…"
        value={keyword}
        onChange={handleKeywordChange}
      />

      <button className="btn primary" onClick={onCreate}>
        新建用例
      </button>
    </div>
  )
}
