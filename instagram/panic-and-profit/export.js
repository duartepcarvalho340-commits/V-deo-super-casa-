const {chromium}=require('playwright');const fs=require('fs');
const [,,input,out,scale]=process.argv;fs.mkdirSync(out,{recursive:true});
(async()=>{const b=await chromium.launch();const pg=await b.newPage({viewport:{width:420,height:525},deviceScaleFactor:parseFloat(scale)});
await pg.setContent(fs.readFileSync(input,'utf8'),{waitUntil:'networkidle'});await pg.waitForTimeout(3000);
console.log('fonts',await pg.evaluate(()=>document.fonts.check("700 20px Fraunces")));
await pg.evaluate(()=>{document.querySelectorAll('.ig-header,.ig-dots,.ig-actions,.ig-caption').forEach(e=>e.style.display='none');
document.querySelector('.ig-frame').style.cssText='width:420px;height:525px;max-width:none;border-radius:0;box-shadow:none;overflow:hidden;margin:0;';
document.querySelector('.carousel-viewport').style.cssText='width:420px;height:525px;overflow:hidden;';
document.body.style.cssText='padding:0;margin:0;display:block;overflow:hidden;';});
const n=await pg.evaluate(()=>document.querySelectorAll('.slide').length);
for(let i=0;i<n;i++){await pg.evaluate(i=>{const t=document.querySelector('.carousel-track');t.style.transition='none';t.style.transform='translateX('+(-i*420)+'px)';},i);
await pg.waitForTimeout(300);await pg.screenshot({path:`${out}/slide_${i+1}.png`,clip:{x:0,y:0,width:420,height:525}});}
await b.close();})();
