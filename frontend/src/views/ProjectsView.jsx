import { useCallback, useEffect, useState, useRef } from 'react'

import { deleteProject, listProjects } from '../apis'

import '../css/ProjectsView.css'
import ProjectCard from '../components/projects/ProjectCard'
import ProjectEditModal from '../components/projects/ProjectEditModal'

/**
 * 项目管理页面：卡片列表 + 编辑/新建弹窗 + 删除确认
 *
 * 卡片展示 → components/projects/ProjectCard.jsx
 * 编辑/新建弹窗 → components/projects/ProjectEditModal.jsx
 */

const PAGE_SIZE = 12

export default function ProjectsView() {
  const [projects, setProjects] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)

  const [creating, setCreating] = useState(false) //新建弹窗的开关
  const [editing, setEditing] = useState(null) //编辑弹窗的开关，正在编辑的项目
  const [deleting, setDeleting] = useState(null) //待删除的项目

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const loadProjects = useCallback(async (p) => {
    setLoading(true)
    setError('')
    try{
      const data = await listProjects({page: p, page_size: PAGE_SIZE})
      setProjects(data.items || [])
      setTotal(data.total || 0)
    }catch (e){
      setError(e?.response?.data?.detail || '获取项目列表失败')
    }finally{
      setLoading(false)
    }
  }, [])
  // 进入页面时/翻页时加载
  useEffect(() => {
    loadProjects(page)
  }, [loadProjects, page])

  // create/edit保存成功后，关闭弹窗、刷新当前页面
  const handleSave = () => {
    setEditing(null)
    setCreating(false)
    loadProjects(page)
  }
  // delete确认后，关闭弹窗、刷新当前页面
  const [notice, setNotice] = useState('')
  const handleDelete = async () => {
    if (!deleting) return
    try{
      const res = await deleteProject(deleting.id)
      setDeleting(null)
      showNotice(
        `已删除项目，同时删除${res.deleted_features}个需求和${res.deleted_testcases}个测试用例` +
        (res.unlinked_history ? `，${res.unlinked_history} 条历史记录已恢复为未保存` : '')
      )
      // 当前页被删空且不是第一页 → 回退一页
      if (projects.length === 1 && page > 1) setPage(page - 1)
      else loadProjects(page)
    }catch(e){
      setError(e?.response?.data?.detail || '删除项目失败')
      setDeleting(null)
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  // notice定时器
  const noticeTimerRef = useRef(null)
  const showNotice = (msg) => {
    setNotice(msg)
    if (noticeTimerRef.current) clearTimeout(noticeTimerRef.current)
    noticeTimerRef.current = setTimeout(() => {
        setNotice(''),
        noticeTimerRef.current = null
    }, 3000
    )
  }
  // 清理定时器
  useEffect(() => {
    return () => {
      if (noticeTimerRef.current) clearTimeout(noticeTimerRef.current)
    }
  }, [])

 
  return (
    <div className="projects-page">
      <div className="page-toolbar">
        <button className="btn primary" onClick={() => setCreating(true)}>
          新建项目
        </button>
      </div>

      {error && <p className="modal-error">{error}</p>}
      {notice && <p className="modal-saved">{notice}</p>}

      {loading && projects.length === 0 ? (
        <p className="hint">加载中…</p>
      ) : projects.length === 0 ? (
        <div className="card empty">暂无项目，点击「新建项目」开始</div>
      ) : (
        <>
          <div className="project-grid">
            {projects.map((p) => (
              <ProjectCard
                key={p.id}
                project={p}
                onEdit={() => setEditing(p)}
                onDelete={() => setDeleting(p)}
              />
            ))}
          </div>

          <div className="pagination">
            <span className="hint">共 {total} 个项目 · 第 {page}/{totalPages} 页</span>
            <div className="pagination-btns">
              <button
                className="btn small"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
              >
                上一页
              </button>
              <button
                className="btn small"
                disabled={page >= totalPages}
                onClick={() => setPage(page + 1)}
              >
                下一页
              </button>
            </div>
          </div>
        </>
      )}

      {/* 编辑弹窗（点卡片或点「编辑」按钮） */}
      {editing && (
        <ProjectEditModal
          project={editing}
          onClose={() => setEditing(null)}
          onSaved={handleSave}
        />
      )}

      {/* 新建弹窗 */}
      {creating && (
        <ProjectEditModal 
        onClose={() => setCreating(false)} 
        onSaved={handleSave} />
      )}

      {/* 删除确认弹窗 */}
      {deleting && (
        <ConfirmModal
          title="删除项目"
          message={`确定要删除项目「${deleting.name}」及其下的需求和测试用例吗？删除后不可恢复。`}
          onCancel={() => setDeleting(null)}
          onConfirm={handleDelete}
        />
      )}
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