<script setup lang="ts">
import { ref, watch } from 'vue';
import { onLoad, onShow } from '@dcloudio/uni-app';
import { extension } from '../../api/extension';
import { useResource } from '../../composables/resource';
import { useCommand } from '../../composables/command';
import { go, guard } from '../../utils/navigation';
import { session } from '../../stores/session';
import { dateTime } from '../../utils/format';
import AppShell from '../../components/AppShell.vue';
import CompanyBar from '../../components/CompanyBar.vue';
import StatePanel from '../../components/StatePanel.vue';
import StatusBadge from '../../components/StatusBadge.vue';
import Timeline from '../../components/Timeline.vue';
import CountStrip from '../../components/CountStrip.vue';
import ModalSheet from '../../components/ModalSheet.vue';
const id = ref(''),
  confirm = ref(false);
onLoad((q) => {
  id.value = q?.id || '';
});
const { data, busy, error, load } = useResource(() => extension.task(id.value));
const command = useCommand('recover-declaration');
watch(
  () => session.epoch,
  () => {
    confirm.value = false;
  }
);
onShow(() => {
  if (guard()) load();
});
async function recover() {
  if (!data.value?.declaration_id) return;
  const declaration = data.value.declaration_id;
  const result = await command.run({ declaration_id: declaration }, (key) =>
    extension.recover(declaration, key)
  );
  if (result) {
    confirm.value = false;
    data.value = result;
  }
}
</script>
<template>
  <AppShell :title="data?.kind === 'DECLARATION' ? '申报任务详情' : '任务详情'" fallback="tasks">
    <view class="extension-page">
      <CompanyBar />
      <StatePanel :busy="busy" :error="error" @retry="load">
        <template v-if="data">
          <view class="card">
            <view class="row between wrap">
              <text class="caption">{{ data.number }}</text>
              <StatusBadge :status="data.status" />
            </view>
            <text class="list-title" style="font-size: 20px">{{ data.title }}</text>
            <text class="caption">{{ dateTime(data.created_at) }}</text>
            <template v-if="data.kind === 'DECLARATION'">
              <text class="caption" style="display: block">
                {{ data.submitted ? '已提交表单' : '尚未提交表单' }} ·
                {{ data.receipt_id ? '回执已归档' : '回执尚未获取' }}
              </text>
              <view class="progress-track">
                <view
                  :style="{
                    width: `${data.total_steps ? ((data.completed_steps || 0) / data.total_steps) * 100 : 0}%`
                  }"
                />
              </view>
              <text class="caption">
                {{ data.completed_steps || 0 }} / {{ data.total_steps || 0 }} 个步骤已完成
              </text>
            </template>
            <CountStrip
              v-else
              :items="[
                { label: '处理总数', value: data.counts.total },
                { label: '成功', value: data.counts.success, tone: 'good' },
                { label: '失败', value: data.counts.failed, tone: 'bad' }
              ]"
            />
          </view>
          <text v-if="data.status === 'WAITING_RECOVERY'" class="notice warning">
            {{
              data.submitted ? '表单已经提交，获取回执时连接中断。' : '任务需要恢复。'
            }}恢复时将先核对已有申报记录，不重复提交。
          </text>
          <text v-if="data.failure_reason" class="notice error" role="alert">
            {{ data.failure_reason }}
          </text>
          <text v-if="data.sources.length" class="section-title">输入来源</text>
          <view v-if="data.sources.length" class="card">
            <view v-for="(source, index) in data.sources" :key="index" class="task-source">
              <text>{{ source.label }}</text>
              <text class="caption">
                {{ source.file_name }} {{ source.row_number ? `· 第 ${source.row_number} 行` : '' }}
              </text>
              <text v-if="source.import_id" class="caption">导入记录 {{ source.import_id }}</text>
            </view>
          </view>
          <text class="section-title">
            {{ data.kind === 'DECLARATION' ? '执行过程' : '事件记录' }}
          </text>
          <view class="card">
            <Timeline :events="data.events" />
            <text v-if="!data.events.length" class="caption">暂无执行节点，请稍后刷新</text>
          </view>
          <view class="card">
            <view class="detail-row">
              <text>所属企业</text>
              <text>{{ session.company?.name }}</text>
            </view>
            <view v-if="data.period" class="detail-row">
              <text>所属期间</text>
              <text>{{ data.period }}</text>
            </view>
            <view v-if="data.acceptance_number" class="detail-row">
              <text>受理编号</text>
              <text>{{ data.acceptance_number }}</text>
            </view>
            <view v-if="data.submission_count !== undefined" class="detail-row">
              <text>申报次数</text>
              <text>{{ data.submission_count }} 次</text>
            </view>
          </view>
          <text v-if="command.error.value" class="notice error" role="alert">
            {{ command.error.value }}
          </text>
          <view class="button-row extension-actions">
            <button
              class="ft-button secondary"
              :disabled="busy || command.busy.value"
              @click="load"
            >
              刷新进度
            </button>
            <button
              v-if="['WAITING_RECOVERY', 'FAILED'].includes(data.status) && data.declaration_id"
              class="ft-button primary"
              :disabled="command.busy.value"
              @click="confirm = true"
            >
              恢复任务并获取回执
            </button>
            <button
              v-else-if="data.receipt_id"
              class="ft-button primary"
              @click="go('receipt', { id: data.receipt_id })"
            >
              查看回执
            </button>
            <button
              v-else-if="data.batch_id"
              class="ft-button primary"
              @click="go('batch', { id: data.batch_id })"
            >
              查看批次明细
            </button>
            <button
              v-else-if="data.reconciliation_id"
              class="ft-button primary"
              @click="go('reconciliation', { id: data.reconciliation_id })"
            >
              查看对账结果
            </button>
          </view>
        </template>
      </StatePanel>
      <ModalSheet
        :open="confirm"
        title="确认恢复申报任务"
        :busy="command.busy.value"
        @close="confirm = false"
      >
        <text class="list-title">{{ session.company?.name }} · {{ data?.period }}</text>
        <text class="notice warning">
          先核对同企业、期间及业务标识对应的申报记录。已受理则沿用原编号补取回执；尚未受理才重新操作表单，不重复提交。
        </text>
        <text v-if="command.error.value" class="notice error">{{ command.error.value }}</text>
        <view class="button-row">
          <button
            class="ft-button secondary"
            :disabled="command.busy.value"
            @click="confirm = false"
          >
            取消
          </button>
          <button
            class="ft-button primary"
            :disabled="command.busy.value"
            :loading="command.busy.value"
            @click="recover"
          >
            确认恢复任务
          </button>
        </view>
      </ModalSheet>
    </view>
  </AppShell>
</template>
