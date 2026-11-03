/**
 * 第二步卡片：分析进度（含取消按钮）
 */
export default function ProgressCard({ stage, onCancel }) {
  return (
    <section className="card">
      <h2>第二步：分析中</h2>
      <div className="progress">
        <span className="spinner" />
        <p>{stage || '正在处理…'}</p>
      </div>
      <p className="hint">分析需要一些时间，请耐心等待，不要关闭页面</p>
      <div className="actions">
        <button className="btn" onClick={onCancel}>
          取消
        </button>
      </div>
    </section>
  )
}
