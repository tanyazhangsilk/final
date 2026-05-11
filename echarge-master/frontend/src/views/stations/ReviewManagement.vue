<script setup>
import { ref } from 'vue'
import { Check, Close, View } from '@element-plus/icons-vue'

const activeTab = ref('pending')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(100)

const pendingData = ref([
  {
    submitTime: '2023-10-27 09:30:00',
    submitter: '深圳市特来电新能源有限公司',
    type: 'station_online',
    content: '申请上线「南山科技园充电站」',
    status: 'pending'
  },
  {
    submitTime: '2023-10-27 10:15:00',
    submitter: '个人 - 张三',
    type: 'pile_add',
    content: '申请新增 2 台直流快充桩',
    status: 'pending'
  }
])

const processedData = ref([
  {
    submitTime: '2023-10-26 14:00:00',
    submitter: '星星充电',
    type: 'info_change',
    content: '变更「福田市民中心充电站」营业时间',
    status: 'approved',
    processTime: '2023-10-26 15:30:00',
    processor: 'admin'
  },
  {
    submitTime: '2023-10-25 11:20:00',
    submitter: '依威能源',
    type: 'station_online',
    content: '申请上线「龙岗大运中心充电站」',
    status: 'rejected',
    processTime: '2023-10-25 12:00:00',
    processor: 'admin',
    reason: '资质文件不全'
  }
])

const getTypeText = (type) => {
    const map = {
        station_online: '电站上线申请',
        pile_add: '新增电桩申请',
        info_change: '信息变更申请'
    }
    return map[type] || '未知申请'
}

const getTypeTag = (type) => {
     const map = {
        station_online: 'warning',
        pile_add: 'primary',
        info_change: 'info'
    }
    return map[type] || 'info'
}

const handleApprove = (row) => {
    console.log('通过', row)
}

const handleReject = (row) => {
    console.log('驳回', row)
}

const handleDetail = (row) => {
    console.log('详情', row)
}
</script>

<template>
  <div class="page-container flex flex-col gap-4">
    <el-card shadow="never" class="base-card flex-1">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="待审核" name="pending">
            <div class="flex justify-end mb-4">
                 <el-button type="primary" plain>批量通过</el-button>
            </div>
          <el-table :data="pendingData" style="width: 100%">
            <el-table-column prop="submitTime" label="提交时间" width="180" />
            <el-table-column prop="submitter" label="申请机构/人" min-width="180" />
            <el-table-column prop="type" label="业务类型" width="150">
              <template #default="{ row }">
                <el-tag :type="getTypeTag(row.type)" effect="light">{{ getTypeText(row.type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="content" label="申请内容" min-width="250" show-overflow-tooltip />
            <el-table-column label="操作" width="220" fixed="right">
              <template #default="{ row }">
                <el-button type="success" size="small" :icon="Check" @click="handleApprove(row)">通过</el-button>
                <el-button type="danger" size="small" :icon="Close" @click="handleReject(row)">驳回</el-button>
                <el-button link type="primary" size="small" @click="handleDetail(row)">详情</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        
        <el-tab-pane label="已处理记录" name="processed">
          <el-table :data="processedData" style="width: 100%">
            <el-table-column prop="submitTime" label="提交时间" width="180" />
            <el-table-column prop="submitter" label="申请机构/人" min-width="180" />
            <el-table-column prop="type" label="业务类型" width="150">
               <template #default="{ row }">
                <el-tag :type="getTypeTag(row.type)" effect="light">{{ getTypeText(row.type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="content" label="申请内容" min-width="200" show-overflow-tooltip />
             <el-table-column prop="status" label="处理结果" width="100">
              <template #default="{ row }">
                <el-tag v-if="row.status === 'approved'" type="success">已通过</el-tag>
                <el-tag v-else type="danger">已驳回</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="processTime" label="处理时间" width="180" />
            <el-table-column prop="processor" label="处理人" width="100" />
             <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                 <el-button link type="primary" size="small" :icon="View" @click="handleDetail(row)">详情</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>

      <div class="mt-4 flex justify-end">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
        />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
/* Tailwind classes handled in template */
</style>
