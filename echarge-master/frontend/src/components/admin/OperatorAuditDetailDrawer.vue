<script setup lang="ts">
import { computed } from 'vue'

import {
  createAuditSummary,
  formatAttachmentStatus,
  formatOperatorAuditStatus,
  getAuditStatusTagType,
  type OperatorAuditRecord,
} from '../../utils/operatorAudit'

const props = defineProps<{
  modelValue: boolean
  record: OperatorAuditRecord | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  review: [record: OperatorAuditRecord]
}>()

const drawerVisible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const attachmentSummary = computed(() =>
  props.record ? createAuditSummary(props.record.attachments) : '--',
)
</script>

<template>
  <el-drawer v-model="drawerVisible" size="760px" :destroy-on-close="false" class="operator-audit-drawer">
    <template #header>
      <div v-if="record" class="drawer-header">
        <div>
          <p class="drawer-header__eyebrow">申请编号 {{ record.applicationNo }}</p>
          <h3>{{ record.operatorName }}</h3>
          <p>{{ record.companyName }}</p>
        </div>
        <el-tag :type="getAuditStatusTagType(record.status)" round effect="light">
          {{ formatOperatorAuditStatus(record.status) }}
        </el-tag>
      </div>
    </template>

    <template v-if="record">
      <section class="drawer-summary">
        <div class="summary-card">
          <span>提交时间</span>
          <strong>{{ record.submittedAt }}</strong>
        </div>
        <div class="summary-card">
          <span>最近处理人</span>
          <strong>{{ record.lastProcessedBy || '待处理' }}</strong>
        </div>
        <div class="summary-card">
          <span>资质材料</span>
          <strong>{{ attachmentSummary }}</strong>
        </div>
      </section>

      <section class="detail-section soft-card">
        <div class="detail-section__head">
          <h4>基础信息</h4>
          <span>主体资料</span>
        </div>
        <div class="info-kv">
          <div class="info-kv__item">
            <p class="info-kv__label">运营商名称</p>
            <p class="info-kv__value">{{ record.operatorName }}</p>
          </div>
          <div class="info-kv__item">
            <p class="info-kv__label">企业全称</p>
            <p class="info-kv__value">{{ record.companyName }}</p>
          </div>
          <div class="info-kv__item">
            <p class="info-kv__label">统一社会信用代码</p>
            <p class="info-kv__value">{{ record.creditCode }}</p>
          </div>
          <div class="info-kv__item">
            <p class="info-kv__label">成立时间</p>
            <p class="info-kv__value">{{ record.foundedAt }}</p>
          </div>
          <div class="info-kv__item">
            <p class="info-kv__label">所在地区</p>
            <p class="info-kv__value">{{ record.region }}</p>
          </div>
          <div class="info-kv__item">
            <p class="info-kv__label">联系地址</p>
            <p class="info-kv__value">{{ record.address }}</p>
          </div>
          <div class="info-kv__item">
            <p class="info-kv__label">联系人</p>
            <p class="info-kv__value">{{ record.contactName }}</p>
          </div>
          <div class="info-kv__item">
            <p class="info-kv__label">联系电话</p>
            <p class="info-kv__value">{{ record.phone }}</p>
          </div>
          <div class="info-kv__item">
            <p class="info-kv__label">联系邮箱</p>
            <p class="info-kv__value">{{ record.email }}</p>
          </div>
        </div>
      </section>

      <section class="detail-section soft-card">
        <div class="detail-section__head">
          <h4>经营信息</h4>
          <span>运营规模</span>
        </div>
        <div class="info-kv">
          <div class="info-kv__item">
            <p class="info-kv__label">已运营电站数量</p>
            <p class="info-kv__value">{{ record.stationCount }} 座</p>
          </div>
          <div class="info-kv__item">
            <p class="info-kv__label">已接入充电桩数量</p>
            <p class="info-kv__value">{{ record.chargerCount }} 个</p>
          </div>
          <div class="info-kv__item">
            <p class="info-kv__label">服务城市</p>
            <p class="info-kv__value">{{ record.serviceCities.join('、') }}</p>
          </div>
          <div class="info-kv__item info-kv__item--wide">
            <p class="info-kv__label">企业简介</p>
            <p class="info-kv__value info-kv__value--multiline">{{ record.description }}</p>
          </div>
        </div>
      </section>

      <section class="detail-section soft-card">
        <div class="detail-section__head">
          <h4>资质材料</h4>
          <span>附件展示区</span>
        </div>
        <div class="attachment-grid">
          <div v-for="attachment in record.attachments" :key="attachment.id" class="attachment-card">
            <div class="attachment-card__top">
              <strong>{{ attachment.label }}</strong>
              <el-tag
                :type="attachment.status === 'ready' ? 'success' : attachment.status === 'reviewing' ? 'warning' : 'info'"
                size="small"
                effect="light"
              >
                {{ formatAttachmentStatus(attachment.status) }}
              </el-tag>
            </div>
            <p>{{ attachment.fileName }}</p>
            <div class="attachment-card__meta">
              <span>{{ attachment.updatedAt }}</span>
              <el-link type="primary" :underline="false">{{ attachment.previewText }}</el-link>
            </div>
          </div>
        </div>
      </section>

      <section class="detail-section soft-card">
        <div class="detail-section__head">
          <h4>审核记录时间线</h4>
          <span>{{ record.auditTimeline.length }} 条记录</span>
        </div>
        <el-timeline class="timeline-panel">
          <el-timeline-item
            v-for="item in record.auditTimeline"
            :key="item.id"
            :timestamp="`${item.time} · ${item.operator}`"
            :type="getAuditStatusTagType(item.status)"
            placement="top"
          >
            <div class="timeline-card">
              <div class="timeline-card__head">
                <strong>{{ item.title }}</strong>
                <el-tag :type="getAuditStatusTagType(item.status)" effect="light" round size="small">
                  {{ formatOperatorAuditStatus(item.status) }}
                </el-tag>
              </div>
              <p>{{ item.comment }}</p>
            </div>
          </el-timeline-item>
        </el-timeline>
      </section>

      <section class="detail-section soft-card">
        <div class="detail-section__head">
          <h4>当前审核意见</h4>
          <span>最新结论</span>
        </div>
        <div class="review-note">
          <p>{{ record.reviewComment || '当前尚未形成最终审核结论，可直接发起审核操作。' }}</p>
        </div>
      </section>

      <div class="drawer-actions">
        <el-button @click="drawerVisible = false">关闭</el-button>
        <el-button type="primary" @click="emit('review', record)">审核处理</el-button>
      </div>
    </template>
  </el-drawer>
