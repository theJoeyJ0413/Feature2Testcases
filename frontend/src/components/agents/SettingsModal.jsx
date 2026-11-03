import { useEffect, useState } from "react"
import { getSettings, updateSettings} from "../../apis"

/**
 * 设置按钮，点击弹窗，设置模型、API KEY
 * 位置：右上角
 */

export default function SettingsModal({onClose}) {

    // 表单状态
    const [apiKey, setApiKey] = useState('')
    const [apiKeyMasked, setApiKeyMasked] = useState('')
    const [baseUrl, setBaseUrl] = useState('')
    const [model, setModel] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [saved, setSaved] = useState(false)

    // 打开弹窗时拉取当前配置，并填充表单
    useEffect(() => {
        getSettings().then((data)=>{
            setApiKeyMasked(data.api_key_masked || '')
            setApiKey(data.api_key_masked || '')
            setBaseUrl(data.base_url || '')
            setModel(data.model || '')
        }).catch(()=>setError('获取当前配置失败'))
    }, [])

    // 点击保存
    const handleSave = async()=>{
        setError('')
        setSaved(false)
        if(!apiKey.trim()){
            setError('API KEY 不能为空')
            return
        }

        setLoading(true)
        try{
            // 约定：api_key传空字符串 等价于 保持原key不变
            const payload = {
                api_key: apiKey === apiKeyMasked ? '' : apiKey,
                base_url: baseUrl.trim(),
                model: model.trim()
            }
            await updateSettings(payload)
            setSaved(true)
            setTimeout(onClose, 1000) //显示已保存，1秒后自动关闭
        }catch(e){
            setError(e?.response?.data?.detail || '保存失败')
        }finally{
            setLoading(false)
        }
    }


    return (
        <div className="modal-mask" onClick={onClose}> {/* 点遮罩，关闭 */}
            <div className="modal" onClick={(e)=>e.stopPropagation()}> {/* 点弹窗内部，不关闭 */}
                <h2>模型设置</h2>

                <label className="modal-field">
                    <span>模型</span>
                    <input
                    type="text"
                    value={model}
                    onChange={(e)=>setModel(e.target.value)} 
                    placeholder="gpt-4o-mini"
                    />
                </label>
                <label className="modal-field">
                    <span>Base URL</span>
                    <input
                    type="text"
                    value={baseUrl}
                    onChange={(e)=>setBaseUrl(e.target.value)} 
                    placeholder="https://api.openai.com/v1"
                    />
                </label>
                <label className="modal-field">
                    <span>API KEY</span>
                    <input 
                    type="text"
                    value={apiKey}
                    onChange={(e)=>setApiKey(e.target.value)}
                    placeholder="sk-xxx"
                    />
                    <small className="hint">不修改则保持原 Key 不变</small>
                </label>

                {error && <p className="modal-error">{error}</p>}
                {saved && <p className="modal-saved">已保存</p>}

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
