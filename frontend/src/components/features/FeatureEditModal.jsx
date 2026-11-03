import { useState } from 'react'

import { createFeatureManual, updateFeature } from '../../apis'

/**
 * 需求编辑/手动新建弹窗
 */
export default function FeatureEditModal({project, feature, onClose, onSaved}) {
    const isEdit = Boolean(feature)

    const [title, setTitle] = useState(feature?.title || '')
    const [description, setDescription] = useState(feature?.description || '')
    const [module, setModule] = useState(feature?.module || '')
    // 功能性要求：动态列表，每项一条；保存时过滤空项
    const [functionalItems, setFunctionalItems] = useState(
      feature && Array.isArray(feature.functional) && feature.functional.length
        ? [...feature.functional]
        : ['']
    )
    // 非功能性要求：维度组列表（key=维度名，items=条目），保存时过滤空项转对象
    const [nfGroups, setNfGroups] = useState(() => {
      if (
        feature &&
        feature.non_functional &&
        typeof feature.non_functional === 'object' &&
        !Array.isArray(feature.non_functional)
      ) {
        const entries = Object.entries(feature.non_functional)
        if (entries.length) {
          return entries.map(([key, items]) => ({
            key,
            items: Array.isArray(items) ? [...items] : [],
          }))
        }
      }
      return [{ key: '', items: [''] }]
    })
    const [status, setStatus] = useState(feature?.status || 'open')
    const [priority, setPriority] = useState(feature?.priority || 'P2')

    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')

    // ==================== 结构化列表操作 ====================
    const handleFunctionalChange = (index, value) => {
        const next = [...functionalItems]
        next[index] = value
        setFunctionalItems(next)
    }
    const addFunctional = () => setFunctionalItems((prev) => [...prev, ''])
    const removeFunctional = (index) =>
        setFunctionalItems((prev) => prev.filter((_, i) => i !== index))

    const handleNfKeyChange = (gIdx, value) => {
        const next = [...nfGroups]
        next[gIdx] = { ...next[gIdx], key: value }
        setNfGroups(next)
    }
    const handleNfItemChange = (gIdx, iIdx, value) => {
        const next = [...nfGroups]
        const items = [...next[gIdx].items]
        items[iIdx] = value
        next[gIdx] = { ...next[gIdx], items }
        setNfGroups(next)
    }
    const addNfItem = (gIdx) =>
        setNfGroups((prev) => {
            const next = [...prev]
            next[gIdx] = { ...next[gIdx], items: [...next[gIdx].items, ''] }
            return next
        })
    const removeNfItem = (gIdx, iIdx) =>
        setNfGroups((prev) => {
            const next = [...prev]
            next[gIdx] = {
                ...next[gIdx],
                items: next[gIdx].items.filter((_, i) => i !== iIdx),
            }
            return next
        })
    const addNfGroup = () =>
        setNfGroups((prev) => [...prev, { key: '', items: [''] }])
    const removeNfGroup = (gIdx) =>
        setNfGroups((prev) => prev.filter((_, i) => i !== gIdx))

    const handleSave = async () => {
        if (!title.trim()) {
            setError('标题不能为空')
            return
        }

        // 结构化列表转目标结构：过滤空项；同名维度条目合并
        const functionalList = functionalItems.map((s) => s.trim()).filter(Boolean)
        const nonFunctionalDict = {}
        nfGroups.forEach(({ key, items }) => {
            const k = key.trim()
            const list = items.map((s) => s.trim()).filter(Boolean)
            if (!k || !list.length) return
            nonFunctionalDict[k] = (nonFunctionalDict[k] || []).concat(list)
        })

        setLoading(true)
        setError('')
        try{
            if (isEdit) {
                await updateFeature(project.id, feature.id, {
                    title: title.trim(),
                    description: description.trim(),
                    module: module.trim(),
                    functional: functionalList,
                    non_functional: nonFunctionalDict,
                    status: status,
                    priority: priority
                })
            } else {
                await createFeatureManual(project.id, {
                    title: title.trim(),
                    description: description.trim(),
                    module: module.trim(),
                    functional: functionalList,
                    non_functional: nonFunctionalDict,
                    priority
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
        <h2>{isEdit ? '编辑需求' : '新建需求'}</h2>

        <label className="modal-field">
          <span>需求名称</span>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="输入需求标题"
          />
        </label>

        <label className="modal-field">
          <span>需求描述</span>
          <textarea
            rows={4}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="简要描述这个需求"
          />
        </label>

        <label className="modal-field">
          <span>所属模块</span>
          <input
            type="text"
            value={module}
            onChange={(e) => setModule(e.target.value)}
            placeholder="所属模块"
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

        <div className="modal-field">
          <span>功能性要求</span>
          <div className="json-list">
            {functionalItems.map((item, idx) => (
              <div className="json-list-row" key={idx}>
                <input
                  type="text"
                  value={item}
                  onChange={(e) => handleFunctionalChange(idx, e.target.value)}
                  placeholder="如：支持登录"
                />
                <button
                  type="button"
                  className="json-row-remove"
                  title="删除该项"
                  onClick={() => removeFunctional(idx)}
                >
                  ×
                </button>
              </div>
            ))}
            <button type="button" className="json-row-add" onClick={addFunctional}>
              + 添加功能点
            </button>
          </div>
        </div>

        <div className="modal-field">
          <span>非功能性要求</span>
          <div className="nf-group-list">
            {nfGroups.map((group, gIdx) => (
              <div className="nf-group" key={gIdx}>
                <div className="nf-group-head">
                  <input
                    type="text"
                    value={group.key}
                    onChange={(e) => handleNfKeyChange(gIdx, e.target.value)}
                    placeholder="维度名，如：性能"
                  />
                  <button
                    type="button"
                    className="json-row-remove"
                    title="删除该维度"
                    onClick={() => removeNfGroup(gIdx)}
                  >
                    删除维度
                  </button>
                </div>
                {group.items.map((item, iIdx) => (
                  <div className="json-list-row" key={iIdx}>
                    <input
                      type="text"
                      value={item}
                      onChange={(e) => handleNfItemChange(gIdx, iIdx, e.target.value)}
                      placeholder="如：响应时间小于2秒"
                    />
                    <button
                      type="button"
                      className="json-row-remove"
                      title="删除该条目"
                      onClick={() => removeNfItem(gIdx, iIdx)}
                    >
                      ×
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  className="json-row-add"
                  onClick={() => addNfItem(gIdx)}
                >
                  + 添加条目
                </button>
              </div>
            ))}
            <button type="button" className="json-row-add" onClick={addNfGroup}>
              + 添加维度
            </button>
          </div>
        </div>

        {isEdit ? (
          <label className="modal-field">
            <span>状态</span>
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="open">未分析</option>
              <option value="analyzed">已分析</option>
              <option value="closed">关闭</option>
            </select>
          </label>
        ) : (
          <label className="modal-field">
            <span>来源</span>
            <input type="text" value="手动创建" disabled readOnly />
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