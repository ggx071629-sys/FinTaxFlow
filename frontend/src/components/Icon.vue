<script setup lang="ts">
defineProps<{ name: string; tone?: 'active' | 'muted' }>();
</script>
<template>
  <image
    class="ui-icon"
    :src="'/static/' + name + (tone ? '-' + tone : '') + '.svg'"
    mode="aspectFit"
    aria-hidden="true"
  />
</template>
