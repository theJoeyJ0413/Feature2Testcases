/**
 * 错误提示卡片
 */
export default function ErrorCard({ error, onReset }) {
  return (
    <section className="card error-card">
      <h2>出错了</h2>
      <pre className="error-text">{error}</pre>
      <div className="actions">
        <button className="btn" onClick={onReset}>
          重新开始
        </button>
      </div>
    </section>
  )
}
