import { useCallback, useEffect, useState, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'

import {
  listProjects,
  listFeatures,
  listTestcases,
  updateTestcase,
  deleteTestcase,
} from '../apis'

import FilterBar from '../components/testcases/FilterBar'
import TestcaseTable from '../components/testcases/TestcaseTable'
import TestcaseEditModal from '../components/testcases/TestcaseEditModal'

import '../css/TestcasesView.css'

/**
 * 测试用例管理页面：筛选栏 + 表格 + 分页
 *
 * 布局依据 DESIGN.md「测试用例管理页面」：
 * - 直接进菜单 = 全量；从需求页「关联用例」跳转 = URL 带 project_id / feature_id 预筛选
 * - 筛选维度：项目 / 需求 / 优先级 / 场景 / 维度 / 状态 / 关键字（可组合）
 * - 表格列：编号 / 模块 / 优先级 / 场景 / 维度 / 标题 / 关联需求 / 状态 / 操作
 * - 点击行展开详情（前置条件 / 操作步骤 / 预期结果）；状态徽标点击切换
 * - 项目筛选变化后，需求下拉只显示该项目下的需求（联动）
 *
 * 组件拆分 → components/testcases/：
 * - FilterBar.jsx           筛选栏
 * - TestcaseTable.jsx       用例表格
 * - TestcaseRow.jsx         用例行（含行展开详情）
 * - TestcaseEditModal.jsx   新建/编辑用例弹窗
 *
 */

const PAGE_SIZE = 10

export default function TestcasesView() {
  // ==================== 状态 ====================
  const [searchParams] = useSearchParams()
  const [filters, setFilters] = useState(() => ({
    project_id: searchParams.get('project_id') || '',
    feature_id: searchParams.get('feature_id') || '',
    priority: '',
    scenario: '',
    dimension: '',
    status: '',
    stage: '',
    keyword: '',
  }))
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  const [items, setItems] = useState([])           // 当前页用例列表
  const [projects, setProjects] = useState([])     // 筛选下拉：全部项目
  const [features, setFeatures] = useState([])     // 筛选下拉：当前项目下的需求（联动）
  const [expandedIds, setExpandedIds] = useState([]) // 展开的用例行 id 列表

  const [creating, setCreating] = useState(false)  // 新建用例弹窗
  const [editing, setEditing] = useState(null)     // 编辑用例弹窗（正在编辑的用例）
  const [deleting, setDeleting] = useState(null)   // 待删除的用例
  const [updatingIds, setUpdatingIds] = useState([]) // 状态切换中的用例 id（防连点）

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const loadTestcases = useCallback(async (p, currentFilters) => {
    setLoading(true)
    setError('')
    try {
      const data = await listTestcases({
        page: p,
        page_size: PAGE_SIZE,
        project_id: currentFilters.project_id || undefined,
        feature_id: currentFilters.feature_id || undefined,
        priority: currentFilters.priority || undefined,
        scenario: currentFilters.scenario || undefined,
        dimension: currentFilters.dimension || undefined,
        status: currentFilters.status || undefined,
        stage: currentFilters.stage || undefined,
        keyword: currentFilters.keyword || undefined,
      })
      setItems(data.items || [])
      setTotal(data.total || 0)
    }catch (e) {
      setError(e?.response?.data?.detail || '获取测试用例列表失败')
    } finally {
      setLoading(false)
    }
  }, [])

  const loadProjects = useCallback(async (p) => {
    setLoading(true)
    setError('')
    try {
      const data = await listProjects({ page: p, page_size: 100 })
      setProjects(data.items || [])
    } catch (e) {
      setError(e?.response?.data?.detail || '获取项目列表失败')
    } finally {
      setLoading(false)
    }
  }, [])

  const loadFeatures = useCallback(async (project_id) => {
    if (!project_id) {
      setFeatures([])
      return
    }
    setLoading(true)
    setError('')
    try {
      const data = await listFeatures(project_id)
      setFeatures(data.items || [])
    } catch (e) {
      setError(e?.response?.data?.detail || '获取需求列表失败')
    } finally {
      setLoading(false)
    }
  }, [])

  // 初始化：只加载下拉数据
  useEffect(() => {
    if (filters.project_id) {
      loadFeatures(filters.project_id)
    }
    loadProjects()
  }, [])

  // filters 变化 → 回到第 1 页并重新加载列表
  useEffect(() => {
    if (page === 1) {
      loadTestcases(1, filters)
    } else{
      setPage(1)
    }
  }, [filters, loadTestcases])

  // 翻页
  const firstRenderRef = useRef(true)
  useEffect(() => {
    if (firstRenderRef.current) {
      firstRenderRef.current = false
      return
    }
    loadTestcases(page, filters)
  }, [page, loadTestcases])

  const handleFilterChange = (key, value) => {
    if (key==='project_id') {
      //项目变化了：清空需求筛选，联动加载该项目下的需求
      setFilters((prev) => ({ ...prev, project_id: value, feature_id: '' }))
      if (value) {
        loadFeatures(value)
      }else {
        setFeatures([])
      }
      return
    }
    setFilters((prev) => ({ ...prev, [key]: value }))
  }

  const handleStatusChange = (testcase) => {
    if (updatingIds.includes(testcase.id)) return // 防连点：更新中忽略再次点击
    const nextStatus = {
      open: 'pass',
      pass: 'fail',
      fail: 'blocked',
      blocked: 'open'
    }[testcase.status] || 'open'
    setUpdatingIds((prev) => [...prev, testcase.id])
    updateTestcase(testcase.id, { status: nextStatus })
      .then((updated) => {
        setItems((prev) => prev.map((item) => item.id === updated.id ? updated : item))
      })
      .catch((e) => {
        setError(e?.response?.data?.detail || '更新测试用例状态失败')
      })
      .finally(() => {
        setUpdatingIds((prev) => prev.filter((id) => id !== testcase.id))
      })
  }

  // 行展开/收起
  const toggleRow = (id) => {
    if (expandedIds.includes(id)) {
      setExpandedIds(expandedIds.filter((i) => i !== id))
    } else {
      setExpandedIds([...expandedIds, id])
    }
  }

  const handleSave = () => {
    setEditing(null)
    setCreating(false)
    if (page!=1) {
      setPage(1)
    }else {
      loadTestcases(1, filters)
    }
  }

  const handleDelete = async() => {
    if (!deleting) return
    try {
      await deleteTestcase(deleting.id)
      setDeleting(null)
      if (page > 1 && items.length === 1) setPage(page - 1)
      else loadTestcases(page, filters)
    }catch(e){
      setError(e?.response?.data?.detail || '删除测试用例失败')
      setDeleting(null)
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div className="testcases-page">
      {/* ===== 筛选栏 ===== */}
      <FilterBar
        filters={filters}
        projects={projects}
        features={features}
        onChange={handleFilterChange}
        onCreate={() => setCreating(true)}
      />

      {error && <p className="modal-error">{error}</p>}

      {/* ===== 用例表格 ===== */}
      {loading ? (
        <div className="testcases-card empty">
          <p className="hint">加载中…</p>
        </div>
      ) : items.length === 0 ? (
        <div className="testcases-card empty">
          暂无测试用例
          {Object.values(filters).some(Boolean)
            ? '，试试调整筛选条件'
            : '，点击「新建用例」开始'}
        </div>
      ) : (
        <div className="testcases-card">
          <TestcaseTable
            items={items}
            expandedIds={expandedIds}
            updatingIds={updatingIds}
            onToggleRow={toggleRow}
            onStatusChange={handleStatusChange}
            onEdit={setEditing}
            onDelete={setDeleting}
          />
        </div>
      )}

      {/* ===== 分页 ===== */}
      <div className="pagination">
        <span className="hint">
          共 {total} 条 · 第 {page}/{totalPages} 页
        </span>
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

      {/* ===== 弹窗 ===== */}
      {editing && (
        <TestcaseEditModal
          testcase={editing}
          projects={projects}
          onClose={() => setEditing(null)}
          onSaved={handleSave}
        />
      )}
      {creating && (
        <TestcaseEditModal
          testcase={null}
          projects={projects}
          onClose={() => setCreating(false)}
          onSaved={handleSave}
        />
      )}
      {deleting && (
        <ConfirmModal
          title="删除用例"
          message={`确定要删除用例「${deleting.testcase_no} ${deleting.title}」吗？删除后不可恢复。`}
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
          <button className="btn" onClick={onCancel}>
            取消
          </button>
          <button className="btn danger" onClick={onConfirm}>
            删除
          </button>
        </div>
      </div>
    </div>
  )
}
