import { useEffect, useState } from 'react'

import { createTestrun, listFeatures } from '../../apis'
import { MODE_OPTIONS, STAGE_OPTIONS } from './meta'

/**
 * 新建运行批次弹窗
 *
 * - 项目必选（运行批次归属项目）
 * - 模式：冒烟 / 全量 / 回归 / 自定义（仅标记批次用途）
 * - 范围：全部用例 / 指定需求（勾选需求）
 * - 可选收窄：优先级、阶段
 * - 提交后由后端按条件快照用例，创建后进入执行工作台
 */
export default function RunCreateModal({
  projects,
  defaultProjectId,
  onClose,
  onCreated,
}) {
  const [projectId, setProjectId] = useState(
    defaultProjectId ? String(defaultProjectId) : ''
  )
  const [features, setFeatures] = useState([])
  const [mode, setMode] = useState('smoke')
  const [scopeType, setScopeType] = useState('all')
  const [featureIds, setFeatureIds] = useState([])
  const [priority, setPriority] = useState('')
  const [stage, setStage] = useState('')

  const [loadingFeatures, setLoadingFeatures] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const loadFeatures = async (pid) => {
    if (!pid) {
      setFeatures([])
      return
    }
    setLoadingFeatures(true)
    try {
      const data = await listFeatures(pid)
      setFeatures(data.items || [])
    } catch (e) {
      setError(e?.response?.data?.detail || '获取需求列表失败')
    } finally {
      setLoadingFeatures(false)
    }
  }

  useEffect(() => {
    if (projectId) loadFeatures(projectId)
  }, [])

  const handleProjectChange = (value) => {
    setProjectId(value)
    setFeatureIds([])
    setScopeType('all')
    loadFeatures(value)
  }

  const toggleFeature = (id) => {
    setFeatureIds((prev) =>
      prev.includes(id) ? prev.filter((fid) => fid !== id) : [...prev, id]
    )
  }

  const handleSubmit = async () => {
    if (!projectId) {
      setError('请选择项目')
      return
    }
    if (scopeType === 'features' && featureIds.length === 0) {
      setError('请至少选择一个需求')
      return
    }

    setSubmitting(true)
    setError('')
    try {
      const run = await createTestrun({
        project_id: Number(projectId),
        mode,
        scope:
          scopeType === 'features'
            ? { type: 'features', feature_ids: featureIds }
            : { type: 'all' },
        ...(priority ? { priority } : {}),
        ...(stage ? { stage } : {}),
      })
      onCreated(run)
    } catch (e) {
      setError(e?.response?.data?.detail || '创建运行批次失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="tr-modal-mask" onClick={onClose}>
      <div className="tr-modal" onClick={(e) => e.stopPropagation()}>
        <h2>新建运行</h2>
        <p className="tr-modal-desc">
          创建后按当前用例生成快照，后续逐条记录结果；快照不受用例后续修改影响。
        </p>

        <label className="tr-field">
          <span>所属项目</span>
          <select
            value={projectId}
            onChange={(e) => handleProjectChange(e.target.value)}
            disabled={submitting}
          >
            <option value="">请选择项目</option>
            {projects.map((p) => (
              <option key={p.id} value={String(p.id)}>
                {p.name}
              </option>
            ))}
          </select>
        </label>

        <div className="tr-field">
          <span>运行模式</span>
          <div className="tr-mode-grid">
            {MODE_OPTIONS.map((item) => (
              <button
                key={item.value}
                type="button"
                className={`tr-mode-card${mode === item.value ? ' selected' : ''}`}
                onClick={() => setMode(item.value)}
                disabled={submitting}
              >
                <strong>{item.label}</strong>
                <small>{item.hint}</small>
              </button>
            ))}
          </div>
        </div>

        <div className="tr-field">
          <span>运行范围</span>
          <div className="tr-scope-row">
            <label className={`tr-radio${scopeType === 'all' ? ' checked' : ''}`}>
              <input
                type="radio"
                name="scope"
                checked={scopeType === 'all'}
                onChange={() => setScopeType('all')}
                disabled={submitting}
              />
              全部用例
            </label>
            <label className={`tr-radio${scopeType === 'features' ? ' checked' : ''}`}>
              <input
                type="radio"
                name="scope"
                checked={scopeType === 'features'}
                onChange={() => setScopeType('features')}
                disabled={submitting}
              />
              指定需求
            </label>
          </div>
        </div>

        {scopeType === 'features' && (
          <div className="tr-field">
            <span>选择需求</span>
            {loadingFeatures ? (
              <p className="hint">加载中…</p>
            ) : features.length === 0 ? (
              <p className="hint">该项目下暂无可选需求</p>
            ) : (
              <div className="tr-feature-checks">
                {features.map((f) => (
                  <label
                    key={f.id}
                    className={`tr-feature-check${featureIds.includes(f.id) ? ' checked' : ''}`}
                  >
                    <input
                      type="checkbox"
                      checked={featureIds.includes(f.id)}
                      onChange={() => toggleFeature(f.id)}
                      disabled={submitting}
                    />
                    <span className="tr-feature-no">{f.feature_no}</span>
                    <span>{f.title}</span>
                  </label>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="tr-field-row">
          <label className="tr-field">
            <span>优先级（可选）</span>
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              disabled={submitting}
            >
              <option value="">不限</option>
              <option value="P0">P0（核心）</option>
              <option value="P1">P1（重要）</option>
              <option value="P2">P2（一般）</option>
              <option value="P3">P3（低）</option>
            </select>
          </label>

          <label className="tr-field">
            <span>阶段（可选）</span>
            <select
              value={stage}
              onChange={(e) => setStage(e.target.value)}
              disabled={submitting}
            >
              <option value="">不限</option>
              {STAGE_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
        </div>

        {error && <p className="tr-modal-error">{error}</p>}

        <div className="tr-modal-actions">
          <button type="button" className="btn" onClick={onClose} disabled={submitting}>
            取消
          </button>
          <button
            type="button"
            className="btn primary"
            onClick={handleSubmit}
            disabled={submitting}
          >
            {submitting ? '创建中…' : '创建并开始'}
          </button>
        </div>
      </div>
    </div>
  )
}
