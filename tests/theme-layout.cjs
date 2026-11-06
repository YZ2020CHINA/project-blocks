const assert=require('node:assert/strict');
const path=require('node:path');
const sharp=require('./runtime.cjs').load('sharp');

module.exports=async function verifyThemesAndSidebar(p){
  // Sample rendered backgrounds as well as CSS colors: transparent glass and
  // reflected gradients cannot be verified by backgroundColor alone.
  async function renderedCardContrast(){
    const card=p.locator('#node-el-goal');
    await card.scrollIntoViewIfNeeded();
    const selectors=['.node-summary','.pb-card-files','.pb-card-check','.choices-title','.pb-card-info > span:last-child'];
    const samples=[];
    for(const selector of selectors){const el=card.locator(selector);samples.push({selector,r:await el.boundingBox(),fg:await el.evaluate(n=>getComputedStyle(n).color.match(/[\d.]+/g).slice(0,3).map(Number))});}
    const mask=await p.addStyleTag({content:selectors.map(s=>'#node-el-goal '+s).join(',')+'{color:transparent!important;text-shadow:none!important}'});
    const box=await card.boundingBox(),image=await sharp(await card.screenshot()).removeAlpha().raw().toBuffer({resolveWithObject:true});
    await mask.evaluate(el=>el.remove());
    const luminance=rgb=>rgb.map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((sum,x,i)=>sum+x*[.2126,.7152,.0722][i],0);
    for(const {selector,r,fg} of samples){
      for(const fraction of [.25,.5,.75]){
        const x=Math.max(0,Math.min(image.info.width-1,Math.floor(r.x-box.x+r.width/2))),y=Math.max(0,Math.min(image.info.height-1,Math.floor(r.y-box.y+r.height*fraction)));
        const offset=(y*image.info.width+x)*image.info.channels,bg=[...image.data.subarray(offset,offset+3)],a=luminance(fg),b=luminance(bg),ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);
        assert.ok(ratio>=4.5,`Rendered night ${selector} contrast ${ratio.toFixed(2)} on ${bg}`);
      }
    }
  }
  async function contrast(selector,ratio=4.5){
    const result=await p.locator(selector).first().evaluate(el=>{
      const parse=color=>color.match(/[\d.]+/g)?.map(Number) || [0,0,0,0];
      const mix=(top,under)=>{const a=top[3] ?? 1;return top.slice(0,3).map((v,i)=>v*a+under[i]*(1-a));};
      const chain=[];for(let n=el;n;n=n.parentElement)chain.unshift(n);
      let bg=[255,255,255];for(const n of chain)bg=mix(parse(getComputedStyle(n).backgroundColor),bg);
      const fg=mix(parse(getComputedStyle(el).color),bg);
      const lum=rgb=>rgb.map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((s,x,i)=>s+x*[.2126,.7152,.0722][i],0);
      const a=lum(fg),b=lum(bg);return {ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05),fg,bg};
    });
    assert.ok(result.ratio>=ratio,`${selector} contrast ${result.ratio.toFixed(2)} < ${ratio}: ${JSON.stringify(result)}`);
  }
  for(const style of ['classic','p5r','liquid']){
    await p.locator('#btn-csp-theme-toggle').click();await p.locator(`#btn-theme-style-${style}`).click();
    await p.locator('#btn-csp-theme-toggle').click();await p.locator('#btn-theme-mode-light').click();
    for(const selector of ['.pb-brick','.pb-brick span','.pb-status-filter','#pb-outline-btn','#pb-save','.node-summary','.pb-card-check','.pb-sync'])await contrast(selector);
    for(const status of ['todo','doing','done'])await contrast(`.pb-pill[data-status="${status}"]`);
    if(style==='classic')await contrast('.node-title'); // P5R uses a black gradient banner.
    await p.locator('#btn-csp-theme-toggle').click();
    for(const selector of ['#btn-theme-style-classic','#btn-theme-style-liquid','#btn-theme-style-p5r','#btn-theme-mode-light','#btn-theme-mode-dark'])await contrast(selector);
    await p.screenshot({path:path.join(__dirname,`${style}-light.png`)});
    await p.locator('#btn-csp-theme-toggle').click();
    await p.reload();await p.waitForFunction(()=>document.getElementById('pb-sync')?.textContent==='已与本地工程同步');
    assert.equal(await p.locator('html').getAttribute('data-ui-style'),style);
    assert.equal(await p.locator('html').getAttribute('data-theme'),'light');
    if(style==='p5r'){
      const card=p.locator('.chapter-item[data-id="design"]');
      await card.hover();
      for(const selector of ['.chapter-title-text','.chapter-desc-text','.chapter-item-footer','.chapter-item-top > span:last-child'])await contrast('.chapter-item[data-id="design"] '+selector);
      await card.click();
      assert.equal(await card.evaluate(el=>el.classList.contains('active')),true);
      for(const selector of ['.chapter-title-text','.chapter-desc-text','.chapter-item-footer','.chapter-item-top > span:last-child'])await contrast('.chapter-item.active '+selector);
      await p.screenshot({path:path.join(__dirname,'p5r-light-selected.png')});
      await p.mouse.move(1000,800);
      await contrast('.chapter-item.active .chapter-title-text');
      await contrast('.chapter-item.active .chapter-desc-text');
      await p.locator('#pb-save').click();await p.waitForFunction(()=>document.getElementById('pb-sync').textContent==='已与本地工程同步');
    }
  }
  // Night mode checks include the small labels missed by the earlier smoke test.
  for(const style of ['classic','liquid']){
    await p.locator('#btn-csp-theme-toggle').click();await p.locator(`#btn-theme-style-${style}`).click();
    await p.locator('#btn-csp-theme-toggle').click();await p.locator('#btn-theme-mode-dark').click();
    for(const id of ['goal','design','schema','reference','task-ui','task-sync','decision','accept']){
      for(const selector of ['.node-summary','.pb-card-info > span:last-child','.pb-card-check','.pb-card-files','.pb-pill'])await contrast(`#node-el-${id} ${selector}`);
    }
    for(const selector of ['.choices-title','.pb-library p','.pb-eyebrow','.chapter-item-footer','.sidebar-footer'])await contrast(selector);
    await p.evaluate(()=>{project.viewport.scale=1;updateCanvasTransform();focusNodeInCanvas('goal');});
    await renderedCardContrast();
    await p.screenshot({path:path.join(__dirname,`${style}-dark-readable.png`)});
  }
  await p.locator('#btn-csp-theme-toggle').click();await p.locator('#btn-theme-mode-light').click();
  await p.locator('#pb-save').click();await p.waitForFunction(()=>document.getElementById('pb-sync').textContent==='已与本地工程同步');
  // Both dimensions respond to real pointer dragging and survive reload.
  await p.setViewportSize({width:1280,height:900});
  const lib=p.locator('.pb-library'),sidebar=p.locator('#sidebar'),heightHandle=p.locator('.pb-pane-resizer'),widthHandle=p.locator('.pb-width-resizer');
  const beforeHeight=(await lib.boundingBox()).height,h=await heightHandle.boundingBox();
  await p.mouse.move(h.x+h.width/2,h.y+h.height/2);await p.mouse.down();await p.mouse.move(h.x+h.width/2,h.y+h.height/2-110,{steps:8});await p.mouse.up();
  assert.ok(Math.abs((await lib.boundingBox()).height-(beforeHeight-110))<2,'library height did not resize');
  const beforeWidth=(await sidebar.boundingBox()).width,w=await widthHandle.boundingBox();
  await p.mouse.move(w.x+w.width/2,w.y+w.height/2);await p.mouse.down();await p.mouse.move(w.x+w.width/2+85,w.y+w.height/2,{steps:8});await p.mouse.up();
  // The original sidebar has a short width transition after releasing the mouse.
  await p.waitForTimeout(300);
  assert.ok(Math.abs((await sidebar.boundingBox()).width-(beforeWidth+85))<2,'sidebar width did not resize');
  const sizes=await p.evaluate(()=>({height:document.querySelector('.pb-library').clientHeight,width:document.getElementById('sidebar').offsetWidth}));
  await p.reload();await p.waitForFunction(()=>document.getElementById('pb-sync')?.textContent==='已与本地工程同步');
  await p.waitForTimeout(300);
  assert.deepEqual(await p.evaluate(()=>({height:document.querySelector('.pb-library').clientHeight,width:document.getElementById('sidebar').offsetWidth})),sizes);
  await p.locator('.pb-pane-resizer').focus();await p.keyboard.press('ArrowDown');
  assert.equal(await p.evaluate(()=>document.querySelector('.pb-library').clientHeight),sizes.height+16);
  await p.locator('#sidebar-toggle-btn').click();await p.waitForTimeout(300);assert.equal(await widthHandle.isVisible(),false);
  await p.locator('#sidebar-toggle-btn').click();await p.waitForTimeout(300);assert.equal(await widthHandle.isVisible(),true);
  await p.setViewportSize({width:1000,height:600});
  await p.screenshot({path:path.join(__dirname,'sidebar-resized.png')});
  assert.ok(await p.locator('.chapter-list').evaluate(el=>el.clientHeight>=48),'directory lost its visible list');
  assert.ok(await lib.evaluate(el=>el.clientHeight>=60),'library lost its visible area');
  const toolbar=p.locator('#pb-help');await toolbar.click();await p.locator('#pb-close').click();
  await p.setViewportSize({width:1600,height:1000});
  await p.locator('#btn-csp-theme-toggle').click();await p.locator('#btn-theme-style-classic').click();
  await p.locator('#btn-csp-theme-toggle').click();await p.locator('#btn-theme-mode-dark').click();
  for(const selector of ['.pb-brick','.pb-brick span','.pb-status-filter','#pb-outline-btn','.node-title','.node-summary'])await contrast(selector);
  await p.locator('.pb-pane-resizer').dblclick();await p.locator('.pb-width-resizer').dblclick();
  console.log('PASS: light themes, P5R day directory hover/selection, classic/liquid night small text, theme persistence, sidebar resizing and scrolling.');
};
