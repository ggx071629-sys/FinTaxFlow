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
  // Lock the scrolling root and constrain the underlying UniApp page. Body-only
  // overflow leaves a tall document visible below a viewport-sized welcome layer.
  const locked: Array<[HTMLElement, string, string, string]> = [];
  function lock(element: HTMLElement, properties: Record<string, string>) {
    for (const [key, value] of Object.entries(properties)) {
      locked.push([element, key, element.style.getPropertyValue(key), element.style.getPropertyPriority(key)]);
      element.style.setProperty(key, value);
    }
  }
  const scrollPosition = { x: window.scrollX, y: window.scrollY };
  lock(document.documentElement, { overflow: 'hidden', height: '100%' });
  lock(document.body, { overflow: 'hidden', height: '100%' });
  lock(business, { position: 'fixed', inset: '0', overflow: 'hidden' });
  const previousFocus = document.activeElement as HTMLElement | null;
  business.inert = true;
  business.setAttribute('aria-hidden', 'true');
  const host = document.createElement('div');
  host.id = 'welcome-host';
  Object.assign(host.style, { position: 'fixed', inset: '0', zIndex: '2147483000', overflow: 'hidden' });
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
    for (const [element, key, value, priority] of locked) {
      if (value) element.style.setProperty(key, value, priority);
      else element.style.removeProperty(key);
    }
    window.scrollTo(scrollPosition.x, scrollPosition.y);
    if (previousFocus?.isConnected) previousFocus.focus({ preventScroll: true });
  }
  if (import.meta.hot) import.meta.hot.dispose(dispose);
}
