import type { gsap } from 'gsap';

export const WELCOME_TEXT = '欢迎纵盟简税的各位老师';
export const WELCOME_LINES = ['欢迎', '纵盟简税', '的各位老师'];
export const INTRO_SECONDS = 3;
export const EXIT_SECONDS = 0.95;
export const WAITING_SWELL = 0.48;
export const WAITING_RIPPLE = 0.18;
export const FLOW_SPEED = 0.42;

// Fade each line gently into the opening water, without changing its shape.
export function greetingPose(entrance: number, line: number) {
  const lag = line * 0.035;
  const progress = Math.max(0, Math.min(1, (entrance - lag) / (1 - lag)));
  return {
    opacity: Math.max(0, Math.min(1, (progress - 0.04) / 0.60))
  };
}

// Liquid relief grows into view, then continues flowing beneath the stable greeting.
export function createScene() {
  return {
    time: 0,
    swell: WAITING_SWELL,
    ripple: WAITING_RIPPLE,
    entrance: 0,
    textAlpha: 1,
    hint: 0,
    exit: 0
  };
}
export type Scene = ReturnType<typeof createScene>;
export function settledScene(s: Scene) {
  Object.assign(s, {
    time: INTRO_SECONDS * FLOW_SPEED,
    swell: 0,
    ripple: 0,
    entrance: 1,
    textAlpha: 1,
    hint: 1,
    exit: 0
  });
}
export function waitingScene(s: Scene) {
  settledScene(s);
  s.swell = WAITING_SWELL;
  s.ripple = WAITING_RIPPLE;
}
export function waitingTimeline(engine: typeof gsap, s: Scene, update: () => void) {
  return (
    engine
      .timeline({ paused: true, onUpdate: update })
      // Refresh relative endpoints on repeat so the liquid clock never rewinds.
      .to(s, {
        time: '+=3600',
        duration: 3600 / FLOW_SPEED,
        ease: 'none',
        repeat: -1,
        repeatRefresh: true
      })
  );
}
export function openingTimeline(
  engine: typeof gsap,
  s: Scene,
  update: () => void,
  complete: () => void
) {
  return engine
    .timeline({ paused: true, onUpdate: update, onComplete: complete })
    .addLabel('liquid', 0)
    .to(s, { time: INTRO_SECONDS * FLOW_SPEED, duration: INTRO_SECONDS, ease: 'none' }, 0)
    // Keep the water advancing through the hint reveal, with no empty hold.
    .to(s, { entrance: 1, duration: INTRO_SECONDS, ease: 'none' }, 0)
    .to(s, { hint: 1, duration: 0.55, ease: 'power2.out' }, INTRO_SECONDS - 0.55)
    .addLabel('waiting', INTRO_SECONDS);
}
export function exitTimeline(
  engine: typeof gsap,
  s: Scene,
  update: () => void,
  complete: () => void
) {
  return engine
    .timeline({ paused: true, onUpdate: update, onComplete: complete })
    .addLabel('release', 0)
    .to(s, { time: `+=${FLOW_SPEED * EXIT_SECONDS}`, duration: EXIT_SECONDS, ease: 'none' }, 0)
    .to(s, { hint: 0, duration: 0.1, ease: 'power2.out' }, 0)
    .to(s, { textAlpha: 0, duration: 0.28, ease: 'power1.out' }, 0)
    // The shader shapes the release locally; a linear clock keeps the handoff predictable.
    .to(s, { exit: 1, duration: EXIT_SECONDS, ease: 'none' }, 0)
    .addLabel('removed', EXIT_SECONDS);
}
