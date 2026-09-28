<template>
  <div class="import-container">
    <el-row :gutter="16">
      <!-- 智能文本解析导入 -->
      <el-col :xs="24" :lg="14">
        <el-card shadow="never" class="box-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">📝 智能长文本提取与入库</span>
              <el-tag size="small" type="success">AI/规则双引擎解析</el-tag>
            </div>
          </template>

          <div class="import-tip">
            支持直接粘贴微信群、朋友圈或相亲角登记文本。系统自动提取：<strong>姓名、性别、年龄、电话、身高、职业、收入、房产</strong>等关键属性。
          </div>

          <el-input
            v-model="importText"
            type="textarea"
            :rows="9"
            placeholder="示例：
姓名：张小明
性别：男
年龄：28
电话：13812345678
身高：178
职业：公务员
收入：8000
房产：本地有房
择偶要求：性格温和，在黄冈本地工作"
          />

          <div class="btn-group">
            <el-button type="primary" :loading="importing" @click="handleExtractAndImport">
              <el-icon><Check /></el-icon> 立即提取并入库
            </el-button>
            <el-button @click="importText = ''">清空文本</el-button>
          </div>

          <div v-if="lastExtracted" class="result-box">
            <el-divider content-position="left">上一次解析入库结果</el-divider>
            <el-descriptions :column="2" size="small" border>
              <el-descriptions-item label="姓名">{{ lastExtracted.name }}</el-descriptions-item>
              <el-descriptions-item label="性别">{{ lastExtracted.gender }}</el-descriptions-item>
              <el-descriptions-item label="电话">{{ lastExtracted.phone }}</el-descriptions-item>
              <el-descriptions-item label="年龄">{{ lastExtracted.age }} 岁</el-descriptions-item>
              <el-descriptions-item label="职业">{{ lastExtracted.occupation || '-' }}</el-descriptions-item>
              <el-descriptions-item label="收入">{{ lastExtracted.income || '-' }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </el-card>
      </el-col>

      <!-- 种子数据一键重置与导入 -->
      <el-col :xs="24" :lg="10">
        <el-card shadow="never" class="box-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">🌱 官方种子数据初始化</span>
            </div>
          </template>

          <div class="seed-desc">
            从后端配置的 <code>sql/seed_notices.json</code> 批量预置相亲角初始数据。
            <br />
            自动按手机号去重，已存在相同手机号的数据将自动跳过，保障已有数据不被破坏。
          </div>

          <el-alert
            title="提示：仅在系统刚搭建、需要快速充实相亲角公开展台卡片时使用。"
            type="info"
            show-icon
            :closable="false"
            style="margin-bottom: 20px;"
          />

          <el-button type="warning" :loading="seeding" @click="handleInitSeed">
            <el-icon><RefreshRight /></el-icon> 导入/更新官方种子数据
          </el-button>

          <div v-if="seedResult" class="seed-result">
            <el-alert
              :title="seedResult.msg"
              type="success"
              show-icon
              :closable="false"
            />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { extractAndImport, initSeedData } from '../../api'

const importText = ref('')
const importing = ref(false)
const lastExtracted = ref(null)

const seeding = ref(false)
const seedResult = ref(null)

const handleExtractAndImport = async () => {
  if (!importText.value.trim()) {
    ElMessage.warning('请先粘贴或输入相亲文本内容')
    return
  }

  importing.value = true
  try {
    const res = await extractAndImport(importText.value)
    if (res.code === 0 && res.data) {
      ElMessage.success('成功提取并入库相亲启事！')
      lastExtracted.value = res.data.extracted
      importText.value = ''
    }
  } catch (err) {
    console.error(err)
  } finally {
    importing.value = false
  }
}

const handleInitSeed = () => {
  ElMessageBox.confirm(
    '确认读取后端 seed_notices.json 导入初始启事吗？已有的重复手机号会自动跳过。',
    '种子数据导入',
    {
      type: 'warning',
      confirmButtonText: '确定导入',
      cancelButtonText: '取消'
    }
  ).then(async () => {
    seeding.value = true
    try {
      const res = await initSeedData()
      if (res.code === 0) {
        ElMessage.success(res.msg || '种子数据导入成功')
        seedResult.value = res
      }
    } catch (e) {
    } finally {
      seeding.value = false
    }
  }).catch(() => {})
}
</script>

<style scoped>
.import-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.box-card {
  border-radius: 8px;
  min-height: 480px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.import-tip {
  font-size: 13px;
  color: #606266;
  margin-bottom: 12px;
  line-height: 1.5;
}

.btn-group {
  margin-top: 16px;
  display: flex;
  gap: 12px;
}

.result-box {
  margin-top: 20px;
}

.seed-desc {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  margin-bottom: 16px;
}

.seed-result {
  margin-top: 20px;
}
</style>
