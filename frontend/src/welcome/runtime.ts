import { reactive } from 'vue';
import { session } from '../stores/session';

// Process memory only: logout, page navigation and component remounts do not reset it.
// A new H5 tab/reload or mini-program cold launch creates a fresh state.
export const welcome = reactive({
  phase: 'opening' as 'opening' | 'ready' | 'exiting' | 'done',
  targetReady: false,
  foreground: true,
  openingTime: 0,
  exitTime: 0
});
let restoredEntry = false;
export function welcomeDestination() {
  if (!session.token) return '/pages/login/index';
  return session.company ? '/pages/home/index' : '/pages/company/select';
}
export function prepareWelcomeTarget() {
  if (welcome.phase === 'done') return;
  const pages = getCurrentPages();
  const route = pages[pages.length - 1]?.route;
  if (!restoredEntry) {
    restoredEntry = true;
    // Only restore the default entry. Deep links continue through existing guards.
    if (route === 'pages/login/index' && session.token) {
      uni.reLaunch({
        url: welcomeDestination(),
        fail: () => {
          welcome.targetReady = true;
        }
      });
      return;
    }
  }
  welcome.targetReady = true;
}

export function beginWelcomeExit() {
  if (welcome.phase !== 'ready' || !welcome.targetReady) return false;
  welcome.phase = 'exiting'; // Synchronous lock, before any animation or nextTick.
  return true;
}
