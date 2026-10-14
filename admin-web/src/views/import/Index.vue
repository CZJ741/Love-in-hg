<template>
  <div class="import-container">
    <el-card shadow="never" class="box-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">📝 智能长文本提取与入库</span>
          <el-tag size="small" type="success">AI / 规则双引擎驱动</el-tag>
        </div>
      </template>

      <div class="import-tip">
        支持粘贴长文本、微信征婚群转发内容、个人自述。系统将智能抽取出姓名、性别、年龄、身高、体重、职业、收入、体制内判断、房产等字段。您可以<strong>先解析预览并进行二次人工校对修改</strong>，确认无误后再入库保存。
      </div>

      <el-input
        v-model="importText"
        type="textarea"
        :rows="7"
        placeholder="请在此粘贴非标准相亲文本，例如：&#10;女孩子96年冬天的，名字叫张晓雪，身高163，体重100斤。目前在黄冈市中心医院做编制内护士，在万达附近有套房。有意联系阿姨电话：13971786523..."
      />

      <div class="btn-group">
        <el-button type="primary" :loading="extracting" @click="handleExtractPreview">
          <el-icon><MagicStick /></el-icon> 智能解析提取（预览）
        </el-button>
        <el-button @click="fillSample">
          <el-icon><DocumentCopy /></el-icon> 填入示例测试文本
        </el-button>
        <el-button @click="clearAll">
          <el-icon><Delete /></el-icon> 清空
        </el-button>
      </div>
    </el-card>

    <!-- 提取预览与确认入库卡片 -->
    <el-card v-if="previewForm" shadow="never" class="preview-card">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span class="card-title">🔍 提取结果预览与校对</span>
            <el-tag v-if="isExisting" type="danger" style="margin-left: 10px;">
              ⚠️ 手机号已存在已有启事：{{ existingNotice?.name }} (ID: {{ existingNotice?.id }})
            </el-tag>
            <el-tag v-else type="info" style="margin-left: 10px;">
              可直接在表单中微调纠偏
            </el-tag>
          </div>
          <div>
            <el-button
              type="success"
              size="default"
              :disabled="isExisting"
              :loading="importing"
              @click="handleConfirmImport"
            >
              <el-icon><Check /></el-icon> 确认无误，正式入库
            </el-button>
          </div>
        </div>
      </template>

      <el-form :model="previewForm" label-width="100px" class="preview-form">
        <el-row :gutter="20">
          <el-col :xs="24" :sm="12" :md="8">
            <el-form-item label="姓名" required>
              <el-input v-model="previewForm.name" placeholder="提取姓名" />
            </el-form-item>
          </el-col>

          <el-col :xs="24" :sm="12" :md="8">
            <el-form-item label="性别" required>
              <el-radio-group v-model="previewForm.gender">
                <el-radio value="男">男</el-radio>
                <el-radio value="女">女</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>

          <el-col :xs="24" :sm="12" :md="8">
            <el-form-item label="手机号码">
              <el-input v-model="previewForm.phone" placeholder="提取手机号" />
            </el-form-item>
          </el-col>

          <el-col :xs="24" :sm="12" :md="8">
            <el-form-item label="年龄">
              <el-input-number v-model="previewForm.age" :min="0" :max="100" style="width: 100%" />
            </el-form-item>
          </el-col>

          <el-col :xs="24" :sm="12" :md="8">
            <el-form-item label="身高(cm)">
              <el-input-number v-model="previewForm.height" :min="0" :max="230" style="width: 100%" />
            </el-form-item>
          </el-col>

          <el-col :xs="24" :sm="12" :md="8">
            <el-form-item label="体重(斤)">
              <el-input-number v-model="previewForm.weight" :min="0" :max="300" style="width: 100%" />
            </el-form-item>
          </el-col>

          <el-col :xs="24" :sm="12" :md="8">
            <el-form-item label="发布人身份">
              <el-select v-model="previewForm.publisherRole" placeholder="发布身份" style="width: 100%">
                <el-option label="本人" value="本人" />
                <el-option label="父母" value="父母" />
                <el-option label="亲戚" value="亲戚" />
                <el-option label="朋友" value="朋友" />
              </el-select>
            </el-form-item>
          </el-col>

          <el-col :xs="24" :sm="12" :md="8">
            <el-form-item label="是否体制内">
              <el-switch
                v-model="previewForm.isPublicSector"
                active-text="体制内/编制"
                inactive-text="体制外"
              />
            </el-form-item>
          </el-col>

          <el-col :xs="24" :sm="12" :md="8">
            <el-form-item label="微信号/社交">
              <el-input v-model="previewForm.socialAccount" placeholder="微信号或社交号" />
            </el-form-item>
          </el-col>

          <el-col :xs="24" :sm="12" :md="12">
            <el-form-item label="职业工作">
              <el-input v-model="previewForm.occupation" placeholder="工作职业" />
            </el-form-item>
          </el-col>

          <el-col :xs="24" :sm="12" :md="12">
            <el-form-item label="月/年收入">
              <el-input v-model="previewForm.income" placeholder="收入状况" />
            </el-form-item>
          </el-col>

          <el-col :xs="24" :sm="24" :md="12">
            <el-form-item label="住房位置">
              <el-input v-model="previewForm.housingLocation" placeholder="住房位置" />
            </el-form-item>
          </el-col>

          <el-col :xs="24" :sm="24" :md="12">
            <el-form-item label="昵称/称呼">
              <el-input v-model="previewForm.nickname" placeholder="昵称或称呼" />
            </el-form-item>
          </el-col>

          <el-col :xs="24" :sm="24" :md="24">
            <el-form-item label="择偶/补充说明">
              <el-input
                v-model="previewForm.remark"
                type="textarea"
                :rows="3"
                placeholder="择偶标准及补充说明"
              />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
    </el-card>

    <!-- 最近一次入库成功展示 -->
    <el-card v-if="lastSavedNotice" shadow="never" class="success-card">
      <el-result
        icon="success"
        title="入库成功！"
        :sub-title="`启事 ID: ${lastSavedNotice.noticeId}，发布对象: ${lastSavedNotice.extracted?.name}`"
      >
        <template #extra>
          <el-button type="primary" @click="$router.push('/notice')">前往相亲启事列表查看</el-button>
          <el-button @click="lastSavedNotice = null">继续录入下一条</el-button>
        </template>
      </el-result>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { extractPreview, extractAndImport } from '../../api'

