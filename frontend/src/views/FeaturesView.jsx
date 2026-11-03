import { useCallback, useEffect, useState } from 'react'
import {useNavigate} from 'react-router-dom'

import { listProjects, listFeatures, deleteFeature, generateFeatureTestcases } from '../apis'

import ProjectListSidebar from '../components/features/ProjectListSidebar'
import FeatureCard from '../components/features/FeatureCard'
import FeatureEditModal from '../components/features/FeatureEditModal'

import '../css/FeaturesView.css'

/**
 * 需求管理页面：左项目列表 + 右项目详情与需求列表（左右分栏）
 *
 * 布局依据 DESIGN.md「需求管理页面」：
 * - 左侧（约30%）：项目列表，搜索 + 选中，只做浏览与选择
 * - 右侧（约70%）：选中项目详情（只读）+ 需求列表
 *
 * 组件拆分 → components/features/：
 * - ProjectListSidebar.jsx   左侧项目列表（搜索 + 列表）
 * - FeatureCard.jsx          需求卡片（折叠展开、功能性/非功能性展示）
 * - FeatureEditModal.jsx     新建/编辑需求弹窗
 *
 * 逻辑待补（见文中 TODO 注释）：
 * 1. 左侧项目搜索过滤
 * 2. 关联用例数跳转用例页、生成测试用例
 */

