<script setup lang="ts">
import { statusLabels } from '../utils/format';
defineProps<{ status: string; text?: string }>();
</script>
<template>
  <text :class="['status-badge', status.toLowerCase()]">
    <text aria-hidden="true">
      {{
        ['SUCCESS', 'VERIFIED', 'COMPLETED'].includes(status)
          ? '✓ '
          : status === 'FAILED'
            ? '! '
            : '◷ '
      }}
    </text>
    {{ text || statusLabels[status] || status }}
  </text>
</template>
