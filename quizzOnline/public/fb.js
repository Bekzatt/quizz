// ================= FIREBASE — басты бет пен «Білім жарысы» үшін ортақ =================
// Тек сайтта жұмыс істейді (Firebase Hosting немесе эмулятор :5000). Файлды екі рет басып ашқанда — FB жоқ, бәрі офлайн.
// Кіру: Google аккаунты болса — сол (сұрақтар бұлтта сақталады), болмаса — анонимді (ойын үшін жеткілікті).
const FBV='10.12.2';
const ON_SITE=/\.web\.app$|\.firebaseapp\.com$/.test(location.hostname) || (/^(localhost|127\.0\.0\.1)$/.test(location.hostname) && location.port==='5000');
let FB=null, fbPromise=null;
function fbInit(){ if(!fbPromise) fbPromise=fbInitInner().catch(e=>{ fbPromise=null; throw e; }); return fbPromise; }
async function fbInitInner(){
  if(!ON_SITE) throw new Error('noconfig');
  const emu=/^(localhost|127\.0\.0\.1)$/.test(location.hostname) && location.port==='5000';
  const base=`https://www.gstatic.com/firebasejs/${FBV}/`;
  const [appM,authM,dbM]=await Promise.all(['firebase-app.js','firebase-auth.js','firebase-database.js'].map(f=>import(base+f)));
  let cfg=null;
  try{ const r=await fetch('/__/firebase/init.json',{cache:'no-store'}); if(r.ok) cfg=await r.json(); }catch(e){}
  if(!cfg || !cfg.projectId) throw new Error('noconfig');
  if(emu) cfg={apiKey:'demo-key',authDomain:'localhost',...cfg};
  if(!cfg.databaseURL) cfg.databaseURL=`https://${cfg.projectId}-default-rtdb.firebaseio.com`;
  const app=appM.initializeApp(cfg);
  const auth=authM.getAuth(app);
  const db=dbM.getDatabase(app);
  if(emu){ authM.connectAuthEmulator(auth,'http://127.0.0.1:9099',{disableWarnings:true}); dbM.connectDatabaseEmulator(db,'127.0.0.1',9000); }
  // Бұрын кірген пайдаланушы (Google немесе анонимді) болса — соны қолданамыз, Google кірісін жоғалтпау үшін
  const prev=await new Promise(res=>{ const off=authM.onAuthStateChanged(auth,u=>{ off(); res(u); }); });
  const user=prev || (await authM.signInAnonymously(auth)).user;
  FB={...dbM, db, auth, A:authM, uid:user.uid, user, offset:0, r:p=>dbM.ref(db,p)};
  dbM.onValue(dbM.ref(db,'.info/serverTimeOffset'),s=>{ FB.offset=s.val()||0; });
  return FB;
}
const isGoogleUser=()=>!!(FB && FB.user && !FB.user.isAnonymous);

// ---------- Сайт статистикасы (жеке дерек жоқ: тек күн сайынғы санауыштар) ----------
// Firebase Console → Realtime Database → stats/ЖЖЖЖ-АА-КК: visit (бір браузер күніне бір рет), login, g_* (ойын басталды), room, online, local, join.
function track(ev){
  if(!ON_SITE) return;
  const d=new Date(), day=`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  fbInit().then(fb=>fb.set(fb.r(`stats/${day}/${ev}`), fb.increment(1))).catch(()=>{});
}
function trackVisit(){
  const d=new Date().toDateString();
  try{ if(localStorage.getItem('og_vday')===d) return; localStorage.setItem('og_vday',d); }catch(e){ return; }
  track('visit');
}
