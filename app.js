'use strict';
const C=JSON.parse(document.querySelector('#catalog-data').textContent),$=s=>document.querySelector(s);
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let profiles=[],active=0,tab='Overview',raw=null,shown=[];
const defaults=()=>({sRank:true,dire:false,useInventory:false,defaultMinutes:10,cleanupHours:null,buyShop:false,mode:'both',goal:'all',samples:[],overrides:{}});
try{profiles=JSON.parse(localStorage.getItem('aot-notebook-v1')||'[]');if(!Array.isArray(profiles))profiles=[];}catch{}
if(window.initialAOTProfile&&!profiles.some(p=>p.snapshot?.sha256===window.initialAOTProfile.snapshot.sha256)){profiles.push({...window.initialAOTProfile,settings:defaults()});}
active=Math.max(0,profiles.length-1);
function persist(){try{localStorage.setItem('aot-notebook-v1',JSON.stringify(profiles));}catch{$('#error').textContent='Browser storage unavailable or full. Export tracker JSON to preserve this session.';}}
function profile(){return profiles[active];}
function snapshot(){const p=profile();if(!p)return null;const s=structuredClone(p.snapshot);for(const [path,value]of Object.entries(p.settings.overrides)){const [group,key,field]=path.split('|');const row=s[group]?.find(x=>String(x.key??x.id)===key);if(row)row[field]=value;}return s;}
function message(s){$('#status').textContent=s;}
function download(name,body,type='application/json'){const url=URL.createObjectURL(new Blob([body],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
async function readSave(buffer){
 if(buffer.byteLength!==0xbbe20)throw Error('This is not a supported original-game PC save: expected 769568 bytes.');
 const bytes=new Uint8Array(buffer.slice(0)),v=new DataView(bytes.buffer);let state=v.getUint16(2,true),sum=0;
 for(let o=4;o<bytes.length;o+=4){for(let n=0;n<3;n++)state=(Math.imul(state,0x5b1a7851)+0xce4e)>>>0;v.setUint32(o,v.getUint32(o,true)^state,true);}
 for(let o=4;o<bytes.length;o+=2)sum=(sum+v.getUint16(o,true))&65535;
 if(sum!==v.getUint16(0,true))throw Error('Checksum failed. The save may be incomplete, corrupt, or from an unsupported game/build.');
 const u=o=>v.getUint32(o,true),hex=o=>'0x'+o.toString(16),txt=(o,n)=>Array.from(bytes.slice(o,o+n),x=>x.toString(16).padStart(2,'0')).join('');
 const s={schema_version:1,game:C.game,checksum_valid:true,captured_at:new Date().toISOString(),summary:{funds:u(0x654),total_kills:u(0x64c),save_summary_raw:new TextDecoder().decode(bytes.slice(4,64)).split('\0')[0]},characters:[],materials:[],inventory:[],gallery:[],missions:[],requests:[]};
 if(globalThis.crypto?.subtle)s.sha256=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',buffer)),x=>x.toString(16).padStart(2,'0')).join('');
 for(let i=0;i<14;i++){const o=0x249f0+i*240;s.characters.push({id:i,name:C.characters[i],level:1+u(o+132)+u(o+216),kills:u(o+64),missions:u(o+72),xp:u(o+128),extra_xp:u(o+212),attributes:Array.from({length:6},(_,j)=>v.getUint16(o+112+j*2,true)),offset:hex(o),raw:txt(o,240)});}
 for(let i=0;i<C.materials.length;i++){const name=C.materials[i];if(!name||name.toLowerCase()==='dummy')continue;const o=0x362c0+i*48;s.materials.push({id:i,name,count:u(o),shop_state:u(o+4),offset:hex(o)});}
 for(let g=0;g<3;g++)for(let slot=0;slot<100;slot++){const o=0x257c0+g*0x1900+slot*64,i=bytes[o];if(i===255)continue;s.inventory.push({key:`${g}:${i}`,group:g,slot,id:i,name:C.equipment.find(e=>e.key===`${g}:${i}`)?.name||`Item ${i}`,fortification:bytes[o+1],offset:hex(o),raw:txt(o,64)});}
 s.gallery=C.gallery.map(e=>({...e,acquired:!!(bytes[e.offset]&(e.accept_bit32?35:3)),raw_flag:bytes[e.offset]}));
 for(let mode=0;mode<2;mode++){
  for(const m of C.missions){const o=0xa70+mode*0xe880+m.id*96;s.missions.push({id:m.id,mode:['normal','true'][mode],name:m.name,completed:!!(bytes[o]&32),time_seconds:u(o+8)===0xffffffff?null:u(o+8),raw_flag:bytes[o],raw_rank:bytes[o+2],offset:hex(o),raw:txt(o,96)});}
  for(let i=0;i<C.requests.length;i++){const o=0x40ac8+i*2+mode;s.requests.push({id:i,mode:['normal','true'][mode],name:C.requests[i],completed:bytes[o]===3,state:bytes[o],offset:hex(o)});}
 }
 s.character_kills_match_global=s.characters.reduce((n,x)=>n+x.kills,0)===s.summary.total_kills;
 s.summary.gallery_done=s.gallery.filter(x=>x.acquired).length;s.summary.gallery_total=s.gallery.length;s.summary.gallery_percent=Math.floor(s.summary.gallery_done*100/s.gallery.length);
 return {snapshot:s,raw:bytes};
}
function validate(s){
 if(s?.schema_version!==1||s.game!==C.game||!s.checksum_valid)throw Error('Unsupported snapshot. Use this tracker’s original-game snapshot format.');
 const integer=x=>Number.isInteger(x)&&x>=0&&x<=0xffffffff;
 for(const k of ['characters','materials','inventory','gallery','missions','requests'])if(!Array.isArray(s[k])||s[k].length>2000)throw Error(`Invalid ${k} list`);
 for(const x of s.characters)if(!Array.isArray(x.attributes)||x.attributes.length!==6||!x.attributes.every(integer))throw Error('Invalid character attributes');
 for(const x of s.characters)for(const k of ['id','level','kills','missions','xp'])if(!integer(x[k]))throw Error('Invalid character counter');
 for(const x of s.materials)if(!integer(x.count)||!integer(x.id)||!integer(x.shop_state))throw Error('Invalid material count');
 for(const x of s.inventory)if(!integer(x.id)||!integer(x.fortification))throw Error('Invalid inventory');
 for(const x of s.gallery)if(!C.gallery.some(e=>e.key===x.key)||!integer(x.offset)||!integer(x.raw_flag)||typeof x.acquired!=='boolean')throw Error('Invalid gallery record');
 for(const x of s.missions)if(!integer(x.id)||!['normal','true'].includes(x.mode)||(x.time_seconds!==null&&!integer(x.time_seconds)))throw Error('Invalid mission record');
 for(const x of s.requests)if(!integer(x.id)||!integer(x.state)||!['normal','true'].includes(x.mode)||typeof x.completed!=='boolean')throw Error('Invalid request');
 if(!integer(s.summary?.funds)||!integer(s.summary?.total_kills))throw Error('Invalid summary');
}
function validSettings(value){
 const t={...defaults(),...value};
 if(!['both','normal','true'].includes(t.mode)||!['all','perfected','rozen'].includes(t.goal))throw Error('Invalid plan selection');
 if(!Number.isFinite(t.defaultMinutes)||t.defaultMinutes<=0||t.defaultMinutes>1440)throw Error('Invalid fallback duration');
 if(t.cleanupHours!==null&&(!Number.isFinite(t.cleanupHours)||t.cleanupHours<0||t.cleanupHours>10000))throw Error('Invalid cleanup hours');
 if(!Array.isArray(t.samples)||t.samples.length>10000)throw Error('Invalid run history');
 for(const r of t.samples){if(!Number.isFinite(r.minutes)||r.minutes<=0||r.minutes>1440||!r.materials||typeof r.materials!=='object')throw Error('Invalid run sample');for(const [id,n]of Object.entries(r.materials))if(!/^\d+$/.test(id)||!C.materials[id]||!Number.isFinite(n)||n<0||n>1e6)throw Error('Invalid run drops');}
 for(const [key,n]of Object.entries(t.overrides||{})){if(!/^(gallery\|[^|]+\|acquired|materials\|\d+\|count|characters\|\d+\|(level|kills|missions))$/.test(key)||!(typeof n==='boolean'||Number.isInteger(n)&&n>=0&&n<=1e9))throw Error('Invalid tracker correction');}
 return t;
}
$('#import').addEventListener('change',async e=>{try{
 $('#error').textContent='';const file=e.target.files[0];if(!file)return;if(file.size>12*1024*1024)throw Error('File is too large. Maximum 12 MB.');
 let p;if(file.name.toLowerCase().endsWith('.dat')){const r=await readSave(await file.arrayBuffer());raw=r.raw;p={name:file.name,snapshot:r.snapshot,settings:profile()?{...structuredClone(profile().settings),overrides:{}}:defaults()};}
 else{const j=JSON.parse(await file.text());p=j.snapshot?j:{name:file.name,snapshot:j,settings:defaults()};validate(p.snapshot);p.settings=validSettings(p.settings);raw=null;}
 validate(p.snapshot);profiles.push(p);active=profiles.length-1;persist();render();message(`Loaded ${file.name}. Checksum verified. Personal data remains local.`);
 }catch(err){$('#error').textContent=err.message;}finally{e.target.value='';}});
$('#export').onclick=()=>{if(profile())download('aot-tracker.json',JSON.stringify(profile(),null,2));};
$('#raw').onclick=()=>{if(raw)download('aot-decrypted.bin',raw,'application/octet-stream');else message('Open a .dat save to enable a decrypted byte export. JSON snapshots include mapped raw records only.');};
$('#csv').onclick=()=>{if(!shown.length)return;const keys=[...new Set(shown.flatMap(x=>Object.keys(x)))];const safe=x=>{let v=typeof x==='object'?JSON.stringify(x):String(x??'');if(/^[=+@-]/.test(v))v="'"+v;return '"'+v.replaceAll('"','""')+'"';};download(`aot-${tab.toLowerCase().replaceAll(' ','-')}.csv`,[keys,...shown.map(r=>keys.map(k=>r[k]))].map(r=>r.map(safe).join(',')).join('\r\n'),'text/csv');};
$('#slot').onchange=e=>{active=Number(e.target.value);raw=null;render();};
$('#search').oninput=renderContent;$('#missing').onchange=renderContent;
function filter(rows){const q=$('#search').value.toLowerCase();return rows.filter(r=>(!q||Object.values(r).some(x=>String(x).toLowerCase().includes(q)))&&(!$('#missing').checked||!(r.acquired??r.completed)));}
function table(rows,cols){shown=rows;return `<div class="scroll"><table><thead><tr>${cols.map(([name])=>`<th>${esc(name)}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${cols.map(([,fn])=>`<td>${fn(r)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;}
function numberEdit(group,row,field){return `<input aria-label="${esc(row.name)} ${field}" type="number" min="0" step="1" data-edit="${esc(group+'|'+(row.key??row.id)+'|'+field)}" value="${row[field]}">`;}
function checkEdit(group,row,field){return `<input aria-label="${esc(row.name)} ${field}" type="checkbox" data-edit="${esc(group+'|'+(row.key??row.id)+'|'+field)}" ${row[field]?'checked':''}>`;}
function render(){
 $('#tabs').innerHTML=['Overview','Equipment','Materials','Characters','Gallery','Missions','Requests','Farming plan','Run log'].map(t=>`<button class="${tab===t?'active':''}" data-tab="${t}">${t}</button>`).join('');
 $('#tabs').querySelectorAll('button').forEach(b=>b.onclick=()=>{tab=b.dataset.tab;$('#search').value='';render();});
 $('#slot').innerHTML=profiles.length?profiles.map((p,i)=>`<option value="${i}" ${i===active?'selected':''}>${esc(p.name)} · ${esc(p.snapshot.captured_at?.slice(0,16))}</option>`).join(''):'<option>No save loaded</option>';
 const s=snapshot();$('#summary').innerHTML=s?`<div class="stats"><div class="stat"><strong>${s.gallery.filter(x=>x.acquired).length} / ${s.gallery.length}</strong>Gallery entries</div><div class="stat"><strong>${s.materials.reduce((n,x)=>n+x.count,0).toLocaleString()}</strong>Materials held</div><div class="stat"><strong>${s.summary.total_kills.toLocaleString()}</strong>Titans slain</div><div class="stat"><strong>${s.summary.funds.toLocaleString()}</strong>Regiment funds</div></div>`:'';renderContent();
}
function renderContent(){
 const s=snapshot(),p=profile();shown=[];if(!s){$('#content').innerHTML='<div class="notice">Open your save to begin. This tool decrypts locally, validates its checksum, and displays historical gallery unlocks separately from equipment currently in your inventory. Keep a backup before making changes in the game.</div>';return;}
 let html='';
 if(tab==='Overview'){
 const groups=[...new Set(s.gallery.map(x=>x.section))].map(section=>{const rows=s.gallery.filter(x=>x.section===section);return {name:section,done:rows.filter(x=>x.acquired).length,total:rows.length};});
 html=table(groups,[['Category',r=>esc(r.name)],['Collected',r=>`${r.done} / ${r.total}`],['Remaining',r=>r.total-r.done],['Progress',r=>`<progress value="${r.done}" max="${r.total}" aria-label="${esc(r.name)}"></progress>`]]);
 const remaining=s.gallery.filter(x=>!x.acquired);html+=`<div class="notice">${remaining.length} gallery entries remain. Character kills ${s.character_kills_match_global?'match':'do not match'} the global total. Normal requests: ${s.requests.filter(x=>x.mode==='normal'&&x.completed).length}/81. True Attack requests: ${s.requests.filter(x=>x.mode==='true'&&x.completed).length}/81.</div><p>Finish outstanding gallery equipment in branches, then use the farming plan to cover shared material shortages. Character level grinding and True Attack request completion are shown separately; they are not automatically added to gallery farming time.</p><details><summary>Evidence and limits</summary><p>Checksum verified. Gallery membership uses the game’s eligibility tables. Character level, kills and battles are mapped; extra star fortification and rank names are not. Mission times are saved records, not measured averages. Full source offsets and raw records are in the JSON/CSV exports.</p><p>Captured ${esc(s.captured_at)}. Save summary: <code>${esc(s.summary.save_summary_raw)}</code>. Edits are local tracker corrections and never modify your save.</p></details>`;
 }
 if(tab==='Equipment'){
 const rows=C.equipment.filter(e=>e.required).map(e=>({...e,acquired:s.gallery.find(x=>x.key==='equipment:'+e.key)?.acquired||false,held:s.inventory.filter(x=>x.key===e.key)}));
 html='<p>Acquired records whether you have ever owned this item. Held lists current inventory. All 225 required blade, scabbard and ODM variants are included; horses are under Gallery.</p>'+table(filter(rows),[['Item',r=>`${esc(r.name)}<br><small>${r.group} · ${r.key}</small>`],['Acquired',r=>checkEdit('gallery',{...r,key:'equipment:'+r.key},'acquired')],['Held',r=>r.held.map(x=>`+${x.fortification}`).join(', ')||'—'],['Stats',r=>r.stats.join(' / ')],['Develop / upgrade materials',r=>[r.develop.length?'Develop: '+recipeText(r.develop):'',r.upgrade.length?'Upgrade: '+recipeText(r.upgrade):''].filter(Boolean).map(esc).join('<br>')]]);
 }
 if(tab==='Materials')html=table(filter(s.materials),[['Material',r=>`${esc(r.name)}<br><small>ID ${r.id}</small>`],['Held',r=>numberEdit('materials',r,'count')],['Shop flag',r=>r.shop_state],['Evidence',r=>esc(r.offset)]]);
 if(tab==='Characters')html='<p>Levels include the additional seventh skill level. Attributes are strength, dexterity, concentration, stamina, health and leadership. Non-playable records retained by the game are included.</p>'+table(filter(s.characters),[['Character',r=>esc(r.name)],['Level',r=>numberEdit('characters',r,'level')],['Kills',r=>numberEdit('characters',r,'kills')],['Battles',r=>numberEdit('characters',r,'missions')],['XP',r=>r.xp],['Attributes',r=>esc(r.attributes.join(' / '))]]);
 if(tab==='Gallery')html=table(filter(s.gallery),[['Section',r=>esc(r.section)],['Entry',r=>esc(r.name)],['Acquired',r=>checkEdit('gallery',r,'acquired')],['Evidence',r=>`${r.offset.toString(16)} · flag ${r.raw_flag}`]]);
 if(tab==='Missions'){
 const rows=s.missions.map(m=>({...m,info:C.missions.find(x=>x.id===m.id)}));html='<p>Rewards below are clear rewards. S-rank and Dire rewards are conditional. Body-part drops add materials separately. Saved time may be a personal best; record whole runs including loading for realistic estimates.</p>'+table(filter(rows),[['Mission',r=>`${esc(r.name)}<br><small>${r.mode==='true'?'True Attack':'Normal'} · ${r.info.type}</small>`],['Cleared',r=>r.completed?'Yes':'No'],['Saved time',r=>r.time_seconds?`${(r.time_seconds/60).toFixed(1)} min`:'—'],['Clear rewards',r=>esc(recipeText(r.info.rewards[r.mode]))],['S-rank',r=>esc(recipeText([r.info.s_rank[r.mode]]))],['Dire',r=>esc(recipeText([r.info.dire[r.mode]]))]]);
 }
 if(tab==='Requests')html=table(filter(s.requests),[['Request',r=>esc(r.name)],['Mode',r=>esc(r.mode)],['Complete',r=>r.completed?'Yes':'No'],['Raw state',r=>r.state]]);
 if(tab==='Farming plan')html=planHTML(s,p.settings);
 if(tab==='Run log')html=logHTML(p.settings);
 $('#content').innerHTML=html;
 $('#content').querySelectorAll('[data-edit]').forEach(input=>input.onchange=()=>{const value=input.type==='checkbox'?input.checked:Number(input.value);if(input.type!=='checkbox'&&(!Number.isInteger(value)||value<0||value>1e9)){render();return;}p.settings.overrides[input.dataset.edit]=value;persist();render();});
 $('#content').querySelectorAll('[data-setting]').forEach(input=>input.onchange=()=>{p.settings[input.dataset.setting]=input.type==='checkbox'?input.checked:input.type==='number'?(input.value===''?null:Number(input.value)):input.value;try{validSettings(p.settings);}catch(e){$('#error').textContent=e.message;return;}persist();render();});
 if(tab==='Run log')bindLog();
}
function recipeText(items){return items.filter(x=>x.material!==255&&x.quantity>0).map(x=>`${x.quantity} ${C.materials[x.material]||'Unknown '+x.material}`).join(', ')||'—';}
function effectiveMissions(s,t){
 const rows=[];
 for(const mode of ['normal','true'])for(const m of C.missions){
  if(t.mode!=='both'&&mode!==t.mode)continue;
  const key=`${mode}:${m.id}`,samples=t.samples.filter(x=>x.key===key),record=s.missions.find(x=>x.id===m.id&&x.mode===mode);
  let minutes=samples.length?samples.reduce((n,x)=>n+x.minutes,0)/samples.length:(record?.time_seconds?record.time_seconds/60*1.25:t.defaultMinutes);
  const yields={};let evidence;
  if(samples.length){for(const x of samples)for(const [id,n]of Object.entries(x.materials))yields[id]=(yields[id]||0)+n/samples.length;evidence=`${samples.length} observed whole runs`;}
  else{for(const r of [...m.rewards[mode],...(t.sRank?[m.s_rank[mode]]:[]),...(t.dire?[m.dire[mode]]:[])])if(r.material!==255&&r.quantity>0)yields[r.material]=(yields[r.material]||0)+r.quantity;evidence=record?.time_seconds?'saved time × 1.25; table yields':'default duration; table yields';}
  rows.push({key,name:m.name,mode,minutes,yields,evidence});
 }
 return rows;
}
const dropHints={52:'Ordinary Titans in late True Attack missions; harvest material-bearing limbs',57:'Normal-mode Dire Titans, including early story missions',58:'Higher-level normal-mode Dire Titans',59:'True Attack Dire Titans; Sign of a Counterattack is a commonly used farm',60:'Female Titan in normal Choices and Consequences or Soldiers Dance',61:'Female Titan in True Attack Choices and Consequences or Soldiers Dance',62:'Armored Titan in normal All Men, Move Out!',63:'Armored Titan in True Attack All Men, Move Out! or the Soldiers Dance Dire target',64:'Beast Titan in normal Choices and Consequences as the Dire target',65:'Beast Titan in True Attack Choices and Consequences as the Dire target',66:'Colossal Titan in normal Last Line of Defense',67:'Colossal Titan in True Attack Last Line of Defense'};
function planHTML(s,t){
 const missing=new Set(s.gallery.filter(x=>!x.acquired).map(x=>x.key));let selected=C.equipment.filter(x=>x.required&&missing.has('equipment:'+x.key));
 if(t.goal==='perfected')selected=selected.filter(x=>x.name.startsWith('Perfected'));
 if(t.goal==='rozen')selected=selected.filter(x=>x.name.startsWith('Rozen'));
 const craft=AOTPlanner.crafting(C,s,selected.map(x=>x.key),t.useInventory);
 const buyable=new Set(s.materials.filter(x=>x.shop_state>=9).map(x=>x.id)),shortages=craft.deficits.filter(x=>!t.buyShop||!buyable.has(x.id));
 const missions=effectiveMissions(s,t),plan=AOTPlanner.allocate(shortages,missions);
 const shopCost=t.buyShop?craft.deficits.filter(x=>buyable.has(x.id)).reduce((n,x)=>n+x.need*C.material_prices[x.id],0):0;
 const fundsGap=Math.max(0,craft.craftingFunds+shopCost-s.summary.funds);
 const formatTime=n=>`${(n/60).toFixed(1)} h`;
 const result=plan.uncovered.length?`At least ${formatTime(plan.minutes)} of covered farming. ${plan.uncovered.length} material types still need a source or run samples.`:`Modelled farming: ${formatTime(plan.minutes)}. Planning range ${formatTime(plan.minutes*.8)}–${formatTime(plan.minutes*1.5)}; this is a timing assumption, not a statistical confidence interval.`;
 const controls=`<div class="controls"><label>Goals <select data-setting="goal"><option value="all" ${t.goal==='all'?'selected':''}>All missing equipment</option><option value="perfected" ${t.goal==='perfected'?'selected':''}>Perfected set</option><option value="rozen" ${t.goal==='rozen'?'selected':''}>Rozen set</option></select></label><label>Modes <select data-setting="mode">${['both','normal','true'].map(x=>`<option ${x===t.mode?'selected':''}>${x}</option>`).join('')}</select></label><label><input type="checkbox" data-setting="sRank" ${t.sRank?'checked':''}>Assume S rank</label><label><input type="checkbox" data-setting="dire" ${t.dire?'checked':''}>Include Dire rewards</label><label><input type="checkbox" data-setting="buyShop" ${t.buyShop?'checked':''}>Buy shop-flagged materials</label><label><input type="checkbox" data-setting="useInventory" ${t.useInventory?'checked':''}>Consume unfortified inventory</label><label>Fallback min/run <input data-setting="defaultMinutes" type="number" min="0.1" step="0.1" value="${t.defaultMinutes}"></label><label>Other cleanup hours <input data-setting="cleanupHours" type="number" min="0" step="0.5" value="${t.cleanupHours??''}" placeholder="Unknown"></label></div>`;
 let html=controls+`<div class="notice">${esc(result)}<br>${craft.steps.length} development/upgrade steps. ${selected.length} missing equipment goals. ${t.cleanupHours===null?'100% ETA remains unknown until you budget non-farming cleanup.':`With ${t.cleanupHours} h cleanup: ${formatTime(plan.minutes+t.cleanupHours*60)} ${plan.uncovered.length?'minimum; blocked materials excluded':'modelled total'}.`}</div><p>Greedy shared-reward plan, not a proven minimum. Base-game equipment goals only; horses and missing scenes/models require separate cleanup. Upgrade chains are rebuilt where necessary. Fortified inventory is always protected. Crafting fees: ${craft.craftingFunds.toLocaleString()}. Shop material costs: ${t.buyShop?craft.deficits.filter(x=>buyable.has(x.id)).reduce((n,x)=>n+x.need*C.material_prices[x.id],0).toLocaleString():'not selected'}. Shop exclusions use the save’s availability flag; confirm stock before relying on purchases.</p>`;
 if(fundsGap)html+=`<div class="notice warning">Crafting and selected purchases exceed current funds by ${fundsGap.toLocaleString()}. Earn those funds or change the purchase plan. Money farming is not included in the ETA.</div>`;
 if(craft.blocked.length)html+=`<p class="error">Unresolved crafting routes: ${esc(craft.blocked.join(', '))}</p>`;
 if(plan.uncovered.length)html+=`<div class="notice warning">No quantified source in this plan: ${esc(plan.uncovered.map(x=>`${C.materials[x.id]} × ${Math.ceil(x.need)}`).join(', '))}. Enable Dire rewards if you will complete their conditions, or log whole-run drops. Random limb drops are not assumed.</div>`;
 html+=`<details ${plan.uncovered.length?'open':''}><summary>Where to get body-part materials</summary><ul>${plan.uncovered.map(x=>`<li><strong>${esc(C.materials[x.id])}</strong>: ${esc(dropHints[x.id]||'Find this material in the mission reward lists, or record a source in Run log')}. Remaining ${Math.ceil(x.need)}. Log full-run yields to estimate repetitions.</li>`).join('')}</ul><p>Break material-bearing limbs before the nape. Clear rewards below exclude random limb drops until you provide whole-run samples.</p></details>`;
 html+=table(plan.rows,[['Do this mission',r=>`${esc(r.name)}<br><small>${r.mode}</small>`],['Runs',r=>r.runs],['Time',r=>formatTime(r.runs*r.minutes)],['Materials per run',r=>esc(recipeText(Object.entries(r.yields).map(([id,q])=>({material:Number(id),quantity:Math.round(q*100)/100}))))],['Basis',r=>esc(r.evidence)]]);
 html+=`<details><summary>Material shopping and farming list</summary>${table(craft.deficits.filter(x=>x.need),[['Material',r=>esc(r.name)],['Required',r=>r.total],['Held',r=>r.held],['Missing',r=>r.need],['Action',r=>t.buyShop&&buyable.has(r.id)?'Buy in shop':'Farm']])}</details><details><summary>Crafting order</summary>${table(craft.steps,[['Action',r=>esc(r.route)],['Item',r=>esc(r.name)],['Materials',r=>esc(recipeText(r.materials))]])}</details>`;
 shown=craft.deficits;return html;
}
function logHTML(t){return `<p>Record the full reward-screen material totals and time including loading. A sample replaces table estimates for that mission, so record every useful material, including zeros for rare drops that failed. Repeated runs improve estimates. Averages are expectations, never guaranteed drop rates.</p><div class="split"><div><label>Mission <select id="logMission">${['normal','true'].flatMap(mode=>C.missions.map(m=>`<option value="${mode}:${m.id}">${esc(mode+' · '+m.name)}</option>`)).join('')}</select></label><p><label>Whole-run minutes <input id="logMinutes" type="number" min="0.1" step="0.1" value="10"></label></p><label>Materials gained, one per line: ID = quantity</label><textarea id="logMaterials" placeholder="61=5&#10;65=2&#10;27=3"></textarea><button id="addLog">Add run</button><p><small>Material IDs are shown in Materials CSV. Example: 61 glowing crystal, 65 ominous crystal, 10 S-grade ultra-hard steel.</small></p></div><div>${table(t.samples,[['Mission',r=>esc(r.key)],['Minutes',r=>r.minutes],['Drops',r=>esc(recipeText(Object.entries(r.materials).map(([id,q])=>({material:Number(id),quantity:q}))))],['',r=>`<button data-remove="${esc(r.id)}">Remove</button>`]])}</div></div>`;}
function bindLog(){
 $('#addLog').onclick=()=>{try{$('#error').textContent='';const minutes=Number($('#logMinutes').value);if(!Number.isFinite(minutes)||minutes<=0||minutes>1440)throw Error('Enter a duration between 0 and 1440 minutes.');const materials={};for(const line of $('#logMaterials').value.split('\n').filter(x=>x.trim())){const match=line.trim().match(/^(\d+)\s*=\s*(\d+)$/);if(!match)throw Error('Use material ID = quantity, one per line.');const id=Number(match[1]),q=Number(match[2]);if(!C.materials[id]||q>1000000)throw Error('Invalid material or quantity');materials[id]=q;}if(!Object.keys(materials).length)throw Error('Enter the materials gained, even if a rare drop quantity is zero.');profile().settings.samples.push({id:String(Date.now()),key:$('#logMission').value,minutes,materials});persist();render();}catch(e){$('#error').textContent=e.message;}};
 document.querySelectorAll('[data-remove]').forEach(x=>x.onclick=()=>{profile().settings.samples=profile().settings.samples.filter(y=>y.id!==x.dataset.remove);persist();render();});
}
render();
