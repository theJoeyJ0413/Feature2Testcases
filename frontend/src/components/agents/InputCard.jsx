/**
 * 第一步卡片：输入需求（支持直接输入文字 / 上传文件两种模式）
 */
export default function InputCard({
  mode,
  onModeChange,
  text,
  onTextChange,
  file,
  onFileChange,
  running,
  onSubmit,
}) {
  return (
    <section className="card">
      <h2>输入需求</h2>
      <div className="mode-tabs">
        <button
          className={mode === 'text' ? 'tab active' : 'tab'}
          onClick={() => onModeChange('text')}
          disabled={running}
        >
          输入文字
        </button>
        <button
          className={mode === 'file' ? 'tab active' : 'tab'}
          onClick={() => onModeChange('file')}
          disabled={running}
        >
          上传文档
        </button>
      </div>

      {mode === 'text' ? (
        <textarea
          className="text-input"
          rows={6}
          placeholder="请简要描述你的需求，例如：我想开发一个在线图书管理系统，用户可以注册登录、搜索图书、借阅归还……"
          value={text}
          onChange={(e) => onTextChange(e.target.value)}
          disabled={running}
        />
      ) : (
        <div className="file-input-wrap">
          <input
            type="file"
            accept=".txt,.md,.pdf"
            onChange={(e) => onFileChange(e.target.files?.[0] || null)}
            disabled={running}
          />
          <p className="hint">支持 .txt / .md / .pdf 文件</p>
        </div>
      )}

      {!running && (
        <div className="actions">
          <button className="btn primary" onClick={onSubmit}>
            开始分析
          </button>
        </div>
      )}
    </section>
  )
}