export default function FeaturesView() {
  // ==================== 状态 ====================
  const [projects, setProjects] = useState([])              // 项目列表（含 feature_count）
  const [keyword, setKeyword] = useState('')                // 左侧项目搜索关键字
  const [selectedProject, setSelectedProject] = useState(null) // 当前选中的项目
  const [features, setFeatures] = useState([])              // 选中项目下的需求列表
  const [expandedIds, setExpandedIds] = useState([])        // 展开的需求卡片 id 列表
  const [generatingId, setGeneratingId] = useState(null)    // 正在生成测试用例的需求 id  
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [toast, setToast] = useState(null)          // 轻提示（生成完成等），3 秒自动消失

  // 弹窗开关
  const [creating, setCreating] = useState(false)   // 新建需求弹窗
  const [editing, setEditing] = useState(null)      // 编辑需求弹窗（正在编辑的需求）
  const [deleting, setDeleting] = useState(null)    // 待删除的需求

  // 跳转
  const navigate = useNavigate()

  // toast 自动消失：新 toast 覆盖时会重置计时器，卸载时清理
  useEffect(() => {
    if (!toast) return
    const timer = setTimeout(() => setToast(null), 3000)
    return () => clearTimeout(timer)
  }, [toast])

  // loadFeatures(project_id)：加载需求列表，默认展开第一张卡片
  const loadFeatures = useCallback(async (project_id) => {
    setLoading(true)
    setError('')
    try {
      const data = await listFeatures(project_id)
      setFeatures(data.items || [])
      setExpandedIds(data.items?.length?[data.items[0].id] : [])
    } catch (e) {
      setError(e?.response?.data?.detail || '获取需求列表失败')
    } finally {
      setLoading(false)
    }
  }, [])

  // 进入页面时加载项目列表，默认选中第一个项目
  useEffect(() => {
    const init = async () => {
      setLoading(true)
      setError('')
      try {
        const data = await listProjects({ page: 1, page_size: 100 })
        const items = data.items || []
        setProjects(items)
        if (items.length > 0) {
          setSelectedProject(items[0])
          loadFeatures(items[0].id)
        }
      } catch (e) {
        setError(e?.response?.data?.detail || '获取项目列表失败')
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [loadFeatures])

  // handleSelectProject(project)：切换选中项目，重新加载需求
  const handleSelectProject = (project) => {
    setSelectedProject(project)
    setExpandedIds([])
    loadFeatures(project.id)
  }

  // 单张卡片展开/收起
  const toggleExpand = (id) => {
    if (expandedIds.includes(id)) {
      setExpandedIds(expandedIds.filter((i) => i !== id))
    } else {
      setExpandedIds([...expandedIds, id])
    }
  }

  // 全部展开（expandedIds = 所有 id）/ 全部收起（= []）
  const handleToggleAll = () => {
    setExpandedIds(expandedIds.length === features.length ? [] : features.map((f) => f.id))
  }

  // 新建/编辑保存成功后关闭弹窗并刷新需求列表
  const handleSave = (created) => {
    setCreating(false)
    setEditing(null)
    if (created) {
      setProjects((prev) => 
        prev.map( (p) => 
          p.id === selectedProject.id
            ? { ...p, feature_count: (p.feature_count ?? 0) + 1 }
            : p
        ))
    }
    loadFeatures(selectedProject.id)
  }
  // 删除确认后刷新需求列表
  const handleDelete = async () => {
    if (!deleting) return
    try {
      await deleteFeature(selectedProject.id, deleting.id)
      setDeleting(null)
      setProjects((prev) => 
        prev.map( (p) => 
          p.id === selectedProject.id
            ? { ...p, feature_count: Math.max(0, (p.feature_count ?? 0) - 1) }
            : p
        ))
      loadFeatures(selectedProject.id)
    } catch (e) {
      setError(e?.response?.data?.detail || '删除需求失败')
      setDeleting(null)
    }
  }

  const handleGenerate = async(feature) => {
    if (generatingId) return
    setGeneratingId(feature.id)
    setError('')
    try {
      const res = await generateFeatureTestcases(selectedProject.id, feature.id)
      loadFeatures(selectedProject.id)
      setToast({
        message: `生成完成：新增/更新 ${res.saved} 条用例` + (res.skipped ? `，跳过 ${res.skipped} 条` : '')
      })
    } catch (e) {
      setError(e?.response?.data?.detail || '生成测试用例失败')
    } finally {
      setGeneratingId(null)
    }
  }

  const handleGoTestcases = (feature) => {
    navigate(`/testcases?project_id=${selectedProject.id}&feature_id=${feature.id}`)
  }

  const filteredProjects = projects.filter((p) => 
    p.name.toLowerCase().includes(keyword.trim().toLowerCase())
  )

  return (
    <div className="features-page">
      {/* ===== 左侧：项目列表 ===== */}
      <ProjectListSidebar
        projects={filteredProjects}
        keyword={keyword}
        onKeywordChange={setKeyword}
        selectedId={selectedProject?.id}
        onSelect={handleSelectProject}
      />

      {/* ===== 右侧：项目详情 + 需求列表 ===== */}
      <section className="features-main">
        {!selectedProject ? (
          <div className="features-placeholder">请选择左侧项目查看需求</div>
        ) : (
          <>
            {/* 项目头部（只读，编辑在项目管理页完成） */}
            <header className="project-header">
              <div className="project-header-top">
                <h2 className="project-header-name">{selectedProject.name}</h2>
                <span className={`feature-status status-${selectedProject.status}`}>
                  {selectedProject.status === 'active' ? '进行中' : '已归档'}
                </span>
              </div>
              <div className="project-header-meta">
                <span>来源：{selectedProject.source === 'agent' ? 'Agent 生成' : '手动创建'}</span>
                <span>需求数：{features.length}</span>
              </div>
              {selectedProject.description && (
                <p className="project-header-desc">{selectedProject.description}</p>
              )}
            </header>

            {/* 需求工具条 */}
            <div className="features-toolbar">
              <span className="features-count">需求（共 {features.length} 条）</span>
              <div className="features-toolbar-actions">
                <button className="btn small" onClick={handleToggleAll}>
                  {expandedIds.length === features.length && features.length > 0
                    ? '全部收起'
                    : '全部展开'}
                </button>
                <button className="btn primary small" onClick={() => setCreating(true)}>
                  新建需求
                </button>
              </div>
            </div>

            {error && <p className="modal-error">{error}</p>}

            {/* 需求卡片列表 */}
            {loading ? (
              <p className="hint">加载中…</p>
            ) : features.length === 0 ? (
              <div className="features-placeholder">暂无需求，点击「新建需求」开始</div>
            ) : (
              <div className="feature-list">
                {features.map((f) => (
                  <FeatureCard
                    key={f.id}
                    feature={f}
                    expanded={expandedIds.includes(f.id)}
                    onToggle={() => toggleExpand(f.id)}
                    onEdit={() => setEditing(f)}
                    onDelete={() => setDeleting(f)}
                    onGenerate={() => handleGenerate(f)}
                    generating={generatingId === f.id}
                    onGoTestcases={() => handleGoTestcases(f)}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </section>

      {/* ===== 弹窗 ===== */}
      {editing && (
        <FeatureEditModal
          project={selectedProject}
          feature={editing}
          onSaved={() => handleSave(false)}
          onClose={() => setEditing(null)}
        />
      )}
      {creating && (
        <FeatureEditModal
          project={selectedProject}
          feature={null}
          onSaved={() => handleSave(true)}
          onClose={() => setCreating(false)}
        />
      )}
      {deleting && (
        <ConfirmModal 
          title="删除需求"
          message={`确定要删除需求「${deleting.title}」吗？删除后不可恢复。`}
          onCancel={() => setDeleting(null)}
          onConfirm={handleDelete}
        />
      )}

      {/* ===== 轻提示 ===== */}
      {toast && <div className="toast">{toast.message}</div>}
    </div>

    
  )
}

/** 本页内联的通用确认弹窗 */
function ConfirmModal({ title, message, onCancel, onConfirm }) {
  return (
    <div className="modal-mask" onClick={onCancel}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>{title}</h2>
        <p className="confirm-message">{message}</p>
        <div className="modal-actions">
          <button className="btn" onClick={onCancel}>取消</button>
          <button className="btn danger" onClick={onConfirm}>删除</button>
        </div>
      </div>
    </div>
  )
}
