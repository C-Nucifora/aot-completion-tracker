/* Pure planning functions shared by the browser and command-line checks. */
(function(root){
'use strict';
function crafting(catalog,snapshot,selected,allowInventory=false){
 const items=new Map(catalog.equipment.map(x=>[x.key,x])), done=new Set(snapshot.gallery.filter(x=>x.acquired).map(x=>x.key.replace(/^equipment:/,'')));
 const pool=new Map(), totals={}, steps=[], blocked=[];
 if(allowInventory) for(const x of snapshot.inventory) if(!x.fortification)pool.set(x.key,(pool.get(x.key)||0)+1);
 function make(key,trail=[]){
  if((pool.get(key)||0)>0)return true;
  const e=items.get(key);if(!e||trail.includes(key)){blocked.push(key);return false;}
  let recipe,route;
  if(e.develop.length){recipe=e.develop;route='Develop';}
  else if(e.parent!==255&&e.upgrade.length){
   const parent=`${e.group_id}:${e.parent}`;
   if(!make(parent,[...trail,key]))return false;
   pool.set(parent,pool.get(parent)-1);recipe=e.upgrade;route='Upgrade';
  }else{blocked.push(e.name);return false;}
  for(const x of recipe)totals[x.material]=(totals[x.material]||0)+x.quantity;
  steps.push({key,name:e.name,route,materials:recipe,price:route==='Develop'?e.price:e.upgrade_price});
  done.add(key);pool.set(key,(pool.get(key)||0)+1);return true;
 }
 for(const key of selected)if(!done.has(key))make(key);
 const held=new Map(snapshot.materials.map(x=>[x.id,x.count]));
 const deficits=Object.entries(totals).map(([id,total])=>({id:Number(id),name:catalog.materials[id],total,held:held.get(Number(id))||0,need:Math.max(0,total-(held.get(Number(id))||0))}));
 return {steps,deficits,blocked:[...new Set(blocked)],fundsKnown:steps.every(s=>s.price!==null),craftingFunds:steps.reduce((n,s)=>n+(s.price||0),0)};
}
function allocate(deficits,missions){
 const left=Object.fromEntries(deficits.filter(x=>x.need>0).map(x=>[x.id,x.need])), rows=[];
 // Greedy coverage per minute. Shared rewards reduce all outstanding deficits together.
 for(let iteration=0;iteration<100000&&Object.values(left).some(x=>x>1e-8);iteration++){
  let best=null,score=0;
  for(const m of missions){
   if(!(m.minutes>0)||!Number.isFinite(m.minutes))continue;
   let gain=0;for(const [id,q] of Object.entries(m.yields))if(Number.isFinite(q)&&q>0)gain+=Math.min(left[id]||0,q)/Math.max(1,left[id]||0);
   const value=gain/m.minutes;if(value>score){score=value;best=m;}
  }
  if(!best||score===0)break;
  let row=rows.find(x=>x.key===best.key);if(!row){row={...best,runs:0};rows.push(row);}row.runs++;
  for(const [id,q] of Object.entries(best.yields))if(q>0&&left[id])left[id]=Math.max(0,left[id]-q);
 }
 return {rows,minutes:rows.reduce((n,x)=>n+x.runs*x.minutes,0),uncovered:Object.entries(left).filter(([,q])=>q>1e-8).map(([id,need])=>({id:Number(id),need}))};
}
const api={crafting,allocate};if(typeof module!=='undefined')module.exports=api;root.AOTPlanner=api;
})(typeof window!=='undefined'?window:globalThis);
