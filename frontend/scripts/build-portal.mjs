import { cp, mkdir, readFile, writeFile } from 'node:fs/promises';
const root = new URL('../', import.meta.url),
  out = new URL('dist/portal/', root);
await mkdir(out, { recursive: true });
await cp(new URL('portal/', root), out, { recursive: true });
await mkdir(new URL('assets/', out), { recursive: true });
await cp(new URL('src/static/fintax_logo.jpg', root), new URL('assets/fintax_logo.jpg', out));
const html = await readFile(new URL('index.html', out), 'utf8');
await writeFile(
  new URL('index.html', out),
  html.replace('../src/static/fintax_logo.jpg', './assets/fintax_logo.jpg')
);
console.log('X01 built to dist/portal (no backend or business simulator)');
