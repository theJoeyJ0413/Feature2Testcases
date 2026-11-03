import { useState } from 'react'

import { bindHistoryProject, createProject, saveAgentFeatures, saveAgentTestcases } from '../../apis'

/**
 * Agent 任务完成后的弹窗：询问用户是否将本次分析保存为项目
 *
 * defaultName 由父组件从需求文档标题中提取；
 * 确认后调 POST /projects（source 固定为 'agent'），依次入库需求与用例，
 * 成功后回写历史记录（project_id）并通过 onSaved 通知父组件更新保存状态。
 */
export default function SaveProjectModal({ taskId, defaultName, description, features = [], testcases = [], onSaved, onClose }) {
  const [name, setName] = useState(defaultName || '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [savedDetail, setSavedDetail] = useState('')

  const handleSave = async () => {
    if (!name.trim()) {
      setError('项目名称不能为空')
      return
    }
    setLoading(true)
    setError('')
    try {
      // 新建项目，并拿到project_id
      const project = await createProject({
        name: name.trim(),
        description: description || '',
        source: 'agent',
      })
      // save_agent_features
      const fr = await saveAgentFeatures(project.id, {features})
      // save_agent_testcases
      const tr = await saveAgentTestcases({ project_id: project.id, testcases })
      // 回写历史记录：标记该任务成果已保存为项目（回写失败不影响保存主流程）
      try {
        if (taskId) await bindHistoryProject(taskId, project.id)
      } catch (e) {
        console.warn('回写历史记录失败：', e)
      }
      onSaved?.(project.id)
      setSaved(true)
      setSavedDetail(`已保存项目 + ${fr.saved} 个需求 + ${tr.saved} 条测试用例`+
        (fr.skipped + tr.skipped > 0 ? `（跳过 ${fr.skipped} 个需求 + ${tr.skipped} 条测试用例）` : '')
      )
      setTimeout(onClose, 1500) // 显示「已保存」后自动关闭
    } catch (e) {
      setError(e?.response?.data?.detail || '保存失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-mask" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>保存为项目？</h2>
        <p className="hint">本次需求分析已完成，是否将其保存到项目列表？是否将分析的需求和生成的测试用例一并保存？</p>

        <label className="modal-field">
          <span>项目名称</span>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="输入项目名称"
          />
        </label>

        {error && <p className="modal-error">{error}</p>}
        {saved && <p className="modal-saved">{savedDetail || '已保存该项目、需求和测试用例'}</p>}

        <div className="modal-actions">
          <button className="btn" onClick={onClose} disabled={loading}>
            暂不保存
          </button>
          <button
            className="btn primary"
            onClick={handleSave}
            disabled={loading || saved}
          >
            {loading ? '保存中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  )
}