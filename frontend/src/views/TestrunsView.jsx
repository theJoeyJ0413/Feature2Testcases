import { useEffect, useState } from 'react'

import {
  finishTestrun,
  getTestrun,
  getTestrunStats,
  listProjects,
  listTestruns,
  updateRunItem,
} from '../apis'

import RunStatsCards from '../components/testruns/RunStatsCards'
import RunListSidebar from '../components/testruns/RunListSidebar'
import RunCreateModal from '../components/testruns/RunCreateModal'
import RunExecutionPanel from '../components/testruns/RunExecutionPanel'

import '../css/TestrunsView.css'

/**
 * 测试运行页面（A 运行工作台）
 *
 * 顶部：项目筛选 + 新建运行 + 执行率/通过率统计卡
 * 左侧：运行批次列表（搜索、分页）
 * 右侧：批次详情，按需求分组逐条记录结果，结束后锁定
 */

const RUN_PAGE_SIZE = 10
const STATS_DAYS = 30

function round1(value) {
  return Math.round(value * 10) / 10
}

/** 根据 item 数组重算批次统计（口径与后端一致） */
function withStats(run, items) {
  const total = items.length
  const passed = items.filter((item) => item.result === 'pass').length
  const failed = items.filter((item) => item.result === 'fail').length
  const blocked = items.filter((item) => item.result === 'blocked').length
  const open = items.filter((item) => item.result === 'open').length
  const executed = total - open
  return {
    ...run,
    items,
    total,
    executed,
    passed,
    failed,
    blocked,
    open,
    execution_rate: total ? round1((executed * 100) / total) : 0,
    pass_rate: executed ? round1((passed * 100) / executed) : 0,
  }
}

