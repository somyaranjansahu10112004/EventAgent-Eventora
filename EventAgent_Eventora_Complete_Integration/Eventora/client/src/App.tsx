import { useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowDown, ArrowRight, CalendarDays, Check, ChevronDown, Clock3, Compass, ExternalLink, Filter, MapPin, MessageCircle, Moon, Search, Send, Sparkles, Sun, Ticket, X } from 'lucide-react';

type EventRecord = {id:string;eventName:string|null;category:string|null;venue:string|null;area:string|null;city:string|null;date:string|null;originalDate:string|null;time:string|null;registrationRequired:string|null;sourceUrl:string|null;price:string|null;hostName:string|null;instagramId:string|null};
type ChatMessage = {role:'user'|'assistant';content:string;events?:EventRecord[]};
const API = import.meta.env.VITE_API_URL || 'http://localhost:5000';
const dateLabel = (date:string|null) => date ? new Date(`${date}T12:00:00`).toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'}) : 'Date unavailable';
const isUpcoming = (e:EventRecord) => !!e.date && e.date >= new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Kolkata'});
const priceLabel = (p:string|null) => !p || p.toUpperCase()==='NA' ? 'Price not listed' : /free/i.test(p) ? p : /^\d+(\.\d+)?$/.test(p) ? `₹${p}` : p;
const unique = (values:(string|null)[]) => [...new Set(values.filter((x):x is string=>!!x))].sort((a,b)=>a.localeCompare(b));
const suggestions = ['What events are coming up this week?','Show me free events','Find music events in Bengaluru','What is happening this weekend?'];

