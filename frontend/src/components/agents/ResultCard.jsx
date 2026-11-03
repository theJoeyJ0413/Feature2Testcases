import { downloadUrl } from '../../apis'
import MarkdownView from './MarkdownView'

/**
 * 第三步卡片：查看和下载结果（需求分析文档 + 测试用例）
 *
 * savedProjectId > 0 表示该结果已保存为项目，保存入口置灰防重复入库。
 */
export default function ResultCard({ taskId, result, savedProjectId = 0, onReset, onSaveProject }) {
  return (
    <section className="card">
      <h2>第三步：查看和下载结果</h2>

      <div className="result-block">
        <div className="result-title">
          <h3>需求分析文档</h3>
          <a
            className="btn small"
            href={downloadUrl(taskId, 'requirement')}
            download
          >
            下载 (.md)
          </a>
        </div>
        <MarkdownView content={result.requirement_content} />
      </div>

      <div className="result-block">
        <div className="result-title">
          <h3>测试用例</h3>
          <a
            className="btn small"
            href={downloadUrl(taskId, 'testcase')}
            download
          >
            下载 (.xlsx)
          </a>
        </div>
        <p className="hint">
          测试用例已生成 Excel 文件（{result.testcase?.filename}），
          点击上方按钮下载后用 Excel / WPS 打开查看。
        </p>
      </div>

      <div className="actions">
        <button className="btn primary" onClick={onSaveProject} disabled={savedProjectId > 0}>
          {savedProjectId > 0 ? '已保存为项目' : '保存为项目'}
        </button>
        <button className="btn" onClick={onReset}>
          再分析一个
        </button>
      </div>
    </section>
  )
}
