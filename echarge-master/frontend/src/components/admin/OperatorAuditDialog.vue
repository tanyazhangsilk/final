<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'

import {
  formatOperatorAuditStatus,
  type OperatorAuditRecord,
  type OperatorAuditStatus,
} from '../../utils/operatorAudit'

type ReviewStatus = Extract<OperatorAuditStatus, 'approved' | 'rejected'>

const props = defineProps<{
  modelValue: boolean
  record: OperatorAuditRecord | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  submit: [payload: { status: ReviewStatus; comment: string }]
}>()

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const form = reactive({
  status: 'approved' as ReviewStatus,
  comment: '',
})

watch(
  () => props.record,
  (record) => {
    form.status = record?.status === 'rejected' ? 'rejected' : 'approved'
    form.comment = record?.status === 'pending' ? '' : record?.reviewComment || ''
  },
  { immediate: true },
)

const dialogTitle = computed(() =>
  props.record ? `审核申请 - ${props.record.operatorName}` : '审核申请',
)

const submitReview = () => {
  if (form.status === 'rejected' && !form.comment.trim()) {
    ElMessage.warning('驳回时必须填写审核意见。')
    return
  }

  emit('submit', {
    status: form.status,
    comment: form.comment.trim() || (form.status === 'approved' ? '资料审核通过，准予入驻平台。' : ''),
  })
}
</script>

<template>
  <el-dialog v-model="dialogVisible" :title="dialogTitle" width="560px" destroy-on-close>
    <template v-if="record">
      <div class="dialog-hero">
        <div>
          <p class="dialog-hero__eyebrow">申请编号 {{ record.applicationNo }}</p>
          <h3>{{ record.companyName }}</h3>
          <p>{{ record.contactName }} · {{ record.phone }} · 当前状态 {{ formatOperatorAuditStatus(record.status) }}</p>
        </div>
      </div>

      <el-form label-position="top" class="review-form">
        <el-form-item label="审核结果">
          <el-radio-group v-model="form.status" class="review-result-group">
            <el-radio-button label="approved">通过</el-radio-button>
            <el-radio-button label="rejected">驳回</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="审核意见" :required="form.status === 'rejected'">
          <el-input
            v-model="form.comment"
            type="textarea"
            :rows="5"
            maxlength="200"
            show-word-limit
            resize="none"
            :placeholder="
              form.status === 'approved'
                ? '请输入通过说明，例如：资料完整、资质有效，可进入下一步接入配置。'
                : '请输入驳回原因，例如：授权证明缺失、营业执照信息需补充。'
            "
          />
        </el-form-item>
      </el-form>
    </template>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitReview">确认提交</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.dialog-hero {
  margin-bottom: 18px;
  padding: 16px 18px;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, rgba(47, 116, 255, 0.08), rgba(255, 255, 255, 0.94));
  border: 1px solid rgba(47, 116, 255, 0.14);
}

.dialog-hero__eyebrow {
  margin: 0 0 8px;
  color: var(--color-text-3);
  font-size: 12px;
}

.dialog-hero h3 {
  margin: 0;
  color: var(--color-text);
  font-size: 18px;
}

.dialog-hero p {
  margin: 8px 0 0;
  color: var(--color-text-2);
  line-height: 1.6;
}

.review-result-group {
  width: 100%;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
