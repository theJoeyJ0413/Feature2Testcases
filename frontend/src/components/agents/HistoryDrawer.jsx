import { useCallback, useEffect, useState } from 'react'

import { deleteHistory, getHistory, listHistory } from '../../apis'

const PAGE_SIZE = 20

// 状态徽标文案（pending / running 统一显示为「进行中」）
const STATUS_LABEL = { done: '完成', failed: '失败', pending: '进行中', running: '进行中' }

// 保存联动分组：null=全部，false=未保存为项目，true=已保存为项目（对应 task_history.project_id）
const SAVED_TABS = [
  { value: null, label: '全部' },
  { value: false, label: '未保存' },
  { value: true, label: '已保存' },
]

function formatTime(iso) {
  return (iso || '').replace('T', ' ').slice(0, 16)
}

/**
 * 历史记录抽屉：右侧滑出，展示历次分析任务（持久化在 task_history 表）
 *
 * 列表可按「全部 / 未保存 / 已保存」分组筛选（保存联动由「保存为项目」成功后回写
 * task_history.project_id）；点击「查看」先拉取详情（含从后端重建的 result 与保存
 * 联动状态），再交给父组件还原结果视图；删除会连同 output 下的任务目录一并清理
 * （项目库数据不受影响）。
 */
export default function HistoryDrawer({ onClose, onOpen }) {
  const [items, setItems] = useState([])          // 已加载的历史记录（分页累加）
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [keyword, setKeyword] = useState('')       // 输入框内容
  const [appliedKeyword, setAppliedKeyword] = useState('')  // 已生效的搜索词
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [savedFilter, setSavedFilter] = useState(null)  // null=全部，false=未保存，true=已保存为项目
  const [openingId, setOpeningId] = useState(null)  // 正在打开详情的记录
  const [deletingId, setDeletingId] = useState(null)

  // 加载历史列表：第 1 页替换，其余页追加；saved 指定分组（null=全部，不传参）
  const load = useCallback(async (targetPage, kw, saved) => {
    setLoading(true)
    setError('')
    try {
      const data = await listHistory({
        page: targetPage,
        pageSize: PAGE_SIZE,
        keyword: kw || undefined,
        saved: saved === null ? undefined : saved,
      })
      setItems((prev) => (targetPage === 1 ? data.items : [...prev, ...data.items]))
      setTotal(data.total)
      setPage(targetPage)
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || '加载历史记录失败')
    } finally {
      setLoading(false)
    }
  }, [])

  // 打开时加载第一页；搜索词或保存联动分组变化后重新加载
  useEffect(() => {
    load(1, appliedKeyword, savedFilter)
  }, [load, appliedKeyword, savedFilter])

  // 查看：拉取详情后交给父组件还原结果视图
  const handleOpen = async (item) => {
    setOpeningId(item.task_id)
    setError('')
    try {
      const detail = await getHistory(item.task_id)
      if (!detail.result || (!detail.result.requirement && !detail.result.testcase)) {
        setError('该任务的产物文件已被清理，无法查看')
        return
      }
      onOpen(detail.task_id, detail.result, detail.project_id)
      onClose()
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || '打开历史记录失败')
    } finally {
      setOpeningId(null)
    }
  }

  // 删除：记录与任务目录一并删除，先二次确认
  const handleDelete = async (item) => {
    if (!window.confirm(`删除这条历史记录？对应任务目录与产物文件会一并删除。\n\n${item.title || item.task_id}`)) return
    setDeletingId(item.task_id)
    setError('')
    try {
      await deleteHistory(item.task_id)
      setItems((prev) => prev.filter((it) => it.task_id !== item.task_id))
      setTotal((t) => Math.max(0, t - 1))
      if (items.length <= 1) load(1, appliedKeyword, savedFilter)  // 列表被删空后重新拉取
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || '删除历史记录失败')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="drawer-mask" onClick={onClose}>
      <div className="drawer" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <h2>历史记录</h2>
          <button className="drawer-close" onClick={onClose} aria-label="关闭">×</button>
        </div>

        <div className="drawer-tabs">
          {SAVED_TABS.map((tab) => (
            <button
              key={String(tab.value)}
              className={`drawer-tab${savedFilter === tab.value ? ' active' : ''}`}
              onClick={() => setSavedFilter(tab.value)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="drawer-search">
          <input
            type="text"
            value={keyword}
            placeholder="搜索标题或输入内容"
            onChange={(e) => setKeyword(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') setAppliedKeyword(keyword.trim()) }}
          />
          <button className="btn small" onClick={() => setAppliedKeyword(keyword.trim())}>
            搜索
          </button>
        </div>

        {error && <p className="drawer-error">{error}</p>}

        <div className="drawer-list">
          {items.length === 0 && !loading && (
            <p className="hint">
              {savedFilter === null ? '暂无历史记录' : savedFilter ? '暂无已保存为项目的记录' : '暂无未保存的记录'}
            </p>
          )}

          {items.map((item) => (
            <div className="history-item" key={item.task_id}>
              <div className="history-item-top">
                <span className="history-title" title={item.title || item.task_id}>
                  {item.title || '未命名任务'}
                </span>
                <span className="history-badges">
                  {item.project_id > 0 ? (
                    <span className="history-badge saved">已保存为项目</span>
                  ) : (
                    <span className="history-badge unsaved">未保存</span>
                  )}
                  <span className={`history-badge ${item.status}`}>
                    {STATUS_LABEL[item.status] || item.status}
                  </span>
                </span>
              </div>

              <div className="history-item-meta">
                <span>{formatTime(item.created_at)}</span>
                <span>
                  {item.input_source === 'file' ? `文件：${item.input_filename || '上传文件'}` : '文字输入'}
                </span>
              </div>

              {item.status === 'failed' && item.error && (
                <p className="history-item-error" title={item.error}>{item.error}</p>
              )}

              <div className="history-item-actions">
                <button
                  className="btn small"
                  disabled={item.status !== 'done' || openingId === item.task_id}
                  onClick={() => handleOpen(item)}
                >
                  {openingId === item.task_id ? '打开中…' : '查看'}
                </button>
                <button
                  className="btn small danger"
                  disabled={deletingId === item.task_id}
                  onClick={() => handleDelete(item)}
                >
                  {deletingId === item.task_id ? '删除中…' : '删除'}
                </button>
              </div>
            </div>
          ))}

          {loading && <p className="hint">加载中…</p>}

          {!loading && items.length < total && (
            <button className="drawer-more" onClick={() => load(page + 1, appliedKeyword, savedFilter)}>
              加载更多（共 {total} 条）
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
