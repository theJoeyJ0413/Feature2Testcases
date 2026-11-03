import ReactMarkdown from 'react-markdown'

export default function MarkdownView({ content }) {
  return (
    <div className="markdown-body">
      <ReactMarkdown>{content || ''}</ReactMarkdown>
    </div>
  )
}
