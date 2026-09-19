import { createApp, watch } from 'vue';
import WelcomeH5 from './WelcomeH5.vue';
import { welcome } from './runtime';

let installed = false;
export function installWelcomeH5() {
  if (installed || welcome.phase === 'done') return;
  installed = true;
  const business = document.getElementById('app')!;
  const previousInert = business.inert;
  const previousAria = business.getAttribute('aria-hidden');
  const previousOverflow = document.body.style.overflow;
  const previousFocus = document.activeElement as HTMLElement | null;
  business.inert = true;
  business.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = 'hidden';
  const host = document.createElement('div');
  host.id = 'welcome-host';
  document.body.appendChild(host);
  const app = createApp(WelcomeH5);
  app.mount(host);
  document.getElementById('welcome-boot')?.remove();
  let disposed = false;
  const stop = watch(
    () => welcome.phase,
    (phase) => {
      if (phase === 'done') dispose();
    }
  );
  function dispose() {
    if (disposed) return;
    disposed = true;
    stop();
    app.unmount();
    host.remove();
    business.inert = previousInert;
    if (previousAria === null) business.removeAttribute('aria-hidden');
    else business.setAttribute('aria-hidden', previousAria);
    document.body.style.overflow = previousOverflow;
    if (previousFocus?.isConnected) previousFocus.focus({ preventScroll: true });
  }
  if (import.meta.hot) import.meta.hot.dispose(dispose);
}
