<script setup lang="ts">
import { computed, defineComponent, h, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import { gsap } from 'gsap';
import { welcome } from './runtime';
import { createWelcomeController } from './controller';
import { createLightCurtain } from './light-curtain';
import { WELCOME_LINES, WELCOME_TEXT, greetingPose, type Scene } from './scene';

const root = ref<HTMLElement>();
const canvasHost = ref<HTMLElement>();
// Render a native button explicitly: UniApp rewrites template <button> to uni-button.
const NativeButton = defineComponent({
  inheritAttrs: false,
  setup:
    (_, { attrs }) =>
    () =>
      h('button', attrs)
});
const ready = computed(() => welcome.phase === 'ready' && welcome.targetReady);
const fallback = ref(false);
const reduced = ref(false);
const keyboardFocus = ref(false);
let nodes: Record<string, HTMLElement> = {};
let renderer: ReturnType<typeof createLightCurtain>;
let width = 0,
  height = 0;
let observer: ResizeObserver;
let forceDraw = true;
const controller = createWelcomeController(gsap, paint, () => root.value);
function paint(s: Scene) {
  if (!root.value) return;
  const set = (name: string, values: Record<string, string>) => {
    for (const [key, value] of Object.entries(values)) {
      const style = nodes[name].style as unknown as Record<string, string>;
      if (style[key] !== value) style[key] = value;
    }
  };
  set('title', { opacity: `${s.textAlpha}` });
  WELCOME_LINES.forEach((_, index) => {
    const pose = greetingPose(s.entrance, index);
    set(`line${index}`, {
      opacity: `${pose.opacity}`
    });
  });
  set('hint', { opacity: `${s.hint}` });
  // The fallback is intentionally a simple fade, not a fake fluid simulation.
  set('fallback', { opacity: `${1 - Math.max(0, (s.exit - 0.32) / 0.68)}` });
  if (!fallback.value) {
    renderer?.draw(s, forceDraw);
    forceDraw = false;
  }
}
let media: MediaQueryList;
function motionChanged() {
  reduced.value = media.matches;
  forceDraw = true;
  controller.setReducedMotion(media.matches);
}
function visibility() {
  forceDraw = true;
  welcome.foreground = !document.hidden;
  if (document.hidden) {
    cancelPointer();
    key = undefined;
  }
}
function focusGuard(event: FocusEvent) {
  if (!root.value?.contains(event.target as Node)) root.value?.focus({ preventScroll: true });
}
// A gesture must begin AND end in the ready phase; moving or holding does not continue.
let pointer: { id: number; x: number; y: number; time: number; valid: boolean } | undefined;
let clickAllowed = false;
let key: { name: string; valid: boolean } | undefined;
function pointerDown(event: PointerEvent) {
  clickAllowed = false;
  keyboardFocus.value = false;
  if (pointer) {
    pointer.valid = false;
    return;
  }
  pointer = {
    id: event.pointerId,
    x: event.clientX,
    y: event.clientY,
    time: performance.now(),
    valid: ready.value && event.isPrimary && event.button === 0
  };
}
function pointerMove(event: PointerEvent) {
  if (pointer && Math.hypot(event.clientX - pointer.x, event.clientY - pointer.y) > 10)
    pointer.valid = false;
}
function pointerUp(event: PointerEvent) {
  clickAllowed =
    !!pointer &&
    pointer.id === event.pointerId &&
    pointer.valid &&
    ready.value &&
    performance.now() - pointer.time < 600 &&
    Math.hypot(event.clientX - pointer.x, event.clientY - pointer.y) <= 10;
  pointer = undefined;
}
function cancelPointer() {
  pointer = undefined;
  clickAllowed = false;
}
function activate(event: MouseEvent) {
  // detail=0 also supports screen-reader button activation, which has no pointer gesture.
  if (ready.value && (clickAllowed || (event.detail === 0 && !pointer && !key)))
    controller.proceed();
  clickAllowed = false;
}
function keyDown(event: KeyboardEvent) {
  keyboardFocus.value = true;
  if (event.key === 'Tab') {
    event.preventDefault();
    (ready.value ? nodes.continue : root.value)?.focus({ preventScroll: true });
  }
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    if (!key && !event.repeat) key = { name: event.key, valid: ready.value };
  }
}
function keyUp(event: KeyboardEvent) {
  if (event.key !== 'Enter' && event.key !== ' ') return;
  event.preventDefault();
  const allowed = key?.name === event.key && key.valid && ready.value;
  key = undefined;
  if (allowed) controller.proceed();
}
watch(ready, async (value) => {
  if (value) {
    await nextTick();
    nodes.continue?.focus({ preventScroll: true });
  }
});
onMounted(() => {
  const select = gsap.utils.selector(root.value!);
  for (const el of select('[data-layer]') as HTMLElement[]) nodes[el.dataset.layer!] = el;
  // Keep the H5 WebGL canvas out of UniApp's native canvas component transform.
  const canvas = document.createElement('canvas');
  canvas.setAttribute('aria-hidden', 'true');
  Object.assign(canvas.style, { width: '100%', height: '100%', display: 'block' });
  canvasHost.value!.appendChild(canvas);
  renderer = createLightCurtain(
    canvas,
    () => {
      fallback.value = true;
      if (width) controller.repaint();
    },
    window.devicePixelRatio
  );
  const resize = () => {
    const rect = root.value!.getBoundingClientRect();
    width = rect.width;
    height = rect.height;
    renderer?.resize(width, height);
    forceDraw = true;
    controller.repaint();
  };
  resize();
  observer = new ResizeObserver(resize);
  observer.observe(root.value!);
  media = window.matchMedia('(prefers-reduced-motion: reduce)');
  reduced.value = media.matches;
  media.addEventListener('change', motionChanged);
  document.addEventListener('visibilitychange', visibility);
  document.addEventListener('focusin', focusGuard);
  root.value!.focus({ preventScroll: true });
  visibility();
  controller.start(media.matches);
});
onUnmounted(() => {
  observer?.disconnect();
  renderer?.dispose();
  media?.removeEventListener('change', motionChanged);
  document.removeEventListener('visibilitychange', visibility);
  document.removeEventListener('focusin', focusGuard);
});
</script>

