import { spawnSync } from 'node:child_process';
import { resolve } from 'node:path';
// Keep the personal project login separate from the existing Ditto login.
const result=spawnSync(process.execPath,[resolve('node_modules/wrangler/bin/wrangler.js'),...process.argv.slice(2)],{
  stdio:'inherit',env:{...process.env,XDG_CONFIG_HOME:resolve('work/cloudflare-config')},
});
process.exit(result.status??1);
