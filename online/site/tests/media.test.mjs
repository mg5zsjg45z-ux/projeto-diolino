import {test} from 'node:test';
import assert from 'node:assert/strict';
import {validateFile,PART_SIZE,MAX_FILE_SIZE,STORAGE_LIMIT,expectedPart,validSignature,byteRange} from '../lib/media.mjs';
test('file metadata rejects executables, path injection and oversized files',()=>{
 const file={name:'aula.mp4',size:200*1024*1024,category:'Medicina',fingerprint:'a'.repeat(64)};
 assert.equal(validateFile(file).mime,'video/mp4');
 for(const value of [{...file,name:'virus.exe'},{...file,name:'../aula.pdf'},{...file,name:'a\r\nb.pdf'},{...file,size:MAX_FILE_SIZE+1},{...file,fingerprint:'invalid'}])assert.throws(()=>validateFile(value));
 assert.equal(STORAGE_LIMIT,10*1024**3);
});
test('part boundaries and file signatures are checked',()=>{
 assert.equal(expectedPart(PART_SIZE+17,1),PART_SIZE);assert.equal(expectedPart(PART_SIZE+17,2),17);assert.throws(()=>expectedPart(17,2));
 assert.equal(validSignature('application/pdf',new TextEncoder().encode('%PDF-1.4')),true);
 assert.equal(validSignature('application/pdf',new TextEncoder().encode('<html>')),false);
 assert.equal(validSignature('video/mp4',new Uint8Array([0,0,0,24,102,116,121,112])),true);
});
test('single ranges support video seeking and suffixes, reject multiple or invalid ranges',()=>{
 assert.deepEqual(byteRange('bytes=10-19',100),{offset:10,length:10});assert.deepEqual(byteRange('bytes=-10',100),{offset:90,length:10});assert.deepEqual(byteRange('bytes=90-',100),{offset:90,length:10});assert.deepEqual(byteRange('bytes=0-999',100),{offset:0,length:100});assert.throws(()=>byteRange('bytes=100-',100));assert.throws(()=>byteRange('bytes=0-1,3-4',100));assert.throws(()=>byteRange('bytes=-0',100));
});

