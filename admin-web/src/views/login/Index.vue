<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <span class="heart-icon">❤️</span>
        <h2>爱在黄冈</h2>
        <p class="subtitle">相亲角运营管理平台</p>
      </div>

      <el-form :model="form" :rules="rules" ref="formRef" class="login-form" @keyup.enter="handleLogin">
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="管理员用户名"
            size="large"
            prefix-icon="User"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="管理员密码"
            size="large"
            prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="submit-btn"
            :loading="loading"
            @click="handleLogin"
          >
            登 录
          </el-button>
        </el-form-item>
      </el-form>
      <div class="footer-tip">
        <span>默认超级管理员账号配置于后端环境</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../../store/user'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  username: 'admin',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入管理员用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入管理员密码', trigger: 'blur' }]
}

const handleLogin = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      await userStore.login(form)
      ElMessage.success('登录成功，欢迎回来')
      router.push('/dashboard')
    } catch (err) {
      console.error(err)
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.login-container {
  width: 100vw;
  height: 100vh;
  background: linear-gradient(135deg, #2b3a4a 0%, #17212b 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-card {
  width: 400px;
  background: #ffffff;
  border-radius: 12px;
  padding: 40px 32px 30px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.25);
}

.login-header {
  text-align: center;
  margin-bottom: 30px;
}

.heart-icon {
  font-size: 36px;
  display: block;
  margin-bottom: 8px;
}

.login-header h2 {
  font-size: 24px;
  color: #1f2d3d;
  font-weight: 600;
  margin-bottom: 6px;
}

.subtitle {
  font-size: 13px;
  color: #909399;
}

.login-form {
  margin-top: 10px;
}

.submit-btn {
  width: 100%;
  font-size: 15px;
  letter-spacing: 2px;
  margin-top: 10px;
}

.footer-tip {
  text-align: center;
  font-size: 12px;
  color: #a8abb2;
  margin-top: 10px;
}
</style>
