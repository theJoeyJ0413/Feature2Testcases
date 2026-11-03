/**
 * 测试运行模块共享枚举与展示辅助
 * 与后端 testruns_store.py 的取值保持一致
 */

export const MODE_LABELS = {
  smoke: '冒烟',
  full: '全量',
  regression: '回归',
  custom: '自定义',
}

export const MODE_OPTIONS = [
  { value: 'smoke', label: '冒烟', hint: '核心链路快速验证' },
  { value: 'full', label: '全量', hint: '覆盖全部用例' },
  { value: 'regression', label: '回归', hint: '验证既有功能未受影响' },
  { value: 'custom', label: '自定义', hint: '按所选范围自由执行' },
]

export const RUN_STATUS_LABELS = {
  running: '进行中',
  completed: '已完成',
}

export const RESULT_LABELS = {
  open: '待执行',
  pass: '通过',
  fail: '失败',
  blocked: '阻塞',
}

export const RESULT_OPTIONS = ['open', 'pass', 'fail', 'blocked']

export const STAGE_OPTIONS = ['冒烟', '通道', '灰度', '系统', '回归', '验收']

/** ISO 时间 → MM-DD HH:mm */
export function formatRunTime(value) {
  if (!value) return ''
  const text = String(value)
  return text.length >= 16 ? `${text.slice(5, 10)} ${text.slice(11, 16)}` : text
}
