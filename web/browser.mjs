import assert from 'node:assert/strict'
import {once} from 'node:events'
import {mkdir,mkdtemp} from 'node:fs/promises'
import path from 'node:path'
import {spawn} from 'node:child_process'
import {fileURLToPath} from 'node:url'
import puppeteer from 'puppeteer-core'
import {randomBytes} from 'node:crypto'

const root=fileURLToPath(new URL('../',import.meta.url))
const scratch=await mkdtemp(path.join(root,'.local/tmp/browser-'))
const shots=path.join(root,'evidence')
await mkdir(shots,{recursive:true})
const token=randomBytes(20).toString('hex'),port=18479,url='http://127.0.0.1:'+port
let server,browser
async function start(){
 server=spawn('./start.sh',[],{cwd:root,stdio:['ignore','pipe','pipe'],env:{...process.env,HOST:'127.0.0.1',PORT:String(port),BLINDSPOT_DATA:path.join(scratch,'state'),BLINDSPOT_MEMORY:'local',BLINDSPOT_MODE:'owner',BLINDSPOT_OWNER_TOKEN:token}})
 let log=''
 server.stderr.on('data',b=>{log+=b.toString()})
 for(let i=0;i<150;i++){
   if(server.exitCode!==null)throw Error('Server startup failed '+log)
   if(log.includes('Uvicorn running on'))return
   await new Promise(r=>setTimeout(r,100))
 }
 throw Error('Server startup timed out')
}
async function stop(){
 if(server&&server.exitCode===null&&server.signalCode===null){const ended=once(server,'exit');server.kill('SIGTERM');await ended}
}
try{
 await start()
 browser=await puppeteer.launch({executablePath:process.env.CHROME_BIN||'/usr/bin/google-chrome',userDataDir:path.join(scratch,'profile'),headless:true,env:{...process.env,TMPDIR:scratch,XDG_CONFIG_HOME:scratch,XDG_CACHE_HOME:scratch,CHROME_CONFIG_HOME:scratch},args:['--no-sandbox','--disable-crashpad','--disable-breakpad','--disable-dev-shm-usage','--disable-background-networking','--disable-component-update','--disable-sync','--no-first-run','--no-proxy-server','--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1']})
 const page=await browser.newPage(),errors=[]
 page.on('pageerror',e=>errors.push(String(e)))
 await page.setViewport({width:1440,height:1000,deviceScaleFactor:1})
 const contains=t=>page.waitForFunction(t=>document.body.innerText.toLowerCase().includes(t.toLowerCase()),{},t)
 const click=async t=>{const b=await page.waitForFunction(t=>Array.from(document.querySelectorAll('button')).find(b=>b.textContent.trim()===t),{},t);await b.asElement().click()}
 await page.goto(url,{waitUntil:'networkidle0'})
 await contains('Recalled a low light failure')
 assert.equal(await page.locator('h1').map(n=>n.textContent).wait(),'Follow-up session')
 assert.equal(await page.$$eval('.pair img',imgs=>imgs.filter(i=>i.complete&&i.naturalWidth>0).length),2)
 await page.screenshot({path:path.join(shots,'desktop.png')})
 console.log('PASS desktop saved report, paired images and remembered test order')
 await page.setViewport({width:390,height:844,deviceScaleFactor:1})
 await page.screenshot({path:path.join(shots,'mobile.png'),fullPage:true})
 assert(await page.evaluate(()=>document.documentElement.scrollWidth===innerWidth))
 await click('Original')
 await page.waitForFunction(()=>document.querySelectorAll('.frame').length===1)
 console.log('PASS mobile layout and trial selection')
 await page.setViewport({width:1280,height:900})
 await click('Owner access');await page.type('input[type=password]',token);await click('Unlock');await click('Owner workspace')
 await click('Load follow-up');await page.waitForSelector('select[multiple] option:checked')
 await click('Create run');await contains('Run next step');await page.waitForFunction(()=>[...document.querySelectorAll('button')].some(b=>b.textContent==='Run next step'&&!b.disabled))
 // A newly created run collapses the owner panel.
 async function controls(){await page.evaluate(()=>document.querySelector('details.owner').open=true)}
 await controls();await click('Run next step');await contains('baseline')
 const fetchOwner=async(p,body)=>{const r=await fetch(url+p,{method:body?'POST':'GET',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})});assert(r.ok);return r.json()}
 const rid=(await fetchOwner('/api/library')).runs[0].id
 const before=await fetchOwner('/api/runs/'+rid)
 assert.equal(before.cursor,1)
 await stop();await start()
 const duplicate=await fetchOwner('/api/runs/'+rid+'/step',{cursor:0})
 assert.equal(duplicate.cursor,1)
 assert.equal(duplicate.photos[0].trials[0].id,before.photos[0].trials[0].id)
 await controls();await click('Run next step');await contains('blur · 1')
 const after=await fetchOwner('/api/runs/'+rid)
 assert.equal(after.photos[0].trials.length,2)
 console.log('PASS authenticated browser run, actual server restart, stale-step replay and continuation')
 assert.deepEqual(errors,[])
 console.log('PASS zero browser uncaught errors')
}finally{if(browser)await browser.close();await stop()}
