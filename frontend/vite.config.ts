import { defineConfig } from 'vite';
import { writeFileSync } from 'node:fs';
import uni from '@dcloudio/vite-plugin-uni';
import { pdfjsAssets } from './scripts/pdfjs-assets';
export default defineConfig({
  plugins: [uni(), pdfjsAssets(), { name: 'release-module-evidence', generateBundle(_options, bundle) { if(process.env.FINTAX_BUNDLE_REPORT) writeFileSync(process.env.FINTAX_BUNDLE_REPORT, JSON.stringify(Object.values(bundle).filter((v: any)=>v.type==='chunk').flatMap((v: any)=>Object.keys(v.modules)).sort(),null,2)); } }],
  server: { host: '127.0.0.1', port: 5173, strictPort: true }
});
