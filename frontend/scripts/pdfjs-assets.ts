import { createReadStream, existsSync, readdirSync, readFileSync } from 'node:fs';
import { dirname, extname, resolve, sep } from 'node:path';
import { createRequire } from 'node:module';
import type { Plugin } from 'vite';
const require = createRequire(import.meta.url);
const root = dirname(require.resolve('pdfjs-dist/package.json'));
const { version } = JSON.parse(readFileSync(resolve(root, 'package.json'), 'utf8'));
const prefix = `/pdfjs/${version}/`;
function files(folder: string): string[] {
  return readdirSync(resolve(root, folder), { withFileTypes: true }).flatMap((entry) => {
    const name = `${folder}/${entry.name}`;
    return entry.isDirectory() ? files(name) : [name];
  });
}
export function pdfjsAssets(): Plugin {
  return {
    name: 'h5-pdfjs-assets',
    apply: () => process.env.UNI_PLATFORM === 'h5',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const url = (req.url || '').split('?')[0];
        if (!url.startsWith(prefix)) return next();
        const relative = url.slice(prefix.length);
        const asset = relative === 'pdf.worker.js' ? 'legacy/build/pdf.worker.min.mjs' : relative === 'pdf.js' ? 'legacy/build/pdf.min.mjs' : relative;
        const file = resolve(root, asset);
        if (!file.startsWith(root + sep) || !existsSync(file) || !/^(legacy\/build\/pdf(?:\.worker)?\.min\.mjs|(?:cmaps|standard_fonts|wasm)\/[^/]+)$/.test(asset)) {
          res.statusCode = 404; res.end(); return;
        }
        res.setHeader('Content-Type', extname(file) === '.mjs' ? 'application/javascript' : extname(file) === '.wasm' ? 'application/wasm' : 'application/octet-stream');
        createReadStream(file).pipe(res);
      });
    },
    generateBundle() {
      this.emitFile({ type: 'asset', fileName: prefix.slice(1) + 'pdf.worker.js', source: readFileSync(resolve(root, 'legacy/build/pdf.worker.min.mjs')) });
      this.emitFile({ type: 'asset', fileName: prefix.slice(1) + 'pdf.js', source: readFileSync(resolve(root, 'legacy/build/pdf.min.mjs')) });
      for (const file of ['LICENSE', ...files('cmaps'), ...files('standard_fonts'), ...files('wasm')]) {
        this.emitFile({ type: 'asset', fileName: prefix.slice(1) + file, source: readFileSync(resolve(root, file)) });
      }
    }
  };
}
