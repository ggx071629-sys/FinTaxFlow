<script setup lang="ts">
import { onLaunch } from '@dcloudio/uni-app';
import { restoreSession } from './stores/session';
// #ifdef H5
import { onShow, onHide } from '@dcloudio/uni-app';
import { welcome } from './welcome/runtime';
// #endif
onLaunch(restoreSession);
// #ifdef H5
onShow(() => {
  welcome.foreground = true;
});
onHide(() => {
  welcome.foreground = false;
});
// #endif
</script>
<style>
@import './styles/base.css';
</style>
