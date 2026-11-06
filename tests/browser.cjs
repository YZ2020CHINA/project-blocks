// Run with the bundled Node runtime. A separate temporary project protects user data.
const {chromium}=require('./runtime.cjs').load('playwright');
const fs=require('node:fs');
const path=require('node:path');
const os=require('node:os');
const {spawn}=require('node:child_process');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'project-blocks-test-'));
const data=path.join(temp,'project.json');
fs.copyFileSync(path.join(root,'data/example.project.json'),data);
const python=require('./runtime.cjs').python;
const server=spawn(python,[path.join(root,'server.py'),'--port','8876','--no-browser','--data',data],{env:{...process.env,PYTHONUTF8:'1'},stdio:'pipe'});
let browser;
(async()=>{
 await new Promise((resolve,reject)=>{server.stdout.once('data',resolve);server.once('error',reject);server.once('exit',code=>reject(Error('Server exited '+code)));});
 browser=await chromium.launch({headless:true,...(process.env.BROWSER_CHANNEL?{channel:process.env.BROWSER_CHANNEL}:{})});
 const p=await browser.newPage({viewport:{width:1600,height:1000}});
 const errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto('http://127.0.0.1:8876');
 await p.waitForFunction(()=>document.getElementById('pb-sync')?.textContent==='已与本地工程同步');
 assert.equal(await p.locator('.story-node').count(),8);
 await p.screenshot({path:path.join(__dirname,'overview.png')});
 await require('./theme-layout.cjs')(p);
 // Add via the actual library, edit all important fields, persist and reload.
 await p.locator('.pb-brick[data-type="common"]').click();
 assert.equal(await p.locator('.story-node').count(),9);
 const id=await p.evaluate(()=>project.nodes.at(-1).id);
 await p.locator(`#node-el-${id} .btn-edit`).click();
 await p.locator('#pb-title').fill('浏览器测试工序');
 await p.locator('#pb-goal').fill('确认真实交互与持久化');
 await p.locator('#pb-status').selectOption('doing');
 await p.locator('#pb-files').fill('app/blocks.js\nserver.py');
 await p.locator('#pb-acceptance').fill('刷新后字段完整\n关系保持一致');
 await p.locator('#pb-instructions').fill('修改前先阅读相关源码。');
 await p.locator('#pb-add-rel').click();
 await p.locator('.rel-type').selectOption({label:'参考关联'});
 await p.locator('.rel-target').selectOption('goal');
 await p.locator('#pb-apply').click();
 await p.locator('#pb-save').click();
 await p.waitForFunction(()=>document.getElementById('pb-sync').textContent==='已与本地工程同步');
 let disk=JSON.parse(fs.readFileSync(data));
 assert.equal(disk.nodes.at(-1).workflow.status,'doing');assert.equal(disk.nodes.at(-1).choices[0].target,'goal');
 await p.reload();await p.waitForFunction(()=>project.nodes.length===9);
 assert.equal(await p.evaluate(()=>project.nodes.at(-1).workflow.acceptance.length),2);
 // Geometry: drag a card, undo, redo.
 await p.evaluate(id=>focusNodeInCanvas(id),id);
 const header=p.locator(`#node-el-${id} .node-title`),box=await header.boundingBox();
 const before=await p.evaluate(id=>project.nodes.find(n=>n.id===id).x,id);
 await p.mouse.move(box.x+box.width/2,box.y+box.height/2);await p.mouse.down();await p.mouse.move(box.x+box.width/2+100,box.y+box.height/2+50,{steps:8});await p.mouse.up();
 assert.notEqual(await p.evaluate(id=>project.nodes.find(n=>n.id===id).x,id),before);
 await p.keyboard.press('Control+z');assert.equal(await p.evaluate(id=>project.nodes.find(n=>n.id===id).x,id),before);
 await p.keyboard.press('Control+y');assert.notEqual(await p.evaluate(id=>project.nodes.find(n=>n.id===id).x,id),before);
 // Task generator reflects selected nodes and IDs.
 await p.locator('#pb-task').click();assert.match(await p.locator('.pb-code').innerText(),new RegExp(id));await p.locator('#pb-close').click();
 // Outline hierarchy is actual graph data and undo is a single operation.
 await p.locator('#pb-outline-btn').click();await p.locator('#pb-outline').fill('需求：网站\n  模块：前台\n    任务：页面\n  验收：检查');await p.locator('#pb-generate').click();
 assert.equal(await p.locator('.story-node').count(),13);
 assert.equal(await p.evaluate(()=>project.nodes.at(-4).choices.length),2);
 await p.keyboard.press('Control+z');assert.equal(await p.locator('.story-node').count(),9);
 await p.locator('#pb-save').click();await p.waitForFunction(()=>document.getElementById('pb-sync').textContent==='已与本地工程同步');
 // External changes auto-refresh when clean.
 disk=JSON.parse(fs.readFileSync(data));disk.nodes[0].title='外部 Codex 已更新';fs.writeFileSync(data,JSON.stringify(disk));
 await p.waitForFunction(()=>project.nodes[0].title==='外部 Codex 已更新',{},{timeout:7000});
 // Dirty conflict preserves local work until explicit resolution.
 await p.locator('.pb-brick[data-type="branch"]').click();
 disk=JSON.parse(fs.readFileSync(data));disk.nodes[0].title='磁盘新版本';fs.writeFileSync(data,JSON.stringify(disk));
 await p.waitForFunction(()=>document.getElementById('pb-sync').textContent.includes('磁盘有新版本'),{},{timeout:7000});
 assert.equal(await p.locator('.story-node').count(),10);
 await p.locator('#pb-save').click();await p.locator('#pb-conf-local').click();
 await p.waitForFunction(()=>document.getElementById('pb-sync').textContent==='已与本地工程同步');
 assert.equal(JSON.parse(fs.readFileSync(data)).nodes.length,10);
 // State protection: unfinished prerequisites cannot be marked complete.
 await p.evaluate(()=>focusNodeInCanvas('accept'));
 await p.locator('#node-el-accept .btn-edit').click();await p.locator('#pb-status').selectOption('done');await p.locator('#pb-apply').click();
 assert.match(await p.locator('#pb-error').innerText(),/前置工序未完成/);await p.locator('#pb-close').click();
 // Detect a dependency cycle from valid imported/external data.
 await p.evaluate(()=>{project.nodes.find(n=>n.id==='accept').choices.push({id:'test_cycle',text:'前置依赖',tag:'前置依赖',target:'goal'});renderAll();});
 await p.locator('#pb-check').click();assert.match(await p.locator('.pb-help').innerText(),/发现.*循环依赖/);await p.locator('#pb-close').click();
 // Server rejects stale revisions and untrusted browser origins.
 const current=await (await fetch('http://127.0.0.1:8876/api/project')).json();
 assert.equal((await fetch('http://127.0.0.1:8876/api/project',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({project:current.project,revision:'stale'})})).status,409);
 assert.equal((await fetch('http://127.0.0.1:8876/api/project',{method:'PUT',headers:{'Content-Type':'application/json',Origin:'https://example.com'},body:JSON.stringify(current)})).status,403);
 current.project.nodes[0].choices.push({id:'bad',target:'missing'});
 assert.equal((await fetch('http://127.0.0.1:8876/api/project',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(current)})).status,422);
 // Responsive smoke test.
 await p.setViewportSize({width:1100,height:800});await p.locator('#pb-help').click();await p.screenshot({path:path.join(__dirname,'help.png')});await p.locator('#pb-close').click();
 assert.deepEqual(errors,[]);
 // Create two cards and connect them through real pointer events on the port.
 await p.evaluate(()=>{project.viewport={x:10,y:40,scale:1};updateCanvasTransform();addNewNode({title:'连线起点',x:30,y:50});addNewNode({title:'连线终点',x:480,y:50});project.viewport={x:10,y:40,scale:1};updateCanvasTransform();renderAll();});
 const pair=await p.evaluate(()=>project.nodes.slice(-2).map(n=>n.id));
 const out=await p.locator(`#node-el-${pair[0]} .port-out-default`).boundingBox(),target=await p.locator(`#node-el-${pair[1]}`).boundingBox();
 await p.mouse.move(out.x+out.width/2,out.y+out.height/2);await p.mouse.down();await p.mouse.move(target.x+20,target.y+50,{steps:10});await p.mouse.up();
 assert.equal(await p.evaluate(id=>project.nodes.find(n=>n.id===id).choices[0]?.target,pair[0]),pair[1]);
 await p.keyboard.press('Control+z');assert.equal(await p.evaluate(id=>project.nodes.find(n=>n.id===id).choices.length,pair[0]),0);
 console.log('PASS: 8 initial cards; edit, multi-link save/reload, drag, undo/redo, outline, task export, external sync, conflict, prerequisite protection, cycle detection, API validation, responsive UI; no page errors.');
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();server.kill();const absolute=path.resolve(temp),parent=path.resolve(os.tmpdir());if(path.dirname(absolute)!==parent || !path.basename(absolute).startsWith('project-blocks-test-'))throw Error('Unsafe temporary directory');fs.rmSync(absolute,{recursive:true,force:true});});