export default function TestrunsView() {
  const [projects, setProjects] = useState([])

  const [projectFilter, setProjectFilter] = useState('')
  const [keyword, setKeyword] = useState('')
  const [runPage, setRunPage] = useState(1)
  const [runs, setRuns] = useState([])
  const [runsTotal, setRunsTotal] = useState(0)
  const [runsLoading, setRunsLoading] = useState(false)
  const [runsRefresh, setRunsRefresh] = useState(0)

  const [stats, setStats] = useState(null)
  const [statsLoading, setStatsLoading] = useState(false)
  const [statsRefresh, setStatsRefresh] = useState(0)

  const [selectedRunId, setSelectedRunId] = useState(null)
  const [detail, setDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [updatingItemId, setUpdatingItemId] = useState(null)

  const [creating, setCreating] = useState(false)
  const [confirmFinish, setConfirmFinish] = useState(false)
  const [finishing, setFinishing] = useState(false)

  const [error, setError] = useState('')

  // 项目下拉：进入页面一次性加载
  useEffect(() => {
    let cancelled = false
    listProjects({ page: 1, page_size: 100 })
      .then((data) => {
        if (!cancelled) setProjects(data.items || [])
      })
      .catch((e) => {
        if (!cancelled) setError(e?.response?.data?.detail || '获取项目列表失败')
      })
    return () => {
      cancelled = true
    }
  }, [])

  // 统计卡：随项目筛选与刷新信号更新
  useEffect(() => {
    let cancelled = false
    setStatsLoading(true)
    getTestrunStats({
      ...(projectFilter ? { project_id: Number(projectFilter) } : {}),
      days: STATS_DAYS,
    })
      .then((data) => {
        if (!cancelled) setStats(data)
      })
      .catch((e) => {
        if (!cancelled) setError(e?.response?.data?.detail || '获取运行统计失败')
      })
      .finally(() => {
        if (!cancelled) setStatsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [projectFilter, statsRefresh])

  // 批次列表：筛选 / 搜索 / 分页
  useEffect(() => {
    let cancelled = false
    setRunsLoading(true)
    listTestruns({
      page: runPage,
      page_size: RUN_PAGE_SIZE,
      ...(projectFilter ? { project_id: Number(projectFilter) } : {}),
      ...(keyword ? { keyword } : {}),
    })
      .then((data) => {
        if (cancelled) return
        const items = data.items || []
        setRuns(items)
        setRunsTotal(data.total || 0)
        setSelectedRunId((prev) => {
          if (prev && items.some((run) => run.id === prev)) return prev
          return prev == null ? items[0]?.id ?? null : prev
        })
      })
      .catch((e) => {
        if (!cancelled) setError(e?.response?.data?.detail || '获取运行批次失败')
      })
      .finally(() => {
        if (!cancelled) setRunsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [projectFilter, keyword, runPage, runsRefresh])

  // 批次详情：选中批次后加载
  useEffect(() => {
    if (!selectedRunId) {
      setDetail(null)
      return
    }
    let cancelled = false
    setDetailLoading(true)
    setDetail((prev) => (prev && prev.id === selectedRunId ? prev : null))
    getTestrun(selectedRunId)
      .then((data) => {
        if (!cancelled) setDetail(data)
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e?.response?.data?.detail || '获取运行详情失败')
          setDetail(null)
        }
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [selectedRunId])

  const handleProjectFilterChange = (value) => {
    setProjectFilter(value)
    setRunPage(1)
    setSelectedRunId(null)
    setDetail(null)
  }

  const handleKeywordChange = (value) => {
    setKeyword(value)
    setRunPage(1)
  }

  const applyItemUpdate = (updated) => {
    if (!detail) return
    setDetail((prev) => {
      if (!prev) return prev
      const items = prev.items.map((item) =>
        item.id === updated.id ? updated : item
      )
      return withStats(prev, items)
    })
  }

  const handleSelectResult = async (item, result) => {
    if (!detail || detail.status !== 'running' || updatingItemId) return
    setUpdatingItemId(item.id)
    setError('')
    try {
      const updated = await updateRunItem(detail.id, item.id, { result })
      applyItemUpdate(updated)
      setRunsRefresh((n) => n + 1)
      setStatsRefresh((n) => n + 1)
    } catch (e) {
      setError(e?.response?.data?.detail || '记录执行结果失败')
    } finally {
      setUpdatingItemId(null)
    }
  }

  const handleFieldSave = async (item, field, value) => {
    if (!detail || detail.status !== 'running' || updatingItemId) return
    setUpdatingItemId(item.id)
    setError('')
    try {
      const updated = await updateRunItem(detail.id, item.id, { [field]: value })
      applyItemUpdate(updated)
    } catch (e) {
      setError(e?.response?.data?.detail || '保存执行记录失败')
    } finally {
      setUpdatingItemId(null)
    }
  }

  const handleFinish = async () => {
    if (!detail) return
    setFinishing(true)
    setError('')
    try {
      const updated = await finishTestrun(detail.id)
      setDetail(updated)
      setConfirmFinish(false)
      setRunsRefresh((n) => n + 1)
      setStatsRefresh((n) => n + 1)
    } catch (e) {
      setError(e?.response?.data?.detail || '结束运行失败')
      setConfirmFinish(false)
    } finally {
      setFinishing(false)
    }
  }

  const handleCreated = (run) => {
    setCreating(false)
    setProjectFilter(String(run.project_id))
    setRunPage(1)
    setSelectedRunId(run.id)
    setDetail(run)
    setRunsRefresh((n) => n + 1)
    setStatsRefresh((n) => n + 1)
  }

  return (
    <div className="testruns-page">
      <header className="tr-page-head">
        <div>
          <h1>测试运行</h1>
          <p className="hint">
            沿「需求 → 用例」链路执行并记录结果；执行率按全部用例、通过率按已执行用例统计。
          </p>
        </div>
        <div className="tr-page-actions">
          <select
            className="tr-select"
            value={projectFilter}
            onChange={(e) => handleProjectFilterChange(e.target.value)}
          >
            <option value="">项目：全部</option>
            {projects.map((p) => (
              <option key={p.id} value={String(p.id)}>
                {p.name}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="btn primary"
            onClick={() => setCreating(true)}
          >
            + 新建运行
          </button>
        </div>
      </header>

      <RunStatsCards stats={stats} loading={statsLoading} />

      {error && (
        <div className="tr-error" role="alert">
          {error}
          <button type="button" onClick={() => setError('')}>
            ×
          </button>
        </div>
      )}

      <div className="tr-body">
        <RunListSidebar
          runs={runs}
          selectedId={selectedRunId}
          keyword={keyword}
          onKeywordChange={handleKeywordChange}
          total={runsTotal}
          page={runPage}
          pageSize={RUN_PAGE_SIZE}
          onPageChange={setRunPage}
          loading={runsLoading}
        />

        <RunExecutionPanel
          detail={detail}
          loading={detailLoading}
          updatingItemId={updatingItemId}
          finishing={finishing}
          onSelectResult={handleSelectResult}
          onFieldSave={handleFieldSave}
          onFinish={() => setConfirmFinish(true)}
        />
      </div>

      {creating && (
        <RunCreateModal
          projects={projects}
          defaultProjectId={projectFilter}
          onClose={() => setCreating(false)}
          onCreated={handleCreated}
        />
      )}

      {confirmFinish && detail && (
        <div className="tr-modal-mask" onClick={() => !finishing && setConfirmFinish(false)}>
          <div className="tr-modal small" onClick={(e) => e.stopPropagation()}>
            <h2>结束运行</h2>
            <p className="tr-confirm-message">
              确定结束批次「{detail.run_no}」吗？结束后所有用例结果将被锁定，不能再修改。
            </p>
            <div className="tr-modal-actions">
              <button
                type="button"
                className="btn"
                onClick={() => setConfirmFinish(false)}
                disabled={finishing}
              >
                取消
              </button>
              <button
                type="button"
                className="btn primary"
                onClick={handleFinish}
                disabled={finishing}
              >
                {finishing ? '结束中…' : '结束运行'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
