import { createLightCurtain, type WaterCanvas } from './light-curtain';
import { greetingPose, WELCOME_LINES, type Scene } from './scene';

export interface NativeDisplayCanvas {
  width: number;
  height: number;
  getContext(type: '2d'): CanvasRenderingContext2D | null;
}

// Compose the greeting after the water in one visible native surface. Native
// WebGL layers can cover even cover-view in the developer tools compositor.
export function createNativeWelcomeScene(canvas: NativeDisplayCanvas, pixelRatio: number) {
  const context = canvas.getContext('2d');
  if (!context) return undefined;
  const ctx = context;
  const ratio = Math.min(pixelRatio || 1, 1.5);
  let water: ReturnType<typeof createLightCurtain>;
  let offscreen: WaterCanvas | undefined;
  let width = 0,
    height = 0,
    bottom = 24;
  let lastDraw = -Infinity;
  let lastKey = '';
  let disposed = false;
  let gradient: CanvasGradient;

  function stopWater() {
    water?.dispose();
    water = undefined;
  }
  try {
    offscreen = uni.createOffscreenCanvas({
      type: 'webgl',
      width: 1,
      height: 1
    }) as unknown as WaterCanvas;
    water = createLightCurtain(offscreen, stopWater, ratio);
  } catch {
    stopWater();
  }

  function text(
    value: string,
    size: number,
    y: number,
    color: string,
    weight: number,
    spacing: number,
    alpha = 1
  ) {
    ctx.globalAlpha = alpha;
    ctx.fillStyle = color;
    ctx.font = `${weight} ${size}px sans-serif`;
    ctx.textBaseline = 'middle';
    const letters = Array.from(value);
    const advances = letters.map((letter) => ctx.measureText(letter).width);
    let x = (width - advances.reduce((sum, n) => sum + n, 0) - spacing * (letters.length - 1)) / 2;
    letters.forEach((letter, i) => {
      ctx.fillText(letter, x, y);
      x += advances[i] + spacing;
    });
  }

  return {
    resize(w: number, h: number, safeBottom: number) {
      width = w;
      height = h;
      bottom = safeBottom;
      canvas.width = Math.round(w * ratio);
      canvas.height = Math.round(h * ratio);
      ctx.scale(ratio, ratio);
      gradient = ctx.createLinearGradient(0, 0, w, h);
      gradient.addColorStop(0, '#eefaff');
      gradient.addColorStop(0.48, '#c9e5f7');
      gradient.addColorStop(1, '#f4fcff');
      water?.resize(w, h);
      lastDraw = -Infinity;
      lastKey = '';
    },
    draw(scene: Scene, reduced: boolean, navigationError: boolean, force = false) {
      if (disposed || !width || !height) return;
      const key = `${scene.time}:${scene.entrance}:${scene.textAlpha}:${scene.hint}:${scene.exit}:${reduced}:${navigationError}`;
      const now = Date.now();
      if (!force && (key === lastKey || now - lastDraw < 1000 / 30)) return;
      lastDraw = now;
      lastKey = key;
      ctx.globalAlpha = 1;
      ctx.clearRect(0, 0, width, height);
      if (water && offscreen) {
        try {
          water.draw(scene, true);
          ctx.drawImage(offscreen as unknown as CanvasImageSource, 0, 0, width, height);
        } catch {
          stopWater();
        }
      }
      if (!water) {
        ctx.globalAlpha = 1 - Math.max(0, (scene.exit - 0.32) / 0.68);
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, width, height);
      }
      const compact = height <= 500;
      const font = compact
        ? Math.min(width * 0.118, height * 0.08, 42)
        : Math.min(width * 0.118, 56.64);
      const sizes = [font * 0.42, font, font * 0.76];
      const lineHeight = compact ? 1.2 : 1.38;
      const gaps = [sizes[0] * (compact ? 0.8 : 1.4), sizes[2] * 0.3];
      const total = sizes.reduce((sum, size) => sum + size * lineHeight, 0) + gaps[0] + gaps[1];
      let y = height * (compact ? 0.43 : 0.46) - total / 2;
      WELCOME_LINES.forEach((line, i) => {
        text(
          line,
          sizes[i],
          y + (sizes[i] * lineHeight) / 2,
          ['#285674', '#123e5b', '#204e6c'][i],
          i === 1 ? 600 : 400,
          sizes[i] * [0.42, 0.065, 0.1][i],
          greetingPose(scene.entrance, i).opacity * scene.textAlpha
        );
        y += sizes[i] * lineHeight + (gaps[i] || 0);
      });
      text(
        '轻触屏幕继续',
        12,
        height - Math.max(height * 0.11, bottom + 32) - 9,
        '#254f6c',
        400,
        2.88,
        scene.hint
      );
      if (!reduced && scene.exit === 0)
        text('减少动态效果', 12, height - bottom - 22, '#285674', 400, 0);
      if (navigationError) {
        ctx.globalAlpha = 1;
        ctx.fillStyle = '#edfaff';
        ctx.fillRect(0, 0, width, height);
        text('页面暂时未能打开，请重试', 16, height / 2 - 24, '#123e5b', 400, 0);
        text('重新进入', 16, height / 2 + 24, '#123e5b', 600, 0);
      }
      ctx.globalAlpha = 1;
    },
    get renderer() {
      return water ? 'webgl' : 'gradient';
    },
    stopWater,
    dispose() {
      disposed = true;
      stopWater();
      if (offscreen) {
        offscreen.width = 1;
        offscreen.height = 1;
      }
    }
  };
}
