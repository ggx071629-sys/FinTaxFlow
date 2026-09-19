import type { Scene } from './scene';

const vertexSource = `
attribute vec2 position;
varying vec2 uv;
void main() { uv = position * .5 + .5; gl_Position = vec4(position, 0., 1.); }
`;
// Seven overlapping wave sources refract a pale sky through a continuous water surface.
// Analytic slopes and curvature produce light concentration without blob silhouettes.
const fragmentSource = `
precision highp float;
varying vec2 uv;
uniform vec2 resolution;
uniform vec4 stage;
uniform float entrance;

struct Water {
  float height;
  vec2 slope;
  vec3 bend; // xx, xy, yy
};
Water wave(vec2 p, float index) {
  // Three wave regions (3 + 2 + 2 sources) have distinct directions and rhythms.
  float group=index<2.5 ? 0. : (index<4.5 ? 1. : 2.);
  float member=index-(group<.5 ? 0. : (group<1.5 ? 3. : 5.));
  float phase=group*1.65+member*.24;
  vec2 source=group<.5 ? vec2(-1.35,.9) : (group<1.5 ? vec2(1.35,.25) : vec2(-.25,-1.35));
  source+=vec2(sin(index*.8),cos(index*.65))*.09;
  source+=vec2(sin(stage.x*.16+group),cos(stage.x*.13+group))*.06;
  // Keep all three wave regions near the portrait canvas, not a desktop-sized field.
  source.x*=min(resolution.x/resolution.y,1.);
  vec2 d=p-source;
  float r=sqrt(dot(d,d)+.22);
  float frequency=4.3+group*.3+member*.09;
  // Opening currents travel briskly, then continuously ease into the waiting speed.
  float waterTime=stage.x+1.8*(1.-pow(1.-entrance,3.));
  float angle=r*frequency-waterTime*(.78+group*.13+member*.015)+phase;
  float birth=smoothstep(index*.022,index*.022+.70,entrance);
  float reach=entrance*(resolution.x/resolution.y+3.2);
  float arrival=smoothstep(-.45,.45,reach-r);
  float amplitude=(.060/(1.+member*1.4))*exp(-r*.42)*birth*arrival;
  float sn=sin(angle), cs=cos(angle);
  float first=amplitude*(frequency*cs-.42*sn);
  float second=amplitude*((.1764-frequency*frequency)*sn-.84*frequency*cs);
  float radial=first/r;
  float curvature=(second-radial)/(r*r);
  Water w;
  w.height=amplitude*sn;
  w.slope=radial*d;
  w.bend=curvature*vec3(d.x*d.x,d.x*d.y,d.y*d.y)+vec3(radial,0.,radial);
  return w;
}
// A finite opening swell travels across the surface before the idle waves take over.
// Its analytic profile contributes to the same lighting as the water, not an overlay wipe.
Water openingSwell(vec2 p, float index) {
  float aspect=resolution.x/resolution.y;
  vec2 source=index<.5 ? vec2(-aspect*.72,.62) :
    (index<1.5 ? vec2(aspect*.78,.14) : vec2(-aspect*.24,-.72));
  float progress=clamp((entrance-index*.045)/(1.-index*.045),0.,1.);
  vec2 d=p-source;
  float r=sqrt(dot(d,d)+.035);
  float front=.12+progress*(aspect+2.1);
  float q=r-front;
  float spread=.14;
  float envelope=sin(progress*3.14159265)*(1.-smoothstep(.65,1.,progress));
  float h=.14*envelope*exp(-q*q/spread);
  float first=h*(-2.*q/spread);
  float second=h*(4.*q*q/(spread*spread)-2./spread);
  float radial=first/r;
  float curvature=(second-radial)/(r*r);
  Water w;
  w.height=h;
  w.slope=radial*d;
  w.bend=curvature*vec3(d.x*d.x,d.x*d.y,d.y*d.y)+vec3(radial,0.,radial);
  return w;
}
// The second phrase crosses behind the greeting after the first three swells open.
// A pair of broad crests separates and softens into the waiting surface.
Water settlingSwell(vec2 p) {
  float progress=clamp((entrance-.36)/.64,0.,1.);
  vec2 d=p-vec2(.06,-.04);
  float r=sqrt(dot(d,d)+.045);
  float front=.10+progress*(resolution.x/resolution.y+1.65);
  float q=r-front;
  float spread=.18;
  float envelope=sin(progress*3.14159265)*(1.-smoothstep(.82,1.,progress));
  float h=.105*envelope*exp(-q*q/spread);
  float first=h*(-2.*q/spread);
  float second=h*(4.*q*q/(spread*spread)-2./spread);
  float radial=first/r;
  float curvature=(second-radial)/(r*r);
  Water w;
  w.height=h;
  w.slope=radial*d;
  w.bend=curvature*vec3(d.x*d.x,d.x*d.y,d.y*d.y)+vec3(radial,0.,radial);
  return w;
}
void main() {
  float aspect=resolution.x/resolution.y;
  vec2 p=(uv-.5)*vec2(aspect,1.)*2.;
  // The water opens from the greeting outward after the text has faded.
  vec2 outward=p-vec2(0.,.08);
  float radius=sqrt(dot(outward,outward)+.025);
  float release=smoothstep(.32,1.,stage.w);
  float front=radius-release*(aspect+1.8);
  float pulse=exp(-front*front/.24)*sin(release*3.14159265);
  p+=outward/radius*pulse*.12;
  float height=0.;
  vec2 slope=vec2(0.);
  vec3 bend=vec3(0.);
  float openingHeight=0.;
  vec2 openingSlope=vec2(0.);
  for(int i=0;i<7;i++) {
    Water w=wave(p,float(i));
    height+=w.height;
    slope+=w.slope;
    bend+=w.bend;
  }
  for(int i=0;i<3;i++) {
    Water w=openingSwell(p,float(i));
    height+=w.height;
    slope+=w.slope;
    bend+=w.bend*.45;
    openingHeight+=w.height;
    openingSlope+=w.slope;
  }
  Water settling=settlingSwell(p);
  height+=settling.height;
  slope+=settling.slope;
  bend+=settling.bend*.35;
  openingHeight+=settling.height;
  openingSlope+=settling.slope;
  // Light rays bend through the surface; curvature controls where they gather.
  vec2 refracted=p+slope*.42;
  vec3 normal=normalize(vec3(-slope*.85,1.));
  float jacobian=(1.+bend.x*1.05)*(1.+bend.z*1.05)-bend.y*bend.y*1.1025;
  // Keep the light narrow; roundness comes from coherent wave geometry, not blur.
  float caustic=exp(-jacobian*jacobian/.025);
  float wash=.5+.24*sin(refracted.x*.85+refracted.y*1.35)+normal.y*.2;
  vec3 color=mix(vec3(.69,.86,.96),vec3(.93,.98,1.),clamp(wash,0.,1.));
  float mint=smoothstep(.15,.9,sin(refracted.x*1.1-refracted.y*.8)*.5+.5);
  color=mix(color,vec3(.867,.961,.937),mint*.15);
  color*=1.-clamp(-height,0.,.10)*.38;
  // Broad opening folds need readable depth even before narrow caustics form.
  color=mix(color,vec3(.60,.80,.92),clamp(length(slope)*.30,0.,.20)*(1.-entrance));
  color*=1.-smoothstep(.8,3.,abs(jacobian))*.035;
  color=mix(color,vec3(.995,1.,1.),caustic*.64);
  // Broad moving highlights remain visible before the caustic threshold is reached.
  color=mix(color,vec3(.63,.82,.94),clamp(openingHeight*3.,0.,.36));
  color=mix(color,vec3(.995,1.,1.),clamp(length(openingSlope)*1.7,0.,.65));
  vec3 lamp=normalize(vec3(-.4,.55,1.));
  float glint=pow(max(dot(normal,normalize(lamp+vec3(0.,0.,1.))),0.),24.);
  color=mix(color,vec3(1.),glint*.11);
  color=mix(color,vec3(.98,1.,1.),pulse*.24);
  // Early ripples show promptly; there is no wipe or floating shape outline.
  color=mix(vec3(.95,.985,1.),color,smoothstep(0.,.22,entrance));
  // A broad, softly irregular release avoids both a hard iris edge and a flat crossfade.
  vec2 releasePosition=outward/vec2(aspect,1.);
  float distanceFromText=length(releasePosition)*.70;
  float contour=.045*sin(p.x*2.2+p.y*1.1)+.025*sin(p.y*2.8-p.x);
  float localRelease=release*1.6-(.10+distanceFromText*.52+contour);
  float alpha=1.-smoothstep(0.,.48,localRelease);
  gl_FragColor=vec4(color*alpha,alpha);
}
`;

