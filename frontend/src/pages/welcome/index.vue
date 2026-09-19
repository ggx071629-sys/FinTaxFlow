<script setup lang="ts">
import { computed, getCurrentInstance, onUnmounted, ref, watch } from 'vue';
import { onHide, onLoad, onReady, onResize, onShow } from '@dcloudio/uni-app';
import { gsap } from 'gsap';
import { createWelcomeController } from '../../welcome/controller';
import { createNativeWelcomeScene, type NativeDisplayCanvas } from '../../welcome/native-scene';
import { welcome, welcomeDestination } from '../../welcome/runtime';
import { greetingPose, WELCOME_LINES, type Scene } from '../../welcome/scene';

const instance = getCurrentInstance();
const ready = computed(() => welcome.phase === 'ready');
const fallback = ref(false);
const reduced = ref(false);
const lineOpacity = ref([0, 0, 0]);
const hintOpacity = ref(0);
const fallbackOpacity = ref(1);
const navigationError = ref(false);
const fontSize = ref(46);
const safeTop = ref(24);
const safeBottom = ref(24);
const painted = ref(false);
let renderer: ReturnType<typeof createNativeWelcomeScene>;
let canvasWidth = 0,
  canvasHeight = 0;
let currentScene: Scene | undefined;
let mounted = false;
let disposed = false;
let navigating = false;
let lastPaint = 0;
let lastPhase = '';
type Action = 'reduce' | 'continue' | 'retry';
let touch: { x: number; y: number; time: number; valid: boolean; action?: Action } | undefined;
let gestureSeen = false;
let tapAction: Action | undefined;
type TouchEvent = {
  touches: ArrayLike<{ clientX: number; clientY: number }>;
  changedTouches: ArrayLike<{ clientX: number; clientY: number }>;
};

const controller = createWelcomeController(gsap, (scene: Scene) => {
  currentScene = scene;
  renderer?.draw(scene, reduced.value, navigationError.value);
  if (renderer) fallback.value = renderer.renderer === 'gradient';
  // Only bridge text changes while fading. The waiting water stays in the canvas.
  const now = Date.now();
  if (now - lastPaint < 1000 / 30 && lastPhase === welcome.phase) return;
  lastPaint = now;
  lastPhase = welcome.phase;
  const lines = WELCOME_LINES.map((_, i) =>
    Number((greetingPose(scene.entrance, i).opacity * scene.textAlpha).toFixed(3))
  );
  if (lines.some((alpha, i) => alpha !== lineOpacity.value[i])) lineOpacity.value = lines;
  hintOpacity.value = scene.hint;
  fallbackOpacity.value = 1 - Math.max(0, (scene.exit - 0.32) / 0.68);
});

