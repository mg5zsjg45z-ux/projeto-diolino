import {env} from 'cloudflare:workers';
import {getChatGPTUser} from '../../chatgpt-auth';
import {devices} from '../../../lib/device-sync.mjs';
export const dynamic='force-dynamic';
const handle=async(request:Request)=>devices(request,env,await getChatGPTUser());
export const GET=handle;
export const POST=handle;
