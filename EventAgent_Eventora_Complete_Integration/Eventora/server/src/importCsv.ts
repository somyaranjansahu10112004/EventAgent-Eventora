/**
 * Import a reviewed CSV into the local JSON dataset.
 * Usage from the server directory: npm run import:csv -- ../Today's\ Lead(1).csv
 * This creates stable IDs from source row order; review duplicates before replacing the production dataset.
 */
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { parse } from 'csv-parse/sync';
type Row=Record<string,string|undefined>;
const input=process.argv.slice(2).join(' ').trim();
if(!input){console.error('Usage: npm run import:csv -- path/to/events.csv');process.exit(1);}
const csv=await readFile(path.resolve(process.cwd(),input),'utf8');
const rows=parse(csv,{columns:true,skip_empty_lines:true,trim:true,bom:true}) as Row[];
const text=(v:unknown)=>typeof v==='string'&&v.trim()&&!['nan','none','null'].includes(v.trim().toLowerCase())?v.trim():null;
const url=(v:string|null)=>{if(!v)return null;const m=v.match(/https?:\/\/[^\s,]+/);if(!m)return null;try{const u=new URL(m[0].replace(/[.]$/,''));return ['https:','http:'].includes(u.protocol)?u.toString():null;}catch{return null;}};
const date=(v:string|null)=>{if(!v)return {iso:null,original:null};const m=v.match(/^(\d{2})-(\d{2})-(\d{4})$/);if(!m)return {iso:null,original:v};const [,dd,mm,yyyy]=m;const d=new Date(`${yyyy}-${mm}-${dd}T12:00:00Z`);if(d.getUTCFullYear()!==Number(yyyy)||d.getUTCMonth()+1!==Number(mm)||d.getUTCDate()!==Number(dd))return {iso:null,original:v};return {iso:`${yyyy}-${mm}-${dd}`,original:v};};
const events=rows.map((r,i)=>{const originalSourceValue=text(r.source_url);const d=date(text(r.date));return {
 id:`evt-${String(i+1).padStart(3,'0')}`,eventName:text(r.event_name),category:text(r.category),venue:text(r.venue),area:text(r.area),city:text(r.City),date:d.iso,originalDate:d.original,time:text(r.time),registrationRequired:text(r.registration_required),sourceUrl:url(originalSourceValue),originalSourceValue,price:text(r.price),hostName:text(r.host_name),instagramId:text(r['Insta id ']),extraColumn:text(r['Unnamed: 12'])
};});
const output=path.resolve(process.cwd(),'data/events.json');
await writeFile(output,JSON.stringify(events,null,2)+'\n','utf8');
const missingDate=events.filter(e=>!e.date).length,missingName=events.filter(e=>!e.eventName).length;
console.log(`Imported ${events.length} rows to ${output}. Missing/ambiguous dates: ${missingDate}; missing event names: ${missingName}. Review duplicate events before production use.`);