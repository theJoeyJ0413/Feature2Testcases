import { useState } from 'react'

import { createTestcaseManual, updateTestcase, listFeatures } from '../../apis'

/**
 * 测试用例 新建/编辑弹窗
 *
 * 新建（依据 DESIGN.md）：
 *   - 项目（必选，仅作定位）+ 需求（必选，真正归属）联动双下拉
 *     —— 选中项目后需求下拉只显示该项目下需求（加载由 view 的 onFeaturesLoad 完成）
 *   - 提交只传 feature_id，testcase_no 由后端按需求内递增生成
 *   - 所属模块默认继承所选需求的 module（可改）
 * 编辑：
 *   - 归属需求不可改（后端更新白名单无 feature_id），只读展示编号与关联需求
 *   - 可编辑 实际结果 / 执行状态（执行记录字段）
 * 字段：标题 / 模块 / 优先级 / 场景 / 维度 / 阶段（多选 checkbox）/ 前置条件
 *       / 操作步骤（动态列表，可增删/排序）/ 预期结果 / 实际结果（仅编辑）/ 状态（仅编辑）
 */

// 阶段选项（与后端 STAGE_VALUES 一致）
const STAGE_OPTIONS = ['冒烟', '通道', '灰度', '系统', '回归', '验收']

export default function TestcaseEditModal({
  testcase,
  projects,
  onClose,
  onSaved,
}) {
  const isEdit = Boolean(testcase)

  // ==================== 表单状态 ====================
  const [projectId, setProjectId] = useState('') // 仅新建：定位用
  // 新建弹窗独立维护需求下拉：打开时为空，选中项目后自加载（不依赖页面筛选的 features）
  const [modalFeatures, setModalFeatures] = useState([])
  const [featureId, setFeatureId] = useState(
    testcase ? String(testcase.feature_id) : ''
  )
  const [title, setTitle] = useState(testcase?.title || '')
  const [module, setModule] = useState(testcase?.module || '')
  const [priority, setPriority] = useState(testcase?.priority || 'P2')
  const [scenario, setScenario] = useState(testcase?.scenario || '')
  const [dimension, setDimension] = useState(testcase?.dimension || '')
  // 阶段：多值列表，checkbox 勾选切换
  const [stages, setStages] = useState(
    testcase && Array.isArray(testcase.stages) ? [...testcase.stages] : []
  )
  const [precondition, setPrecondition] = useState(testcase?.precondition || '')
  // 操作步骤：动态列表，每步一条，支持增删与上移/下移；保存时过滤空项
  const [stepsList, setStepsList] = useState(
    testcase && Array.isArray(testcase.steps) && testcase.steps.length
      ? [...testcase.steps]
      : ['']
  )
  const [expected, setExpected] = useState(testcase?.expected || '')
  const [actual, setActual] = useState(testcase?.actual || '')
  const [status, setStatus] = useState(testcase?.status || 'open')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // 项目变化：重置已选需求与继承的模块，自加载该项目下的需求
  const handleProjectChange = async (value) => {
    setProjectId(value)
    setFeatureId('')
    setModule('')
    setModalFeatures([])
    if (!value) return
    try {
      const data = await listFeatures(value)
      setModalFeatures(data.items || [])
    } catch (e) {
      setError(e?.response?.data?.detail || '获取需求列表失败')
    }
  }

  // 需求变化：选中后默认继承其 module（仅新建且 module 为空时）
  const handleFeatureChange = (value) => {
    setFeatureId(value)
    // 在 features 中找到选中项，若当前 module 为空则 setModule(选中需求.module)
    const selectedFeature = modalFeatures.find((f) => f.id === Number(value))
    if (!module && selectedFeature) {
      setModule(selectedFeature.module)
    }
  }

  // 阶段勾选：已选则移除，未选则加入（保持 STAGE_OPTIONS 顺序）
  const toggleStage = (value) => {
    setStages((prev) =>
      prev.includes(value)
        ? prev.filter((s) => s !== value)
        : STAGE_OPTIONS.filter((s) => [...prev, value].includes(s))
    )
  }

  // ==================== 步骤列表操作 ====================
  const handleStepChange = (index, value) => {
    const next = [...stepsList]
    next[index] = value
    setStepsList(next)
  }
  const addStep = () => setStepsList((prev) => [...prev, ''])
  const removeStep = (index) =>
    setStepsList((prev) => prev.filter((_, i) => i !== index))
  const moveStep = (index, dir) => {
    const target = index + dir
    if (target < 0 || target >= stepsList.length) return
    const next = [...stepsList]
    ;[next[index], next[target]] = [next[target], next[index]]
    setStepsList(next)
  }

  const handleSave = async () => {
    if (!title.trim()) {
      setError('标题不能为空')
      return
    }
    if (!featureId) {
      setError('所属需求不能为空')
      return
    }
    // 步骤列表过滤空项后提交
    const steps = stepsList.map((s) => s.trim()).filter(Boolean)
    if (!isEdit && !projectId) {
      setError('所属项目不能为空')
      return
    }

    setLoading(true)
    setError('')
    try {
      if (isEdit) {
        await updateTestcase(testcase.id, {
          title: title.trim(),
          module: module.trim(),
          priority: priority,
          scenario: scenario.trim(),
          dimension: dimension.trim(),
          stages: stages,
          precondition: precondition.trim(),
          steps: steps,
          expected: expected.trim(),
          actual: actual.trim(),
          status: status,
        })
      } else {
        await createTestcaseManual(featureId, {
          title: title.trim(),
          module: module.trim(),
          priority: priority,
          scenario: scenario.trim(),
          dimension: dimension.trim(),
          stages: stages,
          precondition: precondition.trim(),
          steps: steps,
          expected: expected.trim(),
        })
      }
      onSaved()
    } catch (e) {
      setError(e?.response?.data?.detail || '保存失败')
    } finally {
      setLoading(false)
    }
  }
  return (
    <div className="modal-mask" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>{isEdit ? '编辑用例' : '新建用例'}</h2>

        {isEdit ? (
          /* 编辑：归属只读展示（后端更新不支持改归属） */
          <div className="tc-readonly-line">
            <span>编号：{testcase.testcase_no}</span>
            <span>关联需求：{testcase.feature_ref}</span>
          </div>
        ) : (
          <>
            {/* 联动双下拉：项目仅定位，需求真正归属 */}
            <label className="modal-field">
              <span>所属项目（仅定位）</span>
              <select
                value={projectId}
                onChange={(e) => handleProjectChange(e.target.value)}
              >
                <option value="">请选择项目</option>
                {projects.map((p) => (
                  <option key={p.id} value={String(p.id)}>
                    {p.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="modal-field">
              <span>所属需求（归属，必选）</span>
              <select
                value={featureId}
                onChange={(e) => handleFeatureChange(e.target.value)}
              >
                <option value="">请选择需求</option>
                {modalFeatures.map((f) => (
                  <option key={f.id} value={String(f.id)}>
                    {f.feature_no} {f.title}
                  </option>
                ))}
              </select>
            </label>
          </>
        )}

        <label className="modal-field">
          <span>用例标题</span>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="输入用例标题"
          />
        </label>

        <label className="modal-field">
          <span>所属模块</span>
          <input
            type="text"
            value={module}
            onChange={(e) => setModule(e.target.value)}
            placeholder="默认继承所选需求的模块，可修改"
          />
        </label>

        <label className="modal-field">
          <span>优先级</span>
          <select value={priority} onChange={(e) => setPriority(e.target.value)}>
            <option value="P0">P0（核心）</option>
            <option value="P1">P1（重要）</option>
            <option value="P2">P2（一般）</option>
            <option value="P3">P3（低）</option>
          </select>
        </label>

        <label className="modal-field">
          <span>场景</span>
          <select value={scenario} onChange={(e) => setScenario(e.target.value)}>
            <option value="">请选择场景</option>
            <option value="正向">正向</option>
            <option value="边界">边界</option>
            <option value="异常">异常</option>
          </select>
        </label>

        <label className="modal-field">
          <span>维度</span>
          <select value={dimension} onChange={(e) => setDimension(e.target.value)}>
            <option value="">请选择维度</option>
            <option value="功能">功能</option>
            <option value="性能">性能</option>
            <option value="安全">安全</option>
            <option value="易用性">易用性</option>
            <option value="可靠性">可靠性</option>
            <option value="兼容性">兼容性</option>
          </select>
        </label>

        <div className="modal-field">
          <span>测试阶段（可多选）</span>
          <div className="stage-checks">
            {STAGE_OPTIONS.map((s) => (
              <label key={s} className={`stage-check${stages.includes(s) ? ' checked' : ''}`}>
                <input
                  type="checkbox"
                  checked={stages.includes(s)}
                  onChange={() => toggleStage(s)}
                />
                {s}
              </label>
            ))}
          </div>
        </div>

        <label className="modal-field">
          <span>前置条件</span>
          <textarea
            rows={2}
            value={precondition}
            onChange={(e) => setPrecondition(e.target.value)}
            placeholder="执行前需要满足的条件"
          />
        </label>

        <div className="modal-field">
          <span>操作步骤</span>
          <div className="json-list">
            {stepsList.map((step, idx) => (
              <div className="json-list-row" key={idx}>
                <span className="json-row-index">{idx + 1}.</span>
                <input
                  type="text"
                  value={step}
                  onChange={(e) => handleStepChange(idx, e.target.value)}
                  placeholder="如：打开登录页"
                />
                <button
                  type="button"
                  className="json-row-move"
                  title="上移"
                  disabled={idx === 0}
                  onClick={() => moveStep(idx, -1)}
                >
                  ↑
                </button>
                <button
                  type="button"
                  className="json-row-move"
                  title="下移"
                  disabled={idx === stepsList.length - 1}
                  onClick={() => moveStep(idx, 1)}
                >
                  ↓
                </button>
                <button
                  type="button"
                  className="json-row-remove"
                  title="删除该步骤"
                  onClick={() => removeStep(idx)}
                >
                  ×
                </button>
              </div>
            ))}
            <button type="button" className="json-row-add" onClick={addStep}>
              + 添加步骤
            </button>
          </div>
        </div>

        <label className="modal-field">
          <span>预期结果</span>
          <textarea
            rows={2}
            value={expected}
            onChange={(e) => setExpected(e.target.value)}
            placeholder="预期达到的结果"
          />
        </label>

        {isEdit && (
          <>
            <label className="modal-field">
              <span>实际结果</span>
              <textarea
                rows={2}
                value={actual}
                onChange={(e) => setActual(e.target.value)}
                placeholder="实际执行结果（执行记录）"
              />
            </label>

            <label className="modal-field">
              <span>执行状态</span>
              <select value={status} onChange={(e) => setStatus(e.target.value)}>
                <option value="open">待执行</option>
                <option value="pass">通过</option>
                <option value="fail">失败</option>
                <option value="blocked">阻塞</option>
              </select>
            </label>
          </>
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