<template>
  <div
    ref="root"
    class="welcome-stage"
    :data-phase="welcome.phase"
    :data-renderer="fallback ? 'gradient' : 'webgl'"
    :data-reduced-motion="reduced"
    role="dialog"
    aria-modal="true"
    :aria-label="WELCOME_TEXT"
    tabindex="-1"
    @keydown="keyDown"
    @keyup="keyUp"
    @pointerdown.capture="pointerDown"
    @pointermove.capture="pointerMove"
    @pointerup.capture="pointerUp"
    @pointercancel="cancelPointer"
    @contextmenu.prevent
    @touchmove.stop.prevent
    @wheel.stop.prevent
  >
    <div
      ref="canvasHost"
      class="welcome-material"
      :class="{ 'is-hidden': fallback }"
      aria-hidden="true"
    ></div>
    <div
      class="welcome-fallback"
      data-layer="fallback"
      :class="{ 'is-hidden': !fallback }"
      aria-hidden="true"
    ></div>
    <div class="welcome-title-wrap" data-layer="title">
      <h1 class="welcome-title" :aria-label="WELCOME_TEXT">
        <span v-for="(line, index) in WELCOME_LINES" :key="line" :data-layer="`line${index}`">
          {{ line }}
        </span>
      </h1>
    </div>
    <div class="welcome-hint" data-layer="hint" aria-hidden="true">轻触屏幕继续</div>
    <NativeButton
      class="welcome-continue"
      :class="{ 'is-keyboard': keyboardFocus }"
      data-layer="continue"
      type="button"
      aria-label="轻触屏幕继续"
      :disabled="!ready"
      :tabindex="ready ? 0 : -1"
      :aria-hidden="!ready"
      @click.stop="activate"
    />
  </div>
</template>

<style>
.welcome-stage {
  position: fixed;
  inset: 0;
  width: 100%;
  max-width: 480px;
  height: 100%;
  height: 100dvh;
  margin-inline: auto;
  /* Mask only the desktop gutters; keep the center transparent during exit. */
  box-shadow: 0 0 0 100vmax var(--canvas, #f5f7fb);
  z-index: 2147483000;
  overflow: hidden;
  isolation: isolate;
  color: #174967;
  touch-action: none;
  outline: none;
  user-select: none;
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
}
.welcome-stage * {
  box-sizing: border-box;
}
.welcome-stage .is-hidden {
  visibility: hidden;
}
.welcome-material,
.welcome-fallback {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
.welcome-fallback {
  background:
    radial-gradient(ellipse at 20% 75%, #ddf5ef60, transparent 70%),
    linear-gradient(145deg, #eefaff, #c9e5f7 48%, #f4fcff);
}
.welcome-title-wrap {
  position: absolute;
  top: 46%;
  left: 50%;
  width: 84%;
  transform: translate(-50%, -50%);
  text-align: center;
  pointer-events: none;
}
.welcome-title {
  position: relative;
  margin: 0;
  font-size: min(11.8vw, 56.64px);
  font-weight: 600;
  line-height: 1.38;
  letter-spacing: 0.065em;
  color: #123e5b;
  text-shadow: 0 1px 16px #ffffff40;
}
.welcome-title span {
  display: block;
  white-space: nowrap;
  opacity: 0;
}
.welcome-title span:first-child {
  font-size: 0.42em;
  font-weight: 400;
  letter-spacing: 0.42em;
  text-indent: 0.42em;
  margin-bottom: 1.4em;
  color: #285674;
}
.welcome-title span:last-child {
  font-size: 0.76em;
  font-weight: 400;
  letter-spacing: 0.1em;
  margin-top: 0.3em;
  color: #204e6c;
}
.welcome-hint {
  position: absolute;
  left: 0;
  right: 0;
  bottom: max(11%, calc(env(safe-area-inset-bottom) + 32px));
  text-align: center;
  font-size: 12px;
  font-weight: 400;
  letter-spacing: 0.24em;
  color: #254f6c;
  pointer-events: none;
}
.welcome-continue {
  position: absolute;
  z-index: 10;
  inset: 0;
  display: block;
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  appearance: none;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  outline: none;
}
.welcome-continue:disabled {
  cursor: default;
}
.welcome-continue.is-keyboard:focus-visible {
  outline: 2px solid #205778;
  outline-offset: -8px;
}
@media (max-height: 500px) {
  .welcome-title-wrap {
    top: 43%;
  }
  .welcome-title {
    font-size: clamp(30px, 8vh, 42px);
    line-height: 1.2;
  }
  .welcome-title span:first-child {
    margin-bottom: 0.8em;
  }
  .welcome-hint {
    bottom: max(9%, calc(env(safe-area-inset-bottom) + 12px));
  }
}
</style>
