<template>
  <div class="user-container">
    <!-- 筛选 -->
    <el-card shadow="never" class="filter-card">
      <el-form :inline="true" :model="query" class="filter-form">
        <el-form-item label="搜索用户">
          <el-input
            v-model="query.keyword"
            placeholder="输入手机号 / 姓名"
            clearable
            style="width: 220px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>

        <el-form-item label="会员类型">
          <el-select v-model="query.membershipType" placeholder="全部类型" clearable style="width: 140px">
            <el-option label="普通用户" value="free" />
            <el-option label="月度会员" value="member" />
            <el-option label="年度大会员" value="vip" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon> 搜索
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon> 重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 用户列表 -->
    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <span class="total-text">共登记用户 {{ total }} 名</span>
      </div>

      <el-table :data="list" v-loading="loading" border stripe style="width: 100%">
        <el-table-column prop="id" label="UID" width="70" align="center" />

        <el-table-column prop="phone" label="手机号码" min-width="130" align="center">
          <template #default="{ row }">
            <span class="phone-text">{{ row.phone }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="name" label="姓名" min-width="110" align="center">
          <template #default="{ row }">
            <span>{{ row.name || '未填真实姓名' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="性别/年龄" min-width="100" align="center">
          <template #default="{ row }">
            <span>{{ row.gender || '-' }}</span>
            <span v-if="row.birthday"> ({{ row.birthday }})</span>
          </template>
        </el-table-column>

        <el-table-column prop="membershipType" label="当前会员身份" min-width="130" align="center">
          <template #default="{ row }">
            <el-tag :type="memberTagType(row.membershipType)" effect="dark">
              {{ memberLabel(row.membershipType) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="membershipExpire" label="会员到期时间" min-width="150" align="center">
          <template #default="{ row }">
            <span v-if="row.membershipExpire" class="expire-text">{{ formatExpire(row.membershipExpire) }}</span>
            <span v-else style="color: #c0c4cc;">永久/免费</span>
          </template>
        </el-table-column>

        <el-table-column label="已查看配额(本月/日)" min-width="140" align="center">
          <template #default="{ row }">
            <span>本月: {{ row.monthlyNoticeCount || 0 }} | 今日: {{ row.dailyNoticeCount || 0 }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="publishedCount" label="已发布启事" width="100" align="center">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ row.publishedCount || 0 }} 篇</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleOpenMemberDialog(row)">
              修改会员
            </el-button>
            <el-button type="warning" link size="small" @click="handleOpenQuotaDialog(row)">
              调整配额
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-box">
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchData"
          @current-change="fetchData"
        />
      </div>
    </el-card>

    <!-- 会员身份修改弹窗 -->
    <el-dialog v-model="memberDialogVisible" title="手动调整会员等级与到期时间" width="460px">
      <el-form :model="memberForm" label-width="100px">
        <el-form-item label="用户手机">
          <el-input :value="currentUser.phone" disabled />
        </el-form-item>
        <el-form-item label="会员等级">
          <el-radio-group v-model="memberForm.membershipType">
            <el-radio label="free">普通用户</el-radio>
            <el-radio label="member">月度会员</el-radio>
            <el-radio label="vip">大会员</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="到期日期" v-if="memberForm.membershipType !== 'free'">
          <el-date-picker
            v-model="memberForm.membershipExpire"
            type="date"
            placeholder="选择到期日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="快捷续期" v-if="memberForm.membershipType !== 'free'">
          <el-button-group>
            <el-button size="small" @click="addDays(30)">+30天</el-button>
            <el-button size="small" @click="addDays(90)">+3个月</el-button>
            <el-button size="small" @click="addDays(365)">+1年</el-button>
          </el-button-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="memberDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSaveMember">确认保存</el-button>
      </template>
    </el-dialog>

    <!-- 配额调整弹窗 -->
    <el-dialog v-model="quotaDialogVisible" title="调整/重置用户已查看配额" width="420px">
      <el-form :model="quotaForm" label-width="110px">
        <el-form-item label="本月已看数">
          <el-input-number v-model="quotaForm.monthlyNoticeCount" :min="0" :max="999" />
          <div class="tip-sub">设为 0 即完全清零重置当月消耗</div>
        </el-form-item>
        <el-form-item label="今日已看数">
          <el-input-number v-model="quotaForm.dailyNoticeCount" :min="0" :max="999" />
          <div class="tip-sub">设为 0 即完全清零今日消耗</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="quotaDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSaveQuota">确认调整</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getUsers, updateUserMembership, updateUserQuota } from '../../api'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const saving = ref(false)

const query = reactive({
  page: 1,
  pageSize: 10,
  keyword: '',
  membershipType: ''
})

const currentUser = ref({})
const memberDialogVisible = ref(false)
const memberForm = reactive({
  membershipType: 'free',
  membershipExpire: ''
})

const quotaDialogVisible = ref(false)
const quotaForm = reactive({
  monthlyNoticeCount: 0,
  dailyNoticeCount: 0
})

const memberLabel = (type) => {
  const map = { free: '普通用户', member: '月度会员', vip: '大会员' }
  return map[type] || '普通用户'
}

const memberTagType = (type) => {
  const map = { free: 'info', member: 'primary', vip: 'warning' }
  return map[type] || 'info'
}

const formatExpire = (str) => {
  if (!str) return '-'
  return str.split('T')[0].split(' ')[0]
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getUsers(query)
    if (res.code === 0 && res.data) {
      list.value = res.data.list || []
      total.value = res.data.total || 0
    }
  } catch (err) {
    console.error(err)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  query.page = 1
  fetchData()
}

const handleReset = () => {
  query.keyword = ''
  query.membershipType = ''
  handleSearch()
}

const handleOpenMemberDialog = (row) => {
  currentUser.value = row
  memberForm.membershipType = row.membershipType || 'free'
  memberForm.membershipExpire = row.membershipExpire ? formatExpire(row.membershipExpire) : ''
  memberDialogVisible.value = true
}

const addDays = (days) => {
  const base = memberForm.membershipExpire ? new Date(memberForm.membershipExpire) : new Date()
  base.setDate(base.getDate() + days)
  const y = base.getFullYear()
  const m = String(base.getMonth() + 1).padStart(2, '0')
  const d = String(base.getDate()).padStart(2, '0')
  memberForm.membershipExpire = `${y}-${m}-${d}`
}

const handleSaveMember = async () => {
  saving.value = true
  try {
    const res = await updateUserMembership(currentUser.value.id, memberForm)
    if (res.code === 0) {
      ElMessage.success('会员信息已更新')
      memberDialogVisible.value = false
      fetchData()
    }
  } catch (e) {
  } finally {
    saving.value = false
  }
}

const handleOpenQuotaDialog = (row) => {
  currentUser.value = row
  quotaForm.monthlyNoticeCount = row.monthlyNoticeCount || 0
  quotaForm.dailyNoticeCount = row.dailyNoticeCount || 0
  quotaDialogVisible.value = true
}

const handleSaveQuota = async () => {
  saving.value = true
  try {
    const res = await updateUserQuota(currentUser.value.id, quotaForm)
    if (res.code === 0) {
      ElMessage.success('配额已重置更新')
      quotaDialogVisible.value = false
      fetchData()
    }
  } catch (e) {
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.user-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.filter-card, .table-card {
  border-radius: 8px;
}

.filter-form .el-form-item {
  margin-bottom: 0;
  margin-right: 16px;
}

.table-toolbar {
  margin-bottom: 16px;
  display: flex;
  justify-content: flex-end;
}

.total-text {
  font-size: 13px;
  color: #909399;
}

.phone-text {
  font-family: monospace;
  font-weight: 500;
}

.expire-text {
  font-size: 13px;
  color: #606266;
}

.pagination-box {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.tip-sub {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
  margin-top: 4px;
}
</style>