function navigate() {
  if (navigating || disposed) return;
  navigating = true;
  navigationError.value = false;
  uni.reLaunch({
    url: welcomeDestination(),
    fail: () => {
      navigationError.value = true;
      if (currentScene) renderer?.draw(currentScene, reduced.value, true, true);
    },
    complete: () => {
      navigating = false;
    }
  });
}
watch(
  () => welcome.phase,
  (phase) => {
    if (phase === 'done') navigate();
  }
);
function reduceMotion() {
  reduced.value = true;
  controller.setReducedMotion(true);
  if (currentScene) renderer?.draw(currentScene, true, navigationError.value, true);
}
function hitsReduceMotion(x?: number, y?: number) {
  return (
    !reduced.value &&
    welcome.phase !== 'exiting' &&
    welcome.phase !== 'done' &&
    x !== undefined &&
    y !== undefined &&
    Math.abs(x - canvasWidth / 2) <= 80 &&
    y >= canvasHeight - safeBottom.value - 44 &&
    y <= canvasHeight - safeBottom.value
  );
}
function actionAt(x?: number, y?: number): Action | undefined {
  if (navigationError.value) return 'retry';
  if (hitsReduceMotion(x, y)) return 'reduce';
  if (ready.value) return 'continue';
}
function touchStart(event: TouchEvent) {
  gestureSeen = true;
  tapAction = undefined;
  const point = event.touches[0];
  if (touch || event.touches.length !== 1 || !point) {
    touchCancel();
    return;
  }
  touch = {
    x: point.clientX,
    y: point.clientY,
    time: Date.now(),
    valid: true,
    action: actionAt(point.clientX, point.clientY)
  };
}
function touchMove(event: TouchEvent) {
  const point = event.touches[0];
  if (
    touch &&
    (!point ||
      event.touches.length !== 1 ||
      Math.hypot(point.clientX - touch.x, point.clientY - touch.y) > 10)
  )
    touch.valid = false;
}
function touchEnd(event: TouchEvent) {
  const point = event.changedTouches[0];
  const allowed =
    touch?.valid &&
    point &&
    touch.action &&
    touch.action === actionAt(point.clientX, point.clientY) &&
    Date.now() - touch.time < 600 &&
    Math.hypot(point.clientX - touch.x, point.clientY - touch.y) <= 10;
  tapAction = allowed ? touch?.action : undefined;
  touch = undefined;
}
function touchCancel() {
  touch = undefined;
  tapAction = undefined;
  gestureSeen = true;
}
function activate(event?: { detail?: { x?: number; y?: number } }) {
  // An accessibility activation has no touch sequence; physical taps must pass it.
  const { x, y } = event?.detail || {};
  const action = gestureSeen ? tapAction : actionAt(x, y);
  if (action === 'retry') navigate();
  else if (action === 'reduce') reduceMotion();
  else if (action === 'continue') controller.proceed();
  gestureSeen = false;
  tapAction = undefined;
}
function canvasFailed() {
  fallback.value = true;
  renderer?.dispose();
  renderer = undefined;
  painted.value = false;
}
function measure(initial = false) {
  const system = uni.getSystemInfoSync();
  safeTop.value = Math.max(system.statusBarHeight || 0, 24);
  safeBottom.value = Math.max(system.safeAreaInsets?.bottom || 0, 24);
  uni
    .createSelectorQuery()
    .in(instance?.proxy)
    .select('#welcome-water')
    .fields({ node: true, size: true }, (result) => {
      if (disposed) return;
      const { node, width, height } = (result || {}) as {
        node?: NativeDisplayCanvas;
        width?: number;
        height?: number;
      };
      const w = width || system.windowWidth;
      const h = height || system.windowHeight;
      canvasWidth = w;
      canvasHeight = h;
      fontSize.value = h <= 500 ? Math.min(w * 0.118, h * 0.08, 42) : Math.min(w * 0.118, 56.64);
      if (initial) {
        try {
          renderer = node ? createNativeWelcomeScene(node, system.pixelRatio) : undefined;
        } catch {
          canvasFailed();
        }
        if (!renderer) fallback.value = true;
        painted.value = Boolean(renderer);
      }
      renderer?.resize(w, h, safeBottom.value);
      if (initial) {
        welcome.targetReady = true;
        controller.start(reduced.value);
      } else controller.repaint();
    })
    .exec();
}
onLoad(() => {
  if (welcome.phase === 'done') navigate();
});
onReady(() => {
  if (welcome.phase === 'done') return;
  mounted = true;
  measure(true);
});
onShow(() => {
  welcome.foreground = true;
});
onHide(() => {
  welcome.foreground = false;
  touch = undefined;
});
onResize(() => {
  if (mounted) measure();
});
onUnmounted(() => {
  disposed = true;
  renderer?.dispose();
});
</script>

