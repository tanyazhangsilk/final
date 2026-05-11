<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Key } from '@element-plus/icons-vue'
import request from '../api/http'
import { ROLES, setStoredRole, setStoredOperatorId, resolveRoleDefaultRoute } from '../config/permissions'

const router = useRouter()
const account = ref('')
const password = ref('')
const loading = ref(false)
const loginType = ref('admin')

async function handleLogin() {
  if (!account.value.trim() || !password.value.trim()) {
    ElMessage.warning('请输入账号和密码')
    return
  }

  loading.value = true
  try {
    const res = await request.post('/mgr/login', {
      account: account.value.trim(),
      password: password.value.trim(),
    })
    const body = res.data
    const data = body && body.code === 200 ? body.data : (res.data || res)

    if (data && data.role === 'admin') {
      setStoredRole(ROLES.ADMIN)
      setStoredOperatorId(1)
      router.push('/admin')
    } else if (data && data.role === 'operator') {
      setStoredRole(ROLES.OPERATOR)
      setStoredOperatorId(data.operator_id || data.user_id || data.id || 1)
      router.push('/operator')
    } else {
      ElMessage.warning('该账号不是管理员或运营商账号')
    }
  } catch {
    // 尝试本地管理员账号
    if (account.value === 'admin@echarge.com' && password.value === 'admin123') {
      setStoredRole(ROLES.ADMIN)
      setStoredOperatorId(1)
      router.push('/admin')
      return
    }
    if (account.value === 'operator@echarge.com' && password.value === 'operator123') {
      setStoredRole(ROLES.OPERATOR)
      setStoredOperatorId(1)
      router.push('/operator')
      return
    }
    ElMessage.error('登录失败，请检查账号密码或后端服务')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <h1 class="login-title">E-Charge 聚合充电平台</h1>
        <p class="login-subtitle">运营商管理后台</p>
      </div>

      <el-form @submit.prevent="handleLogin" class="login-form">
        <el-form-item>
          <el-input
            v-model="account"
            placeholder="邮箱账号或手机号"
            :prefix-icon="User"
            size="large"
            clearable
          />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="password"
            type="password"
            placeholder="密码"
            :prefix-icon="Lock"
            size="large"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            style="width:100%"
            @click="handleLogin"
          >
            登 录
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-footer">
        <p class="demo-hint">演示账号</p>
        <div class="demo-accounts">
          <el-tag type="success" class="demo-tag" @click="account='admin@echarge.com';password='admin123'">
            <el-icon style="margin-right:4px"><Key /></el-icon>管理员: admin
          </el-tag>
          <el-tag type="warning" class="demo-tag" @click="account='operator@echarge.com';password='operator123'">
            <el-icon style="margin-right:4px"><Key /></el-icon>运营商: operator
          </el-tag>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0d9488 0%, #115e59 50%, #134e4a 100%);
}

.login-card {
  width: 420px;
  padding: 48px 40px 40px;
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

.login-header {
  text-align: center;
  margin-bottom: 40px;
}

.login-title {
  font-size: 28px;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 8px;
}

.login-subtitle {
  font-size: 14px;
  color: #64748b;
  margin: 0;
}

.login-form {
  margin-bottom: 24px;
}

.login-footer {
  text-align: center;
}

.demo-hint {
  font-size: 13px;
  color: #94a3b8;
  margin: 0 0 12px;
}

.demo-accounts {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.demo-tag {
  cursor: pointer;
  padding: 6px 12px;
  font-size: 13px;
}
</style>
