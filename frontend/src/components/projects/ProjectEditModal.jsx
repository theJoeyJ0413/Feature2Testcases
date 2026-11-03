import { useState } from 'react'

import { createProject, updateProject } from '../../apis'

/**
 * 项目编辑/新建弹窗
 *
 * project 为 null → 新建模式（可选来源：手动 / Agent）
 * project 有值   → 编辑模式（可改标题、描述、状态）
 */
export default function ProjectEditModal({ project, onClose, onSaved }) {
  const isEdit = Boolean(project)
  const [name, setName] = useState(project?.name || '')
  const [description, setDescription] = useState(project?.description || '')
  const [status, setStatus] = useState(project?.status || 'active')
  const [source, setSource] = useState('manual')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSave = async () => {
    if (!name.trim()) {
      setError('项目名称不能为空')
      return
    }
    setLoading(true)
    setError('')
    try {
      if (isEdit) {
        await updateProject(project.id, {
          name: name.trim(),
          description: description.trim(),
          status,
        })
      } else {
        await createProject({
          name: name.trim(),
          description: description.trim(),
          source,
        })
      }
      onSaved() // 父组件关闭弹窗并刷新列表
    } catch (e) {
      setError(e?.response?.data?.detail || '保存失败')
    } finally {
      setLoading(false)
    }
  }
  return (
    <div className="modal-mask" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>{isEdit ? '编辑项目' : '新建项目'}</h2>

        <label className="modal-field">
          <span>项目名称</span>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="输入项目名称"
          />
        </label>

        <label className="modal-field">
          <span>项目描述</span>
          <textarea
            rows={4}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="简要描述这个项目"
          />
        </label>

        {isEdit ? (
          <label className="modal-field">
            <span>状态</span>
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="active">进行中</option>
              <option value="archived">已归档</option>
            </select>
          </label>
        ) : (
          <label className="modal-field">
            <span>来源</span>
            <select value={source} onChange={(e) => setSource(e.target.value)}>
              <option value="manual">手动创建</option>
              <option value="agent">Agent 生成</option>
            </select>
          </label>
        )}

        {error && <p className="modal-error">{error}</p>}

        <div className="modal-actions">
          <button className="btn" onClick={onClose} disabled={loading}>
            取消
          </button>
          <button className="btn primary" onClick={handleSave} disabled={loading}>
            {loading ? '保存中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  )
}