export type OperatorAuditStatus = 'pending' | 'approved' | 'rejected'
export type AttachmentStatus = 'ready' | 'reviewing' | 'missing'

export interface OperatorAuditAttachment {
  id: string
  label: string
  fileName: string
  status: AttachmentStatus
  updatedAt: string
  previewText: string
}

export interface OperatorAuditTimelineItem {
  id: string
  title: string
  time: string
  operator: string
  status: OperatorAuditStatus
  comment: string
}

export interface OperatorAuditRecord {
  id: string
  applicationNo: string
  operatorName: string
  companyName: string
  contactName: string
  phone: string
  email: string
  region: string
  address: string
  creditCode: string
  foundedAt: string
  stationCount: number
  chargerCount: number
  serviceCities: string[]
  description: string
  attachments: OperatorAuditAttachment[]
  status: OperatorAuditStatus
  submittedAt: string
  reviewedBy: string
  reviewedAt: string
  reviewComment: string
  lastProcessedBy: string
  lastProcessedAt: string
  auditTimeline: OperatorAuditTimelineItem[]
}

const statusMetaMap = {
  pending: { label: '待审核', tagType: 'warning' },
  approved: { label: '已通过', tagType: 'success' },
  rejected: { label: '已驳回', tagType: 'danger' },
} as const

const attachmentMetaMap = {
  ready: '已上传',
  reviewing: '待复核',
  missing: '待补充',
} as const

export const formatOperatorAuditStatus = (status: OperatorAuditStatus) => statusMetaMap[status].label

export const getAuditStatusTagType = (status: OperatorAuditStatus) => statusMetaMap[status].tagType

export const formatAttachmentStatus = (status: AttachmentStatus) => attachmentMetaMap[status]

export const createAuditSummary = (attachments: OperatorAuditAttachment[]) => {
  const readyCount = attachments.filter((item) => item.status === 'ready').length
  return `${readyCount}/${attachments.length} 份材料已完成`
}