<template>
  <view
    class="mp-welcome"
    :data-phase="welcome.phase"
    :data-renderer="fallback ? 'gradient' : 'webgl'"
    :data-compositor="painted ? 'canvas2d' : 'view'"
  >
    <view v-if="fallback" class="mp-fallback" :style="{ opacity: fallbackOpacity }" />
    <canvas
      id="welcome-water"
      type="2d"
      class="mp-water"
      :class="{ hidden: fallback && !painted }"
      :disable-scroll="true"
      aria-label="欢迎纵盟简税的各位老师"
      @error="canvasFailed"
      @touchstart="touchStart"
      @touchmove.stop.prevent="touchMove"
      @touchend="touchEnd"
      @touchcancel="touchCancel"
      @tap="activate"
    />
    <cover-view class="mp-greeting" :class="{ painted }" :style="{ fontSize: `${fontSize}px` }">
      <cover-view
        v-for="(line, i) in WELCOME_LINES"
        :key="line"
        class="mp-line"
        :style="{ opacity: lineOpacity[i] }"
      >
        {{ line }}
      </cover-view>
    </cover-view>
    <cover-view
      class="mp-hint"
      :class="{ painted }"
      :style="{ opacity: hintOpacity, bottom: `max(11%, ${safeBottom + 32}px)` }"
    >
      轻触屏幕继续
    </cover-view>
    <cover-view
      class="mp-touch"
      @touchstart="touchStart"
      @touchmove.stop.prevent="touchMove"
      @touchend="touchEnd"
      @touchcancel="touchCancel"
    >
      <button class="mp-continue" :disabled="!ready" aria-label="轻触屏幕继续" @tap="activate" />
    </cover-view>
    <cover-view
      v-if="!reduced && welcome.phase !== 'exiting' && welcome.phase !== 'done'"
      class="mp-reduce-wrap"
      :class="{ painted }"
      :style="{ bottom: `${safeBottom}px` }"
    >
      <button class="mp-reduce" aria-label="减少动态效果" @tap.stop="reduceMotion">
        减少动态效果
      </button>
    </cover-view>
    <cover-view
      v-if="navigationError"
      class="mp-error"
      :class="{ painted }"
      :style="{ paddingTop: `${safeTop}px` }"
    >
      <cover-view>页面暂时未能打开，请重试</cover-view>
      <button @tap="navigate">重新进入</button>
    </cover-view>
  </view>
</template>

<style>
.mp-welcome {
  position: fixed;
  inset: 0;
  overflow: hidden;
  background: #f5f7fb;
  color: #123e5b;
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
}
.mp-water,
.mp-fallback,
.mp-touch {
  position: fixed;
  inset: 0;
  width: 100%;
  height: 100%;
}
.mp-water {
  z-index: 0;
}
.mp-water.hidden {
  visibility: hidden;
}
/* Keep native semantics and tap targets; pixels are composed above the water. */
.mp-greeting.painted .mp-line,
.mp-hint.painted,
.mp-reduce-wrap.painted .mp-reduce,
.mp-error.painted,
.mp-error.painted button {
  color: transparent;
}
.mp-error.painted,
.mp-error.painted button {
  background: transparent;
}
.mp-fallback {
  background:
    radial-gradient(ellipse at 20% 75%, #ddf5ef60, transparent 70%),
    linear-gradient(145deg, #eefaff, #c9e5f7 48%, #f4fcff);
}
.mp-greeting {
  position: fixed;
  z-index: 1;
  top: 46%;
  left: 8%;
  width: 84%;
  transform: translateY(-50%);
  text-align: center;
  pointer-events: none;
}
.mp-line {
  display: block;
  font-weight: 600;
  line-height: 1.38;
  letter-spacing: 0.065em;
  white-space: nowrap;
}
.mp-line:first-child {
  font-size: 0.42em;
  font-weight: 400;
  letter-spacing: 0.42em;
  text-indent: 0.42em;
  margin-bottom: 1.4em;
  color: #285674;
}
.mp-line:last-child {
  font-size: 0.76em;
  font-weight: 400;
  letter-spacing: 0.1em;
  margin-top: 0.3em;
  color: #204e6c;
}
.mp-hint {
  position: fixed;
  z-index: 1;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 12px;
  letter-spacing: 0.24em;
  color: #254f6c;
}
.mp-continue {
  position: fixed;
  inset: 0;
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 0;
  border: 0;
  background: transparent !important;
}
.mp-continue::after,
.mp-reduce::after {
  border: 0;
}
.mp-touch {
  z-index: 2;
}
.mp-reduce-wrap {
  position: fixed;
  z-index: 3;
  left: 50%;
  transform: translateX(-50%);
}
.mp-reduce {
  min-height: 44px;
  padding: 0 16px;
  background: transparent;
  color: #285674;
  font-size: 12px;
  line-height: 44px;
}
.mp-error {
  position: fixed;
  z-index: 4;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 24px;
  background: #edfaff;
}
@media (max-height: 500px) {
  .mp-greeting {
    top: 43%;
  }
  .mp-line {
    line-height: 1.2;
  }
  .mp-line:first-child {
    margin-bottom: 0.8em;
  }
}
</style>