function App(){
 const [events,setEvents]=useState<EventRecord[]>([]);
 const [loading,setLoading]=useState(true);
 const [query,setQuery]=useState('');
 const [category,setCategory]=useState('All categories');
 const [city,setCity]=useState('All locations');
 const [dateFilter,setDateFilter]=useState('upcoming');
 const [sort,setSort]=useState('soonest');
 const [selected,setSelected]=useState<EventRecord|null>(null);
 const [chatOpen,setChatOpen]=useState(false);
 const [chatInput,setChatInput]=useState('');
 const [chatBusy,setChatBusy]=useState(false);
 const [chatError,setChatError]=useState('');
 const [messages,setMessages]=useState<ChatMessage[]>([{role:'assistant',content:"Hi! I'm Eventora AI ✨ Ask me about upcoming events, locations, dates, prices, or a specific event. I'll use the event listings available on this site."}]);
 const [dark,setDark]=useState(()=>localStorage.getItem('eventora-theme')!=='light');
 const [mobileMenu,setMobileMenu]=useState(false);
 const [visibleGenreCount,setVisibleGenreCount]=useState(3);
 useEffect(()=>{localStorage.setItem('eventora-theme',dark?'dark':'light');document.documentElement.dataset.theme=dark?'dark':'light';},[dark]);
 useEffect(()=>{fetch(`${API}/api/events?includePast=true`).then(r=>{if(!r.ok)throw new Error('Could not load events');return r.json()}).then(d=>setEvents(d.events||[])).catch(()=>setChatError('Could not reach the event service. Start the backend and refresh the page.')).finally(()=>setLoading(false));},[]);
 const categories=useMemo(()=>unique(events.map(e=>e.category)),[events]);
 const cities=useMemo(()=>unique(events.map(e=>e.city)),[events]);
 const genreCards=useMemo(()=>categories
  .map(name=>({name,events:events.filter(event=>event.category===name)}))
  .filter(genre=>genre.events.length>0)
  .sort((a,b)=>b.events.length-a.events.length||a.name.localeCompare(b.name)),[categories,events]);
 const visibleGenres=genreCards.slice(0,visibleGenreCount);
 const filtered=useMemo(()=>{
  let result=events.filter(e=>{
   const hay=[e.eventName,e.category,e.venue,e.area,e.city,e.hostName].filter(Boolean).join(' ').toLowerCase();
   const matchQuery=hay.includes(query.toLowerCase());
   const matchCat=category==='All categories'||e.category===category;
   const matchCity=city==='All locations'||e.city===city;
   const matchDate=dateFilter==='all'||(dateFilter==='upcoming'?isUpcoming(e):e.date && e.date>=new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Kolkata'}) && e.date<=new Date(Date.now()+7*86400000).toLocaleDateString('en-CA',{timeZone:'Asia/Kolkata'}));
   return matchQuery&&matchCat&&matchCity&&matchDate;
  });
  if(sort==='soonest')result=result.sort((a,b)=>(a.date||'9999').localeCompare(b.date||'9999'));
  if(sort==='name')result=result.sort((a,b)=>(a.eventName||'').localeCompare(b.eventName||''));
  return result;
 },[events,query,category,city,dateFilter,sort]);
 const upcomingCount=events.filter(isUpcoming).length;
 async function sendMessage(text=chatInput){
  const message=text.trim();if(!message||chatBusy)return;
  setMessages(prev=>[...prev,{role:'user',content:message}]);setChatInput('');setChatBusy(true);setChatError('');
  try{
   const res=await fetch(`${API}/api/chat`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message,conversationId:'browser-session',timezone:'Asia/Kolkata'})});
   const data=await res.json();if(!res.ok)throw new Error(data.error||'The assistant could not respond.');
   setMessages(prev=>[...prev,{role:'assistant',content:data.answer||'I could not find a clear answer in the available event listings.',events:data.events||[]}]);
  }catch(e){setChatError(e instanceof Error?e.message:'Something went wrong. Please try again.');}
  finally{setChatBusy(false);}
 }
 const resetFilters=()=>{setQuery('');setCategory('All categories');setCity('All locations');setDateFilter('upcoming');setSort('soonest');};
 return <main className="app-shell">
  <header className="topbar glass">
   <a className="brand" href="#home" aria-label="Eventora home"><span className="brand-mark"><Compass size={20}/></span><span>eventora<span className="brand-dot">.</span></span></a>
   <nav className={mobileMenu?'nav-links nav-open':'nav-links'}><a href="#home" onClick={()=>setMobileMenu(false)}>Home</a><a href="#explore" onClick={()=>setMobileMenu(false)}>Explore events</a><a href="#categories" onClick={()=>setMobileMenu(false)}>Categories</a><button className="nav-ai" onClick={()=>{setChatOpen(true);setMobileMenu(false)}}><Sparkles size={15}/> Eventora AI</button></nav>
   <div className="top-actions"><button className="icon-button" aria-label="Toggle color theme" onClick={()=>setDark(!dark)}>{dark?<Sun size={18}/>:<Moon size={18}/>}</button><a className="nav-cta" href="#explore">Explore <ArrowRight size={16}/></a><button className="icon-button menu-toggle" aria-label="Toggle menu" onClick={()=>setMobileMenu(!mobileMenu)}>{mobileMenu?<X/>:<ChevronDown/>}</button></div>
  </header>
  <section className="hero" id="home">
   <div className="hero-orb orb-one"/><div className="hero-orb orb-two"/>
   <div className="hero-content"><div className="eyebrow"><span className="pulse-dot"/> YOUR CITY, YOUR NEXT STORY</div>
    <h1>Your next great<br/><span className="gradient-text">experience</span> starts here.</h1>
    <p className="hero-copy">Discover events, explore new experiences, and find what's happening around you — with an AI assistant that makes it effortless.</p>
    <div className="hero-search glass"><Search size={20}/><input aria-label="Search events" placeholder="Try “live music in Bengaluru”" value={query} onChange={e=>{setQuery(e.target.value);document.getElementById('explore')?.scrollIntoView({behavior:'smooth',block:'nearest'})}}/><button onClick={()=>document.getElementById('explore')?.scrollIntoView({behavior:'smooth'})}>Find events <ArrowRight size={16}/></button></div>
    <div className="hero-actions"><a className="button-primary" href="#explore">Explore events <ArrowDown size={16}/></a><button className="button-secondary" onClick={()=>setChatOpen(true)}><Sparkles size={16}/> Ask Eventora AI</button></div>
    <div className="hero-proof"><div className="proof-icon"><CalendarDays size={17}/></div><div><strong>{loading?'…':upcomingCount}</strong><span>upcoming listings in your dataset</span></div><span className="proof-separator"/><div className="proof-live"><span className="pulse-dot"/> Updated from your event sheet</div></div>
   </div>
   <div className="hero-art" aria-hidden="true"><div className="art-ring ring-a"/><div className="art-ring ring-b"/><div className="art-center"><Sparkles size={42}/><span>Make room<br/>for moments.</span></div><div className="floating-card fc-top glass"><span className="mini-icon purple"><MusicGlyph/></span><div><strong>Find your vibe</strong><small>Music · Culture · More</small></div></div><div className="floating-card fc-bottom glass"><span className="mini-icon blue"><CalendarDays size={17}/></span><div><strong>Plans, sorted.</strong><small>Discover something new</small></div><Check size={17} className="check-icon"/></div><div className="art-spark spark-one">✳</div><div className="art-spark spark-two">✦</div></div>
  </section>
  <section className="genre-discovery" aria-labelledby="genre-discovery-title">
   <div className="genre-heading">
    <div><div className="section-kicker">EXPLORE YOUR INTERESTS</div><h2 id="genre-discovery-title">Explore Events by <span className="gradient-text">Genre.</span></h2><p>Find your next experience, explore your interests, and discover what's happening.</p></div>
    <span className="genre-total">{genreCards.length} {genreCards.length===1?'genre':'genres'} available</span>
   </div>
   {loading?<div className="genre-grid">{[1,2,3].map(n=><div className="genre-card genre-skeleton" key={n}/>)}</div>:
    genreCards.length===0?<div className="genre-empty">Event genres will appear here when listings are available.</div>:
    <>
     <div className="genre-grid">
      {visibleGenres.map((genre,index)=><motion.article className={`genre-card glass genre-tone-${index%5}`} key={genre.name} initial={{opacity:0,y:12}} animate={{opacity:1,y:0}} transition={{duration:.25,delay:Math.min(index*.04,.2)}}>
       <div className="genre-card-top"><span className="genre-symbol"><Compass size={18}/></span><span className="genre-count">{genre.events.length} {genre.events.length===1?'event':'events'}</span></div>
       <h3>{genre.name}</h3>
       <div className="genre-preview">{genre.events.slice(0,2).map(event=><div className="genre-preview-row" key={event.id}><span className="genre-preview-dot"/><span title={event.eventName||'Event name unavailable'}>{event.eventName||'Event name unavailable'}</span></div>)}</div>
       <button className="genre-explore" onClick={()=>{setQuery('');setCategory(genre.name);setCity('All locations');setDateFilter('all');document.getElementById('explore')?.scrollIntoView({behavior:'smooth',block:'start'});}}>Explore genre <ArrowRight size={15}/></button>
      </motion.article>)}
     </div>
     {visibleGenreCount<genreCards.length&&<div className="genre-load-more-wrap"><button className="genre-load-more" onClick={()=>setVisibleGenreCount(count=>Math.min(count+3,genreCards.length))}>Load More <ArrowDown size={16}/><span className="genre-load-count">{Math.min(3,genreCards.length-visibleGenreCount)} more</span></button></div>}
    </>}
  </section>
  <section className="category-strip" id="categories"><div className="section-kicker">FIND YOUR KIND OF THING</div><div className="category-pills">{['All categories',...categories].slice(0,9).map((c,i)=><button key={c} className={`category-pill ${category===c?'active':''}`} onClick={()=>{setCategory(c);document.getElementById('explore')?.scrollIntoView({behavior:'smooth'})}}>{i===0?<Compass size={15}/>:<span className="category-dot" style={{'--i':i} as React.CSSProperties}/ >}{c}</button>)}</div></section>
  <section className="explore-section" id="explore">
   <div className="section-heading"><div><div className="section-kicker">THE GOOD STUFF</div><h2>Find your next <span className="gradient-text">thing.</span></h2><p>Real listings from your event sheet. Your next story is out there.</p></div><div className="result-counter"><strong>{filtered.length}</strong><span>matching events</span></div></div>
   <div className="filter-bar glass"><div className="filter-search"><Search size={18}/><input aria-label="Search events" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search events, hosts, keywords..."/>{query&&<button onClick={()=>setQuery('')} aria-label="Clear search"><X size={15}/></button>}</div><div className="filter-control"><Filter size={16}/><select aria-label="Filter category" value={category} onChange={e=>setCategory(e.target.value)}>{['All categories',...categories].map(c=><option key={c}>{c}</option>)}</select></div><div className="filter-control"><MapPin size={16}/><select aria-label="Filter location" value={city} onChange={e=>setCity(e.target.value)}>{['All locations',...cities].map(c=><option key={c}>{c}</option>)}</select></div><div className="filter-control"><CalendarDays size={16}/><select aria-label="Filter date" value={dateFilter} onChange={e=>setDateFilter(e.target.value)}><option value="upcoming">Upcoming</option><option value="week">Next 7 days</option><option value="all">All dates</option></select></div><button className="clear-button" onClick={resetFilters}>Reset</button></div>
   <div className="results-meta"><span>{loading?'Loading event listings…':`Showing ${filtered.length} of ${events.length} listings`}</span><label>Sort by <select value={sort} onChange={e=>setSort(e.target.value)}><option value="soonest">Soonest first</option><option value="name">Event name</option></select></label></div>
   {loading?<div className="event-grid">{[1,2,3,4,5,6].map(n=><div className="skeleton-card" key={n}/>)}</div>:filtered.length===0?<div className="empty-state"><span className="empty-icon"><Search size={24}/></span><h3>No matching events</h3><p>Try another search or clear your filters to see more listings.</p><button className="button-primary" onClick={resetFilters}>Clear filters</button></div>:<div className="event-grid">{filtered.map((event,i)=><motion.article className="event-card glass" key={event.id} initial={{opacity:0,y:12}} animate={{opacity:1,y:0}} transition={{delay:Math.min(i*.025,.2)}} whileHover={{y:-5}}><div className={`event-visual visual-${i%5}`}><div className="visual-shape shape-one"/><div className="visual-shape shape-two"/><span className="visual-category">{event.category||'Event'}</span><span className="visual-monogram">{(event.eventName||'E').split(/\s+/).slice(0,2).map(x=>x[0]).join('').toUpperCase()}</span><span className="visual-date"><CalendarDays size={13}/>{dateLabel(event.date)}</span></div><div className="event-body"><div className="event-title-row"><h3>{event.eventName||'Event name unavailable'}</h3><span className="event-price">{priceLabel(event.price)}</span></div><div className="event-meta"><span><MapPin size={14}/>{[event.area,event.city].filter(Boolean).join(', ')||'Location unavailable'}</span><span><Clock3 size={14}/>{event.time||'Time not listed'}</span></div><div className="event-card-footer"><span className="host-name">{event.hostName?`By ${event.hostName}`:'Organizer not listed'}</span><button onClick={()=>setSelected(event)} className="details-link">Details <ArrowRight size={15}/></button></div></div></motion.article>)}</div>}
  </section>
  <section className="ai-banner"><div className="ai-banner-glow"/><div className="ai-banner-icon"><Sparkles size={27}/></div><div className="ai-banner-copy"><div className="section-kicker">YOUR PERSONAL EVENT SIDEKICK</div><h2>Not sure what you're in the mood for?</h2><p>Tell Eventora AI what you love. Get answers grounded in the event listings, not guesswork.</p></div><button className="button-primary" onClick={()=>setChatOpen(true)}>Ask the AI <MessageCircle size={16}/></button></section>
  <footer className="footer"><a className="brand" href="#home"><span className="brand-mark"><Compass size={18}/></span><span>eventora<span className="brand-dot">.</span></span></a><span>Discover what's happening.</span><a href="#explore">Back to events ↑</a></footer>
  <AnimatePresence>{selected&&<motion.div className="modal-backdrop" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} onMouseDown={e=>{if(e.target===e.currentTarget)setSelected(null)}}><motion.div className="event-modal glass" initial={{opacity:0,y:20,scale:.98}} animate={{opacity:1,y:0,scale:1}} exit={{opacity:0,y:10}} role="dialog" aria-modal="true" aria-label="Event details"><button className="modal-close icon-button" onClick={()=>setSelected(null)} aria-label="Close details"><X/></button><div className="modal-art"><span className="visual-category">{selected.category||'Event'}</span><span className="modal-monogram">{(selected.eventName||'E').slice(0,1).toUpperCase()}</span></div><div className="modal-content"><div className="section-kicker">EVENT DETAILS</div><h2>{selected.eventName||'Event name unavailable'}</h2><div className="detail-list"><Detail icon={<CalendarDays/>} label="Date" value={dateLabel(selected.date)}/><Detail icon={<Clock3/>} label="Time" value={selected.time||'Not listed in the source'}/><Detail icon={<MapPin/>} label="Venue" value={[selected.venue,selected.area,selected.city].filter(Boolean).join(', ')||'Not listed in the source'}/><Detail icon={<Ticket/>} label="Price" value={priceLabel(selected.price)}/><Detail icon={<Sparkles/>} label="Organizer" value={selected.hostName||'Not listed in the source'}/><Detail icon={<Check/>} label="Registration" value={selected.registrationRequired||'Requirements not listed'}/></div><p className="source-note">Details are shown as provided in the event sheet. Confirm event information with the organizer before making plans.</p>{selected.sourceUrl&&<a className="button-primary modal-register" href={selected.sourceUrl} target="_blank" rel="noopener noreferrer">Open original listing <ExternalLink size={16}/></a>}</div></motion.div></motion.div>}</AnimatePresence>
  <AnimatePresence>{chatOpen&&<motion.div className="chat-panel glass" initial={{opacity:0,y:24,scale:.98}} animate={{opacity:1,y:0,scale:1}} exit={{opacity:0,y:12,scale:.98}} role="dialog" aria-label="Eventora AI chat"><div className="chat-header"><div className="chat-avatar"><Sparkles size={19}/></div><div className="chat-heading"><strong>Eventora AI</strong><span><i/> Here to help you discover</span></div><button className="icon-button" onClick={()=>setMessages([messages[0]])} title="Clear conversation"><span className="clear-chat-label">Clear</span></button><button className="icon-button" onClick={()=>setChatOpen(false)} aria-label="Close chat"><X/></button></div><div className="chat-messages" aria-live="polite">{messages.map((m,i)=><div key={i} className={`message-row ${m.role}`}><div className="message-avatar">{m.role==='assistant'?<Sparkles size={14}/>: 'Y'}</div><div className="message-content"><div className="message-bubble">{m.content}</div>{m.events&&m.events.length>0&&<div className="chat-event-list">{m.events.slice(0,4).map(e=><button className="chat-event" key={e.id} onClick={()=>{setSelected(e);setChatOpen(false)}}><span><strong>{e.eventName||'Event name unavailable'}</strong><small>{dateLabel(e.date)} · {[e.area,e.city].filter(Boolean).join(', ')||'Location unavailable'}</small></span><ArrowRight size={15}/></button>)}</div>}</div></div>)}{chatBusy&&<div className="message-row assistant"><div className="message-avatar"><Sparkles size={14}/></div><div className="typing-bubble"><i/><i/><i/></div></div>}{chatError&&<div className="chat-error">{chatError}<button onClick={()=>sendMessage(messages.filter(m=>m.role==='user').slice(-1)[0]?.content||'Help me find events')}>Retry</button></div>}</div><div className="suggested-prompts">{suggestions.slice(0,2).map(s=><button key={s} onClick={()=>sendMessage(s)}>{s}</button>)}</div><form className="chat-composer" onSubmit={e=>{e.preventDefault();sendMessage()}}><input aria-label="Ask about events" placeholder="Ask about events..." value={chatInput} onChange={e=>setChatInput(e.target.value)}/><button type="submit" disabled={!chatInput.trim()||chatBusy} aria-label="Send message"><Send size={17}/></button></form><div className="chat-footnote">Answers are based on available event listings.</div></motion.div>}</AnimatePresence>
  {!chatOpen&&<button className="chat-launcher" onClick={()=>setChatOpen(true)} aria-label="Open Eventora AI"><Sparkles size={20}/><span>Ask Eventora AI</span><span className="launcher-pulse"/></button>}
 </main>;
}
function Detail({icon,label,value}:{icon:React.ReactNode;label:string;value:string}){return <div className="detail-row"><span className="detail-icon">{icon}</span><span className="detail-label">{label}</span><strong>{value}</strong></div>}
function MusicGlyph(){return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>}
export default App;