// Both a browser canvas and the native WeChat canvas node implement this surface.
export interface WaterCanvas {
  width: number;
  height: number;
  getContext(type: 'webgl', options: WebGLContextAttributes): WebGLRenderingContext | null;
  addEventListener?: HTMLCanvasElement['addEventListener'];
  removeEventListener?: HTMLCanvasElement['removeEventListener'];
  dataset?: DOMStringMap;
}

export function createLightCurtain(canvas: WaterCanvas, fallback: () => void, pixelRatio = 1) {
  const gl = canvas.getContext('webgl', {
    alpha: true,
    premultipliedAlpha: true,
    antialias: false,
    depth: false,
    stencil: false,
    powerPreference: 'low-power',
    preserveDrawingBuffer: true
  });
  if (!gl) {
    fallback();
    return undefined;
  }
  const resources: WebGLShader[] = [];
  let program: WebGLProgram | null = null;
  let buffer: WebGLBuffer | null = null;
  let disposed = false;
  const dispose = () => {
    if (disposed) return;
    disposed = true;
    canvas.removeEventListener?.('webglcontextlost', lost);
    resources.forEach((shader) => gl.deleteShader(shader));
    if (buffer) gl.deleteBuffer(buffer);
    if (program) gl.deleteProgram(program);
  };
  const lost = (event: Event) => {
    event.preventDefault();
    dispose();
    fallback();
  };
  function shader(type: number, source: string) {
    const result = gl!.createShader(type);
    if (!result) throw new Error('Shader allocation failed');
    resources.push(result);
    gl!.shaderSource(result, source);
    gl!.compileShader(result);
    if (!gl!.getShaderParameter(result, gl!.COMPILE_STATUS))
      throw new Error('Shader compilation failed');
    return result;
  }
  try {
    program = gl.createProgram();
    if (!program) throw new Error('Program allocation failed');
    gl.attachShader(program, shader(gl.VERTEX_SHADER, vertexSource));
    gl.attachShader(program, shader(gl.FRAGMENT_SHADER, fragmentSource));
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error('Program linking failed');
    gl.useProgram(program);
    buffer = gl.createBuffer();
    if (!buffer) throw new Error('Buffer allocation failed');
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const position = gl.getAttribLocation(program, 'position');
    gl.enableVertexAttribArray(position);
    gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);
    const locations = Object.fromEntries(
      ['resolution', 'stage', 'entrance'].map((k) => [k, gl.getUniformLocation(program!, k)])
    );
    let lastDraw = -Infinity;
    let lastState = '';
    let width = 0,
      height = 0;
    let mobile = false;
    let draws = 0;
    canvas.addEventListener?.('webglcontextlost', lost);
    return {
      resize(w: number, h: number) {
        width = w;
        height = h;
        mobile = w < 900;
        const ratio = Math.min(pixelRatio || 1, 1.5);
        canvas.width = Math.round(w * ratio);
        canvas.height = Math.round(h * ratio);
        gl.viewport(0, 0, canvas.width, canvas.height);
        lastDraw = -Infinity;
        lastState = '';
      },
      draw(s: Scene, force = false) {
        if (disposed || !width || !height) return;
        const state = `${s.time}:${s.swell}:${s.ripple}:${s.exit}:${s.entrance}`;
        if (!force && state === lastState) return;
        const now = Date.now();
        const settled = s.swell === 0 && s.ripple === 0 && s.exit === 0;
        // Always draw the exact settled image, even inside the mobile frame budget.
        if (!force && !settled && mobile && now - lastDraw < 1000 / 30) return;
        lastState = state;
        lastDraw = now;
        gl.uniform2f(locations.resolution, width, height);
        gl.uniform4f(locations.stage, s.time, s.swell, s.ripple, s.exit);
        gl.uniform1f(locations.entrance, s.entrance);
        gl.drawArrays(gl.TRIANGLES, 0, 3);
        // Diagnostic counters make background suspension and render budgets testable.
        if (canvas.dataset) {
          canvas.dataset.frames = String(++draws);
          canvas.dataset.motion = (s.swell + s.ripple).toFixed(4);
          canvas.dataset.exit = s.exit.toFixed(4);
          canvas.dataset.entrance = s.entrance.toFixed(4);
        }
      },
      dispose
    };
  } catch {
    dispose();
    fallback();
    return undefined;
  }
}
