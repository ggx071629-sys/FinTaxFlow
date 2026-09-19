import { createSSRApp } from 'vue';
import App from './App.vue';
import { installH5Accessibility } from './utils/h5-accessibility';
// #ifdef H5
import { installWelcomeH5 } from './welcome/install-h5';
// #endif
export function createApp() {
  // #ifdef H5
  installH5Accessibility();
  installWelcomeH5();
  // #endif
  return { app: createSSRApp(App) };
}
