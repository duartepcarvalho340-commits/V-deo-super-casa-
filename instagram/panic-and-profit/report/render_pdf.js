const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();
await p.goto('file://'+path.join(__dirname,'report.html'),{waitUntil:'networkidle'});await p.waitForTimeout(1500);
await p.pdf({path:path.join(__dirname,'panic_and_profit_report.pdf'),format:'A4',printBackground:true,margin:{top:'16mm',bottom:'16mm',left:'14mm',right:'14mm'}});
await b.close();console.log('pdf ok')})();
