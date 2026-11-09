import 'dotenv/config';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { pool } from './db.js';
const here=path.dirname(fileURLToPath(import.meta.url));
const file=process.argv[2] || path.resolve(here,'../data/events.json');
if(!pool) throw new Error('DATABASE_URL is required for migration');
const rows=JSON.parse(await readFile(file,'utf8')) as any[];
let count=0;
for(const e of rows){
 const name=String(e.eventName||e.event_name||'').trim(), city=String(e.city||'').trim(), date=String(e.date||'').slice(0,10);
 if(!e.id||!name||!city) continue;
 const validDate=/^\d{4}-\d{2}-\d{2}$/.test(date)?date:null;
 await pool.query(`INSERT INTO events(id,event_name,category,venue,area,city,event_date,original_date,event_time,registration_required,source_url,original_source_value,price,host_name,instagram_id,status,is_published,extra,published_at) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,'published',TRUE,$16,NOW()) ON CONFLICT(id) DO UPDATE SET event_name=EXCLUDED.event_name,category=EXCLUDED.category,venue=EXCLUDED.venue,area=EXCLUDED.area,city=EXCLUDED.city,event_date=EXCLUDED.event_date,event_time=EXCLUDED.event_time,source_url=EXCLUDED.source_url,price=EXCLUDED.price,host_name=EXCLUDED.host_name,is_published=TRUE,status='published',extra=EXCLUDED.extra,updated_at=NOW()`,[e.id,name,e.category||null,e.venue||null,e.area||null,city,validDate,e.originalDate||null,e.time||null,e.registrationRequired||null,e.sourceUrl||null,e.originalSourceValue||null,e.price||null,e.hostName||null,e.instagramId||null,e]);
 if(e.sourceUrl) await pool.query(`INSERT INTO event_sources(event_id,source_url,platform) VALUES($1,$2,$3) ON CONFLICT(event_id,source_url) DO NOTHING`,[e.id,e.sourceUrl,/instagram/i.test(e.sourceUrl)?'instagram':/facebook/i.test(e.sourceUrl)?'facebook':'web']);
 count++;
}
console.log(`Migrated ${count} Eventora JSON records (upsert; safe to rerun).`);
await pool.end();
