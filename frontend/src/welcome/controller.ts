import { onUnmounted, watch } from 'vue';
import type { gsap } from 'gsap';
import { welcome, beginWelcomeExit } from './runtime';
import {
  createScene,
  settledScene,
  waitingScene,
  waitingTimeline,
  INTRO_SECONDS,
  WAITING_SWELL,
  WAITING_RIPPLE,
  openingTimeline,
  exitTimeline
} from './scene';

export function createWelcomeController(
  engine: typeof gsap,
  render: (s: ReturnType<typeof createScene>) => void,
  scope?: () => HTMLElement | undefined
) {
  const scene = createScene();
  let intro: gsap.core.Timeline | undefined;
  let outro: gsap.core.Timeline | undefined;
  let idle: gsap.core.Timeline | undefined;
  let reduced = false;
  let started = false;
  let ctx: gsap.Context;
  const paint = () => render(scene);
  function finishIntro() {
    if (reduced) settledScene(scene);
    welcome.openingTime = INTRO_SECONDS;
    welcome.phase = 'ready';
    paint();
    playIdle();
  }
  function playIdle() {
    if (reduced || welcome.phase !== 'ready') return;
    idle?.kill();
    ctx.add(() => {
      idle = waitingTimeline(engine, scene, paint);
      if (welcome.foreground) idle.play();
    });
  }
  function start(reduceMotion: boolean) {
    if (started || welcome.phase === 'done') return;
    started = true;
    reduced = reduceMotion;
    ctx = engine.context(() => {}, scope?.());
    ctx.add(() => {
      if (reduced || welcome.phase !== 'opening') {
        if (reduced) settledScene(scene);
        else waitingScene(scene);
        if (welcome.phase === 'opening') finishIntro();
        else if (welcome.phase === 'ready') playIdle();
        if (welcome.phase === 'exiting') playExit();
        paint();
        return;
      }
      intro = openingTimeline(
        engine,
        scene,
        () => {
          welcome.openingTime = intro?.time() || 0;
          paint();
        },
        finishIntro
      );
      intro.seek(welcome.openingTime);
      if (welcome.foreground) intro.play();
      paint();
    });
  }
  function playExit() {
    ctx.add(() => {
      intro?.kill();
      idle?.kill();
      // Keep the current liquid shape and clock when the surface starts releasing.
      if (reduced) {
        welcome.phase = 'done';
        return;
      }
      outro = exitTimeline(
        engine,
        scene,
        () => {
          welcome.exitTime = outro?.time() || 0;
          paint();
        },
        () => {
          welcome.phase = 'done';
        }
      );
      outro.seek(welcome.exitTime);
      if (welcome.foreground) outro.play();
    });
  }
  function proceed() {
    if (beginWelcomeExit()) playExit();
  }
  function setReducedMotion(value: boolean) {
    reduced = value;
    if (!value) {
      // A reduced-motion cold start has no displacement; ease it back in.
      if (started && welcome.phase === 'ready') {
        playIdle();
        idle?.to(
          scene,
          { swell: WAITING_SWELL, ripple: WAITING_RIPPLE, duration: 0.6, ease: 'power2.out' },
          0
        );
      }
      return;
    }
    intro?.kill();
    outro?.kill();
    idle?.kill();
    idle = undefined;
    if (welcome.phase === 'exiting') welcome.phase = 'done';
    else if (started && welcome.phase === 'opening') finishIntro();
    else paint();
  }
  const stop = watch(
    () => welcome.foreground,
    (active) => {
      const current =
        welcome.phase === 'opening' ? intro : welcome.phase === 'exiting' ? outro : idle;
      if (active) {
        current?.play();
        if (welcome.phase === 'ready') paint();
      } else current?.pause();
    },
    { flush: 'sync' }
  );
  onUnmounted(() => {
    stop();
    ctx?.revert();
  });
  return { start, proceed, setReducedMotion, repaint: paint };
}