const router = useRouter()

const importText = ref('')
const extracting = ref(false)
const importing = ref(false)

const previewForm = ref(null)
const isExisting = ref(false)
const existingNotice = ref(null)
const lastSavedNotice = ref(null)

const sampleText = `【帮邻居阿姨家姑娘找对象】
女孩子96年冬天的，属鼠，名字叫张晓雪，人长得清秀白净，身高1米63，体重大概100斤出头。目前在黄冈市中心医院做编制内护士，工作稳定待遇不错，公积金社保都齐全。父母都在黄州城区开超市，家里在万达附近全款有套大三居。姑娘平时圈子比较小，性格文静贤惠，会做饭。
期望男方：黄冈本地人或者定居在黄冈，92-96年为佳，身高173以上，大专或本科学历，工作稳定有上进心，不抽烟少喝酒。
有意者请联系阿姨电话：13971786523，微信同号，非诚勿扰！`

const fillSample = () => {
  importText.value = sampleText
}

const clearAll = () => {
  importText.value = ''
  previewForm.value = null
  isExisting.value = false
  existingNotice.value = null
  lastSavedNotice.value = null
}

const handleExtractPreview = async () => {
  if (!importText.value.trim()) {
    ElMessage.warning('请先粘贴或输入相亲长文本内容')
    return
  }

  extracting.value = true
  lastSavedNotice.value = null
  try {
    const res = await extractPreview(importText.value)
    if (res.code === 0 && res.data) {
      const ext = res.data.extracted || {}
      previewForm.value = {
        name: ext.name || '',
        nickname: ext.nickname || '',
        gender: ext.gender || '男',
        age: ext.age ? Number(ext.age) : 0,
        phone: ext.phone || '',
        height: ext.height ? Number(ext.height) : 0,
        weight: ext.weight ? Number(ext.weight) : 0,
        publisherRole: ext.publisherRole || '本人',
        isPublicSector: Boolean(ext.isPublicSector),
        socialAccount: ext.socialAccount || '',
        occupation: ext.occupation || '',
        income: ext.income || '',
        housingLocation: ext.housingLocation || '本地',
        remark: ext.remark || ''
      }
      isExisting.value = Boolean(res.data.isExisting)
      existingNotice.value = res.data.existingNotice || null
      ElMessage.success('解析成功，请在下方预览并确认字段')
    } else {
      ElMessage.error(res.msg || '文本解析失败')
    }
  } catch (err) {
    ElMessage.error('解析服务异常，请重试')
  } finally {
    extracting.value = false
  }
}

const handleConfirmImport = async () => {
  if (!previewForm.value) return

  if (!previewForm.value.name.trim()) {
    ElMessage.warning('请填写姓名')
    return
  }
  if (!previewForm.value.gender) {
    ElMessage.warning('请选择性别')
    return
  }

  importing.value = true
  try {
    const res = await extractAndImport({ notice: previewForm.value })
    if (res.code === 0 && res.data) {
      ElMessage.success('成功入库相亲启事！')
      lastSavedNotice.value = res.data
      previewForm.value = null
      importText.value = ''
    } else {
      ElMessage.error(res.msg || '入库失败')
    }
  } catch (err) {
    ElMessage.error(err.response?.data?.msg || '入库失败，请检查手机号或内容')
  } finally {
    importing.value = false
  }
}
</script>

<style scoped>
.import-container {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.box-card, .preview-card, .success-card {
  border-radius: 8px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.import-tip {
  font-size: 13px;
  color: #606266;
  margin-bottom: 12px;
  line-height: 1.6;
}

.btn-group {
  margin-top: 16px;
  display: flex;
  gap: 12px;
}

.preview-card {
  border: 1px solid #e4e7ed;
}

.preview-form {
  margin-top: 8px;
}

.header-left {
  display: flex;
  align-items: center;
}
</style>
