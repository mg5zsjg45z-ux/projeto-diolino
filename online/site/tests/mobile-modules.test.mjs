import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const modules=await readFile(new URL('../public/mobile/modules.js',import.meta.url),'utf8');
const workspace=await readFile(new URL('../public/mobile/workspace.js',import.meta.url),'utf8');

test('module navigation hides every page owned by older navigation handlers',()=>{
  assert.match(modules,/\['overview','routine','records','calculator','planning','files','more'\]/);
});

test('planned strength permits decimal loads and habit status updates retain notes',()=>{
  assert.match(modules,/fields\.load_kg\.step='any'/);
  assert.match(modules,/status:select\.value,notes:mark\?\.notes\|\|''/);
});

test('Bible restores legacy and saved editions and keeps new marks edition scoped',()=>{
  assert.match(workspace,/edition\.value=editions\[saved\.edition\]\?saved\.edition:'BPM'/);
  assert.match(workspace,/\(saved\.edition\|\|'BPM'\)===key\?saved/);
  assert.match(workspace,/edition\.value==='BPM'&&!note&&favorites\.includes\(key\)/);
});

test('late Bible downloads cannot replace the selected edition',()=>{
  assert.match(workspace,/generation!==editionLoadGeneration\|\|key!==edition\.value\)return/);
});
