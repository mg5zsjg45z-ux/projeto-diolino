import {env} from 'cloudflare:workers';
import {desktopSync} from '../../../lib/device-sync.mjs';
export const dynamic='force-dynamic';
export const GET=(request:Request)=>desktopSync(request,env);
export const POST=(request:Request)=>desktopSync(request,env);