</template>

<style scoped>
.drawer-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.drawer-header__eyebrow {
  margin: 0 0 8px;
  color: var(--color-text-3);
  font-size: 12px;
  letter-spacing: 0.06em;
}

.drawer-header h3 {
  margin: 0;
  color: var(--color-text);
  font-size: 24px;
}

.drawer-header p {
  margin: 8px 0 0;
  color: var(--color-text-2);
}

.drawer-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.summary-card {
  padding: 14px 16px;
  border-radius: var(--radius-md);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(243, 246, 251, 0.96));
  border: 1px solid var(--color-border);
}

.summary-card span {
  display: block;
  color: var(--color-text-3);
  font-size: 12px;
}

.summary-card strong {
  display: block;
  margin-top: 10px;
  color: var(--color-text);
  line-height: 1.5;
}

.detail-section {
  margin-bottom: 16px;
  padding: 18px;
}

.detail-section__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.detail-section__head h4 {
  margin: 0;
  color: var(--color-text);
  font-size: 16px;
}

.detail-section__head span {
  color: var(--color-text-3);
  font-size: 12px;
}

.attachment-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.attachment-card {
  padding: 14px;
  border-radius: var(--radius-md);
  border: 1px dashed rgba(47, 116, 255, 0.18);
  background: rgba(255, 255, 255, 0.64);
}

.attachment-card__top,
.attachment-card__meta,
.timeline-card__head,
.drawer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.attachment-card p,
.timeline-card p,
.review-note p {
  margin: 10px 0 0;
  color: var(--color-text-2);
  line-height: 1.7;
}

.attachment-card__meta {
  margin-top: 12px;
  color: var(--color-text-3);
  font-size: 12px;
}

.timeline-panel {
  padding-left: 6px;
}

.timeline-card {
  padding: 14px 16px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: rgba(255, 255, 255, 0.76);
}

.review-note {
  padding: 14px 16px;
  border-radius: var(--radius-md);
  background: rgba(47, 116, 255, 0.06);
  border: 1px solid rgba(47, 116, 255, 0.14);
}

.drawer-actions {
  margin-top: 20px;
}

.info-kv__item--wide {
  grid-column: 1 / -1;
}

.info-kv__value--multiline {
  line-height: 1.7;
  font-weight: 500;
  white-space: pre-line;
}

@media (max-width: 768px) {
  .drawer-summary,
  .attachment-grid {
    grid-template-columns: 1fr;
  }
}
</style>
