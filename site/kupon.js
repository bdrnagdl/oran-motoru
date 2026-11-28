// Kuponlar: sitenin günlük kuponları (bugün / yarın), geçmiş kuponlar, "En başarılı bahisler" ve "Kupon oluştur".
{
const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const yuz=v=>"%"+(v*100).toLocaleString("tr-TR",{maximumFractionDigits:v<0.01?1:0});
const say=v=>Number(v).toLocaleString("tr-TR",{maximumFractionDigits:2});
const o2=v=>Number(v).toFixed(2).replace(".",",");
const isoTR=d=>new Intl.DateTimeFormat("en-CA",{timeZone:"Europe/Istanbul"}).format(d);
const BUGUN=isoTR(new Date()),YARIN=isoTR(new Date(Date.now()+86400000));
const kisa=iso=>iso.slice(8,10)+"."+iso.slice(5,7);
const uzun=iso=>new Date(iso+"T12:00:00Z").toLocaleDateString("tr-TR",{day:"numeric",month:"long",year:"numeric",weekday:"long"});
const DURUM={tuttu:["Tuttu","d-ok"],yatti:["Yattı","d-no"],kismen:["Kısmen geri dönüş","d-mid"],bekliyor:["Sonuç bekleniyor","d-wait"],bilinmiyor:["Sonuç bilinmiyor","d-wait"]};
const rozet=d=>DURUM[d]?`<span class="dz ${DURUM[d][1]}">${DURUM[d][0]}</span>`:"";
const RENK={banko:"",sistem:" y",iyms:" iy"};

// ---- "Kopyala": kuponun seçimlerini düz metin olarak panoya alır
const kopyaDugme=(baslik,satirlar)=>`<button type="button" class="kopyala" data-metin="${esc(baslik+"\n"+satirlar.join("\n"))}">Kuponu kopyala</button>`;
document.addEventListener("click",e=>{
 const b=e.target.closest(".kopyala");if(!b)return;
 const ok=()=>{b.textContent="Kopyalandı";setTimeout(()=>b.textContent="Kuponu kopyala",1800)};
 (navigator.clipboard?navigator.clipboard.writeText(b.dataset.metin):Promise.reject()).then(ok).catch(()=>{
  const t=document.createElement("textarea");t.value=b.dataset.metin;document.body.appendChild(t);t.select();
  try{document.execCommand("copy");ok()}catch(_){b.textContent="Kopyalanamadı"}t.remove()});
});

// ---- kombine kupon uyarısı: gerçekçi ihtimal düşükse açıkça söyle
const ihUyari=ih=>ih>0&&ih<0.5?`<p class="knote warn">Bu kuponun hepsinin birden tutma ihtimali yaklaşık ${ih>=0.1?yuz(ih):`${say(Math.round(1/ih))}'da 1`}. ${ih<0.2?"Çok maçlı kuponlarda bir maç yatması çok olasıdır.":"Her maç eklendikçe ihtimal düşer."}</p>`:"";
// ---- canlı oran: seçimin bültendeki şimdiki oranını getirir, değiştiyse yanında gösterir
const BUL="https://sportsbookv2.iddaa.com/sportsbook/",EVC={};
const evAl=id=>EVC[id]||(EVC[id]=fetch(BUL+"event/"+id).then(r=>r.ok?r.json():null).then(j=>j&&j.data).catch(()=>null));
const canliAttr=(id,key,sov,n,oran)=>id&&key?` data-ev="${esc(id)}" data-k="${esc(key)}" data-sov="${esc(sov??"")}" data-n="${esc(n)}" data-oran="${oran}"`:"";
function canli(kok){
 for(const el of kok.querySelectorAll("[data-ev]:not([data-bakildi])")){
  el.dataset.bakildi="1";
  evAl(el.dataset.ev).then(d=>{
   if(!d)return;
   const m=(d.m||[]).find(m=>`${m.t}_${m.st}`===el.dataset.k&&String(m.sov??"")===el.dataset.sov);
   const o=m&&(m.o||[]).find(x=>String(x.n)===el.dataset.n);
   const eski=+el.dataset.oran,yeni=o&&o.odd;
   const t=document.createElement("small");t.className="simdi";
   if(!yeni)return;   // bulunamadıysa bir şey iddia etme
   if(Math.abs(yeni-eski)<0.005){t.textContent="güncel";t.classList.add("ayni")}
   else{t.textContent="şimdi "+o2(yeni);t.classList.add(yeni>eski?"cik":"dus")}
   el.after(t);
  });
 }
}
(()=>{const st=document.createElement("style");st.textContent=".simdi{display:block;font:600 11px Barlow,sans-serif;text-align:right;margin-top:2px}.simdi.ayni{color:var(--soluk)}.simdi.dus{color:#b4231a}.simdi.cik{color:var(--saha)}@media(prefers-color-scheme:dark){.simdi.dus{color:#ff8a80}.simdi.cik{color:#7fd3a4}}.gi{font-weight:700}.karne td,.karne th{padding:6px 10px}.karne{border-collapse:collapse;width:100%;font-size:14px}.karne th{text-align:left;font-weight:600;color:var(--soluk)}.karne td.n,.karne th.n{text-align:right}.karne tr+tr td{border-top:1px solid var(--cizgi)}";document.head.appendChild(st)})();

// ---- tek seçim satırı (kartların içinde)
const secim=(s,ek,ca)=>`<div class="sec${s.durum==="tuttu"?" ok":s.durum==="yatti"?" no":""}">
 <div class="r"><span class="m">${esc(s.mac)}</span><span class="o"><span${ca||""}>${s.oran?o2(s.oran):"–"}</span></span></div>
 <div class="i"><span>${esc(s.saat)}</span><span>${esc(s.lig)}</span>${s.mbs?`<span>MBS ${esc(s.mbs)}</span>`:""}</div>
 <span class="pk">${esc(s.secim)}</span>${rozet(s.durum)}${s.skor?`<div class="i">${esc(s.skor)}</div>`:""}${ek||""}
</div>`;

// ---- sitenin kupon kartı (günün kuponları ve geçmiş)
function kart(k,tam){
 const S=k.secimler.map(s=>({...s,mac:s.idd_ad||s.mac}));
 const simdi=Date.now()/1000;
 const sec=S.map(s=>secim(s,tam&&s.n?`<div class="i"><span class="gi">Gerçekçi ihtimal ${yuz(s.ortalama)}</span> · bülten oranı ${yuz(1/s.oran)} diyor</div><details><summary>Neden bu seçim?</summary><p>${esc(s.aciklama)}</p><p>Birebir aynı oranlı ${s.n} maçın ${s.hits} tanesinde oldu (${yuz(s.gecmis)}); az sayıda maçtan çıktığı için şans payı yüksek, ihtimal olarak kullanılmıyor.</p></details>`:"",
  tam&&s.durum!=="tuttu"&&s.durum!=="yatti"&&(!s.t||s.t>simdi)?canliAttr(s.idd_id,s.key,s.sov,s.sec,s.oran):"")).join("");
 const ih=S.length&&S.every(s=>s.ortalama)?S.reduce((a,s)=>a*s.ortalama,1):(k.tutma_olasiligi||0);
 let alt="";
 if(k.tur==="sistem"){
  let sonuc="";
  if(k.tutan!=null&&k.durum!=="bekliyor")sonuc=`<p class="knote"><b>${k.tutan}/${S.length} seçim tuttu.</b>${k.donus!=null?` Geri dönüş ${say(k.donus)} birim (${k.kolon} birim yatırılmıştı).`:""}</p>`;
  const rows=tam&&k.tablo?k.tablo.filter(t=>t.tutan>=1).map(t=>`<tr><td>${t.tutan} maç tutarsa</td><td class="n">${yuz(t.olasilik)}</td><td class="n">${t.en_cok===null?"–":t.en_cok?(t.en_az===t.en_cok?say(t.en_az):say(t.en_az)+" – "+say(t.en_cok)):"0"}</td></tr>`).join(""):"";
  alt=`<div class="tot"><div><b>${k.kolon??"–"}</b><span>kolon, her kolona 1 birim</span></div><div><b>${S.length}</b><span>maç</span></div></div>${sonuc}${rows?`<div class="scroll knote"><table class="st"><thead><tr><th>Durum</th><th class="n">İhtimal</th><th class="n">Geri dönüş (birim)</th></tr></thead><tbody>${rows}</tbody></table></div>`:""}`;
 }else{
  alt=`<div class="tot"><div><b>${k.toplam_oran?say(k.toplam_oran):"–"}</b><span>toplam oran</span></div>${tam?`<div><b>${yuz(ih)}</b><span>gerçekçi tutma ihtimali</span></div>`:""}</div>${tam&&k.durum!=="tuttu"&&k.durum!=="yatti"?ihUyari(ih):""}`;
 }
 const kopya=S.length?`<div class="kalt">${kopyaDugme(k.ad,S.map(s=>`${s.mac}: ${s.secim} (${o2(s.oran)})`))}</div>`:"";
 return `<article class="kart${RENK[k.tur]??" s"}"><header><h3>${esc(k.ad)}</h3>${rozet(k.durum)}${tam?`<p>${esc(k.not_)}</p>`:""}</header>${sec||'<p class="knote" style="padding-top:12px">Bu gün için bu kupona uygun maç bulunamadı.</p>'}${alt}${kopya}</article>`;
}

// ---- günün kuponları ve geçmiş
let IDX=[],FILTRE="tutan";
function gunGoster(iso){
 $("kgecmis").hidden=true;$("kgrid").hidden=false;$("kmeta").textContent="Yükleniyor…";$("kuyari").hidden=true;$("kgrid").innerHTML="";
 fetch(`arsiv/${iso}.json`,{cache:"no-store"}).then(r=>{if(!r.ok)throw 0;return r.json()}).then(j=>{
  $("kmeta").textContent=`${uzun(iso)} maçları. ${j.mac_sayisi} maç incelendi, ${j.uygun_mac??"?"} tanesinde aynı oranlı en az ${j.min_n??20} geçmiş maç vardı. Hazırlanma: ${j.hazirlandi}. Saatler Türkiye saatiyle.`;
  if(j.uyari){$("kuyari").textContent=j.uyari;$("kuyari").hidden=false}
  $("kgrid").innerHTML=j.kuponlar.map(k=>kart(k,true)).join("")+`<p class="knote">Oranlar kupon hazırlanırken (${esc(j.hazirlandi)}) bültenden alındı. Başlamamış maçlarda oranın altında "şimdi" yazıyorsa bültendeki oran o arada değişmiştir; "güncel" yazıyorsa aynıdır.</p>`;
  canli($("kgrid"));
 }).catch(()=>{$("kmeta").textContent=iso===BUGUN?"Bugünün kuponları henüz yayınlanmadı. Site kuponları günün ilk maçından yaklaşık 1 saat önce bir kez yayınlar; yayınlanan kupon bir daha değişmez.":"Bu günün kuponları henüz hazır değil."});
}
function gecmisGoster(){
 $("kgrid").hidden=true;$("kuyari").hidden=true;$("kgecmis").hidden=false;
 const G=IDX.filter(g=>g.tarih<BUGUN);
 const sayac={};for(const g of G)for(const k of g.kuponlar){const s=sayac[k.ad]=sayac[k.ad]||[0,0];if(["tuttu","yatti","kismen"].includes(k.durum)){s[1]++;if(k.durum==="tuttu")s[0]++}}
 $("kmeta").textContent=G.length?"Sitenin geçmişte hazırladığı kuponlar ve sonuçları. Sonuçlar maç bittikten yaklaşık yarım saat sonra işlenir.":"Henüz geçmiş kupon yok. Kuponlar her gün otomatik kaydedilir; sonuçlar maç bittikten yaklaşık yarım saat sonra işlenir.";
 let h=G.length?`<div class="ozet">${Object.entries(sayac).map(([a,[t,n]])=>`<div><b>${t}/${n}</b><span>${esc(a)} tuttu</span></div>`).join("")}</div>
 <div class="seg" role="group" aria-label="Filtre"><button type="button" class="segb${FILTRE==="tutan"?" on":""}" data-f="tutan">Tutan kuponlar</button><button type="button" class="segb${FILTRE==="hepsi"?" on":""}" data-f="hepsi">Bütün kuponlar</button></div>`:"";
 let bos=true;
 for(const g of G){
  const K=g.kuponlar.filter(k=>k.secimler.length&&(FILTRE==="hepsi"||k.durum==="tuttu"||k.durum==="kismen"));
  if(!K.length)continue;bos=false;
  h+=`<h3 class="gunbaslik">${esc(uzun(g.tarih))}</h3><div class="kgrid">${K.map(k=>kart(k,false)).join("")}</div>`;
 }
 if(bos&&G.length)h+=`<div class="empty" style="margin-top:14px">${FILTRE==="tutan"?"Henüz tutan kupon yok.":"Gösterilecek kupon yok."}</div>`;
 $("kgecmis").innerHTML=`<div id="karne"></div>`+h;
 karne();
}
// ---- karne: sitenin ihtimalleri gerçekte ne kadar tuttu (son 30 günün kayıtlı kuponlarından)
let KARNE=null;
function karne(){
 const yaz=()=>{const el=$("karne");if(!el||!KARNE)return;
  const S=KARNE;
  if(S.length<1){el.innerHTML="";return}
  const D=[[0,.3,"%30'un altı"],[.3,.5,"%30–50"],[.5,.7,"%50–70"],[.7,.85,"%70–85"],[.85,1.01,"%85 ve üstü"]];
  const rows=D.map(([a,b,l])=>{const x=S.filter(s=>s.g>=a&&s.g<b);if(!x.length)return"";
   const ort=f=>x.reduce((t,s)=>t+f(s),0)/x.length;
   return `<tr><td>${l}</td><td class="n">${x.length}</td><td class="n">${yuz(ort(s=>s.g))}</td><td class="n"><b>${yuz(ort(s=>s.t))}</b></td><td class="n">${yuz(ort(s=>s.a))}</td></tr>`}).join("");
  const top=S.filter(s=>s.t).length;
  el.innerHTML=`<h3 class="gunbaslik">Karne: dediklerimiz ne kadar tuttu?</h3><p class="note" style="margin:0 0 10px;max-width:72ch">Son ${KARNE.gun} günde sitenin kuponlarındaki ${S.length} sonuçlanmış seçimin ${top} tanesi tuttu. Aşağıda seçimler sitenin verdiği gerçekçi ihtimale göre gruplandı. İki sütun birbirine yakınsa site doğru ölçüyor demektir. Gün sayısı az olduğunda rakamlar şanstan çok etkilenir; birkaç hafta sonra anlamlı hale gelir.</p><div class="scroll"><table class="karne"><thead><tr><th>Sitenin dediği</th><th class="n">Seçim</th><th class="n">Ortalama tahmin</th><th class="n">Gerçekte tutan</th><th class="n">Aynı oranlı % (eski ölçü)</th></tr></thead><tbody>${rows}</tbody></table></div>`;
 };
 if(KARNE){yaz();return}
 const G=IDX.filter(g=>g.tarih<=BUGUN).map(g=>g.tarih).sort().reverse().slice(0,30);
 Promise.all(G.map(t=>fetch(`arsiv/${t}.json`,{cache:"no-store"}).then(r=>r.ok?r.json():null).catch(()=>null))).then(L=>{
  const S=[],gor=new Set();
  for(const j of L){if(!j)continue;for(const k of j.kuponlar)for(const s of k.secimler){
   if((s.durum!=="tuttu"&&s.durum!=="yatti")||!s.ortalama)continue;
   const id=(s.idd_ad||s.mac)+"|"+s.secim;if(gor.has(id))continue;gor.add(id);
   S.push({g:s.ortalama,t:s.durum==="tuttu"?1:0,a:s.gecmis||0})}}
  KARNE=S;KARNE.gun=G.length;yaz();
 });
}
$("kgecmis").addEventListener("click",e=>{const b=e.target.closest("[data-f]");if(!b)return;FILTRE=b.dataset.f;gecmisGoster()});
function sekmeler(){
 const T=[];
 T.push([BUGUN,`Bugün, ${kisa(BUGUN)}`]);   // yayınlanmadıysa "henüz yayınlanmadı" yazar
 if(IDX.some(g=>g.tarih===YARIN))T.push([YARIN,`Yarın, ${kisa(YARIN)}`]);
 T.push(["gecmis","Geçmiş kuponlar"]);
 $("ktabs").innerHTML=T.map(([v,l],i)=>`<button type="button" role="tab" class="tab${i===0?" on":""}" data-v="${v}" aria-selected="${i===0}">${esc(l)}</button>`).join("");
 sec(T[0][0]);
}
function sec(v){
 for(const b of $("ktabs").children){const on=b.dataset.v===v;b.classList.toggle("on",on);b.setAttribute("aria-selected",on)}
 v==="gecmis"?gecmisGoster():gunGoster(v);
}
$("ktabs").addEventListener("click",e=>{const b=e.target.closest(".tab");if(b)sec(b.dataset.v)});
fetch("arsiv/index.json",{cache:"no-store"}).then(r=>r.ok?r.json():[]).catch(()=>[]).then(j=>{IDX=j;sekmeler()});

// ---- havuzdan gelen seçimlerle kart (kupon oluştur ve en başarılı 5)
let HV=null,TUR="guvenli";
const num=v=>{const x=parseFloat(String(v).replace(",","."));return isFinite(x)?x:0};
function havuzKart(baslik,alt,K,cls,ekNot){
 const top=K.reduce((a,c)=>a*c.oran,1),ih=K.reduce((a,c)=>a*c.base,1),mbs=Math.max(...K.map(c=>c.mbc));
 const sec=K.map(c=>secim({mac:c.m.ad,oran:c.oran,saat:c.m.saat,lig:c.m.lig,mbs:c.mbc,secim:c.ad},
  `<div class="i"><span class="gi">Gerçekçi ihtimal ${yuz(c.base)}</span> · bülten oranı ${yuz(1/c.oran)} diyor</div><details><summary>Neden bu seçim?</summary><p>Bu maçın uluslararası 1-X-2 oranları ${c.m.oran.map(o2).join(" – ")}. Oranı buna yakın çok sayıda geçmiş maçta "${esc(c.ad)}" ${yuz(c.base)} oranında oldu. 2,5 yıllık testte gerçek sonuçlar bu yüzdeye uydu. Bültendeki ${o2(c.oran)} oranı yaklaşık ${yuz(1/c.oran)} ihtimal veriyor. Birebir aynı oranlı ${c.n} maçta ${c.hits} kez oldu (${yuz(c.hits/c.n)}); az maçtan çıktığı için şans payı yüksek. Bu oranlı maçlarda en sık skorlar: ${esc(c.m.skorlar)}.</p></details>`,
  canliAttr(c.m.id,c.key,c.sov,c.sec,c.oran))).join("");
 return `<article class="kart${cls}"><header><h3>${esc(baslik)}</h3><p>${esc(alt)}</p></header>${sec}<div class="tot"><div><b>${say(top)}</b><span>toplam oran</span></div><div><b>${yuz(ih)}</b><span>gerçekçi tutma ihtimali</span></div></div>${ihUyari(ih)}${ekNot||""}${K.length<mbs?`<p class="knote warn">Dikkat: bir maçın MBS'si ${mbs}; bültende oynamak için kuponda en az ${mbs} maç olmalı.</p>`:""}<p class="knote">Oranlar ${esc(HV.guncelleme)} itibarıyla bültenden alındı; oynamadan önce güncel oranı kontrol et. Bu bir tahmindir, kesinlik vermez.</p><div class="kalt">${kopyaDugme(baslik,K.map(c=>`${c.m.ad}: ${c.ad} (${o2(c.oran)})`))}</div></article>`;
}
function havuz(gs,min){
 const A=[],simdi=Date.now()/1000+300;
 HV.gunler.forEach((g,gi)=>{if(gs!=="hepsi"&&+gs!==gi)return;
  for(const s of g.secenekler){const m=g.maclar[s[0]];if(m.t<=simdi||s[2]<min)continue;
   A.push({m,mid:gi+"|"+s[0],ad:s[1],oran:s[2],mbc:s[3],hits:s[4],n:s[5],base:s[6],tahmin:s[6],key:s[8],sov:s[9],sec:s[10],p:s[4]/s[5]})}});
 return A;
}

// ---- en başarılı bahisler: her maç için yakın oranlı maçlarda en sık tutan bahis
function enIyi(){
 if(!HV)return;
 const sira=$("eisira").value;
 const deger=c=>sira==="ayni"?c.p:sira==="fark"?c.base-1/c.oran:c.base;
 const A=havuz($("eigun").value,num($("eimin").value)||1),best={};
 for(const c of A){const b=best[c.mid];if(!b||deger(c)>deger(b)||(deger(c)===deger(b)&&c.base>b.base))best[c.mid]=c}
 const R=Object.values(best).sort((a,b)=>deger(b)-deger(a)||b.base-a.base);
 if(!R.length){$("eilist").innerHTML='<div class="empty">Bu ayarlarla maç yok. En az oranı düşür ya da günü değiştir.</div>';return}
 EIR=R;
 const acik={gercek:"gerçekçi ihtimali en yüksekten aşağı doğru",fark:"gerçekçi ihtimali bülten oranının verdiği ihtimalden en çok yüksek olandan aşağı doğru",ayni:"birebir aynı oranlı maçlardaki yüzdeye göre (şans payı yüksek, gerçekçi değil)"}[sira];
 $("eilist").innerHTML=`<p class="note" style="margin:0 0 8px">${R.length} maç; ${acik}. Bir maça dokunursan o oranlarla oynanmış geçmiş maçların sonuçları açılır.</p><div class="scroll"><table class="tablo eit"><thead><tr><th>Saat</th><th>Maç</th><th>Bahis</th><th class="n">Gerçekçi ihtimal</th><th class="n gizle">Bülten oranının ihtimali</th><th class="n">Oran</th></tr></thead><tbody>${R.map((c,i)=>{const fark=c.base-1/c.oran;return `<tr class="eirow" data-i="${i}" tabindex="0" aria-label="${esc(c.m.ad)}: geçmiş maçları göster">
 <td class="saat">${esc(c.m.saat)}</td>
 <td><b>${esc(c.m.ad)}</b><small>${esc(c.m.lig)}</small></td>
 <td><span class="tag">${esc(c.ad)}</span></td>
 <td class="n"><div class="cub"><span style="width:${(c.base*100).toFixed(0)}%"></span></div><b class="yuzde">${yuz(c.base)}</b><small>aynı oranlı ${c.hits}/${c.n}</small></td>
 <td class="n gizle">${yuz(1/c.oran)}<small>${fark>=0?"bizimki "+Math.round(fark*100)+" puan yüksek":"bülten "+Math.round(-fark*100)+" puan yüksek"}</small></td>
 <td class="n"><b class="oranb"${canliAttr(c.m.id,c.key,c.sov,c.sec,c.oran)}>${o2(c.oran)}</b>${c.mbc>1?`<small>MBS ${c.mbc}</small>`:""}</td></tr>`}).join("")}</tbody></table></div>`+
  `<h3 class="gunbaslik">Listenin ilk ${Math.min(5,R.length)} bahsiyle kupon</h3><div class="tekkart">${havuzKart(`${Math.min(5,R.length)} maçlık kupon`,"Yukarıdaki listenin ilk bahisleri. Hepsinin birden tutması gerekir.",R.slice(0,5),"","")}</div>`;
 canli($("eilist"));
}
(()=>{const d=document.createElement("div");d.className="fl";d.innerHTML='<label class="lb" for="eisira">Sırala</label><select id="eisira"><option value="gercek">Gerçekçi ihtimale göre</option><option value="fark">Bülten oranına göre en avantajlı</option><option value="ayni">Aynı oranlı maçlara göre (şans payı yüksek)</option></select>';$("eimin").closest(".fl").after(d)})();
for(const k of ["eigun","eimin","eisira"])$(k).addEventListener("input",enIyi);
// listedeki maça dokununca: o maçın oranlarıyla geçmiş maç aramasını aç
let EIR=[];
(()=>{const st=document.createElement("style");st.textContent=".eit .eirow{cursor:pointer}.eit .eirow:hover td,.eit .eirow:focus-visible td{background:rgba(31,122,77,.08)}.eit .eirow:focus-visible{outline:2px solid var(--saha);outline-offset:-2px}";document.head.appendChild(st)})();
function eiAc(tr){
 const c=EIR[+tr.dataset.i];if(!c)return;
 const o=c.m.oran.map(v=>Number(v).toFixed(2).replace(".",","));
 ["o1","ox","o2"].forEach((id,i)=>{const el=$(id);el.value=o[i];el.dispatchEvent(new Event("input",{bubbles:true}));el.dispatchEvent(new Event("change",{bubbles:true}))});
 const s=$("secili");
 s.innerHTML=`<b>${esc(c.m.ad)}</b><span class="note">${esc(c.m.lig)}, ${esc(c.m.saat)}</span><p>Bu maçın uluslararası oranı ${o.join(" – ")}. Aşağıda bu oranlarla oynanmış geçmiş maçların sonuçları var. Listede gördüğün bahis "${esc(c.ad)}": oranı buna yakın geçmiş maçlarda ${yuz(c.base)} tuttu (birebir aynı oranlı ${c.n} maçta ${c.hits} kez).</p>`;
 s.hidden=false;
 setTimeout(()=>document.getElementById("sonuc").scrollIntoView({behavior:matchMedia("(prefers-reduced-motion: reduce)").matches?"auto":"smooth",block:"start"}),250);
}
$("eilist").addEventListener("click",e=>{if(e.target.closest("button,a,details"))return;const tr=e.target.closest(".eirow");if(tr)eiAc(tr)});
$("eilist").addEventListener("keydown",e=>{if(e.key!=="Enter"&&e.key!==" ")return;const tr=e.target.closest(".eirow");if(tr){e.preventDefault();eiAc(tr)}});

// ---- kupon oluştur
const VARS={guvenli:{adet:3,min:"1,20"},surpriz:{adet:5,min:"3,00"}};
$("kadet").innerHTML=[...Array(10)].map((_,i)=>`<option${i+1===3?" selected":""}>${i+1}</option>`).join("");
$("kturu").addEventListener("click",e=>{const b=e.target.closest("[data-tur]");if(!b)return;TUR=b.dataset.tur;
 for(const x of $("kturu").children){x.classList.toggle("on",x===b);x.setAttribute("aria-pressed",x===b)}
 $("kadet").value=VARS[TUR].adet;$("kmin").value=VARS[TUR].min;$("ksonuc").innerHTML=""});
function olustur(karistir){
 if(!HV){$("ksonuc").innerHTML='<div class="empty">Kupon verisi henüz hazır değil.</div>';return}
 const n=+$("kadet").value,min=num($("kmin").value),bt=$("kbahis").value;
 const A=havuz($("kgun").value,min).filter(c=>!bt||c.ad===bt);
 const puan=c=>(TUR==="guvenli"?c.tahmin:c.tahmin*c.oran)*(karistir?0.8+Math.random()*0.4:1);
 const sec=liste=>{const out=[],kul=new Set(),tur={};
  for(const c of liste.map(c=>[puan(c),c]).sort((a,b)=>b[0]-a[0]).map(x=>x[1])){
   if(kul.has(c.mid)||(!bt&&(tur[c.key]||0)>=2))continue;out.push(c);kul.add(c.mid);tur[c.key]=(tur[c.key]||0)+1;if(out.length===n)break}
  return out};
 let K=TUR==="surpriz"?sec(A.filter(c=>c.hits>=3&&c.base*c.oran>=0.95)):sec(A);
 if(K.length<n)K=sec(A);
 if(!K.length){$("ksonuc").innerHTML=`<div class="empty">${bt?`"${esc(bt)}" için bu ayarlarla uygun maç bulunamadı. En az oranı düşür, "Bugün ve yarın"ı seç ya da başka bir bahis türü dene.`:`Bu ayarlarla uygun seçim bulunamadı. En az oranı düşür ya da "Bugün ve yarın"ı seç.`}</div>`;return}
 const macSay=new Set(A.map(c=>c.mid)).size;
 $("ksonuc").innerHTML=`<div class="tekkart">${havuzKart(`${TUR==="surpriz"?"Sürpriz":"Güvenli"} kupon, ${K.length} maç`,`${bt?`Hepsi "${bt}". `:""}${macSay} uygun maç arasından, her seçimin oranı en az ${o2(min)}.`,K,TUR==="surpriz"?" s":"",
  K.length<n?`<p class="knote warn">İstediğin ${n} maç için yeterli seçim yok; ${K.length} maçlık kupon hazırlandı. En az oranı düşürmeyi${bt?" ya da başka bir bahis türünü":""} dene.</p>`:"")}<button type="button" class="ikincil" id="kbaska">Başka bir kupon öner</button></div>`;
 $("kbaska").addEventListener("click",()=>olustur(true));canli($("ksonuc"));
}
$("kyap").addEventListener("click",()=>olustur(false));
// bahis türü seçimi: sitedeki havuzda bulunan bütün bahisler, gruplara ayrılmış
const BGRUP=[["1_1","Maç sonucu"],["2_92","Çifte şans"],["2_101","Toplam gol alt / üst"],["2_89","Karşılıklı gol"],["2_60","İlk yarı gol alt / üst"],["2_730","İki yarıda da 1.5 üst / alt"],["2_729",null],["2_720","İlk yarı karşılıklı gol"],["2_821","2. yarı karşılıklı gol"],["2_866","İlk yarı KG / 2. yarı KG"],["2_88","İlk yarı sonucu"],["2_36","2. yarı sonucu"],["2_90","İlk yarı / maç sonu"],["2_7","Maç sonucu ve alt / üst"],["2_698","Maç sonucu ve karşılıklı gol"],["2_700","Alt / üst ve karşılıklı gol"],["2_724","İlk yarı sonucu ve İY alt / üst"],["2_699","İlk yarı sonucu ve İY karşılıklı gol"],["2_4","Toplam gol aralığı"],["2_91","Toplam gol tek / çift"],["2_719","İlk yarı gol tek / çift"],["2_603","Ev sahibi gol alt / üst"],["2_604","Deplasman gol alt / üst"],["2_722","Ev sahibi ilk yarı gol"],["2_723","Deplasman ilk yarı gol"],["2_861","Takım iki yarıda da gol atar"],["2_862",null],["2_69","Takım iki yarıyı da kazanır"],["2_72",null],["2_727","Takım en az bir yarıyı kazanır"],["2_728",null],["2_6","En çok gol olan yarı"],["2_84",null],["2_85",null],["2_11","Gol farkı"],["2_100","Handikaplı maç sonucu"]];
(()=>{const d=document.createElement("div");d.className="fl";d.innerHTML='<label class="lb" for="kbahis">Bahis türü</label><select id="kbahis" style="max-width:100%"><option value="">Karışık (en iyileri)</option></select>';$("kadet").closest(".fl").after(d)})();
function bahisDoldur(){
 const ad={},sira={};let grup=null;
 BGRUP.forEach(([k,g],i)=>{if(g)grup=g;ad[k]=grup;sira[k]=i});
 const G={};
 for(const g of HV.gunler)for(const x of g.secenekler){const k=x[8],gb=ad[k]||"Diğer";(G[gb]=G[gb]||{s:sira[k]??999,b:new Set()}).b.add(x[1])}
 const once=$("kbahis").value;
 $("kbahis").innerHTML='<option value="">Karışık (en iyileri)</option>'+Object.entries(G).sort((a,b)=>a[1].s-b[1].s).map(([g,v])=>`<optgroup label="${esc(g)}">${[...v.b].sort((a,b)=>a.localeCompare(b,"tr",{numeric:true})).map(b=>`<option value="${esc(b)}">${esc(b)}</option>`).join("")}</optgroup>`).join("");
 if(once)$("kbahis").value=once;
}

// ---- en yakın 4 maçtan hızlı banko ve sürpriz kupon
(()=>{const d=document.createElement("div");d.innerHTML=`<h3 class="gunbaslik">En yakın 4 maçtan hızlı kupon</h3><p class="note" style="margin:0 0 12px;max-width:72ch">Başlamasına en az süre kalan 4 maçla tek tıkla bir banko, bir sürpriz kupon. Yalnızca geçmişte aynı oranla en az 20 maç oynanmış maçlar arasından seçilir.</p><button type="button" class="kbtn" id="k4yap">En yakın 4 maçtan kupon hazırla</button><div id="k4sonuc"></div>`;$("ksonuc").after(d)})();
function yakin4(){
 if(!HV){$("k4sonuc").innerHTML='<div class="empty" style="margin-top:14px">Kupon verisi henüz hazır değil.</div>';return}
 const A=havuz("hepsi",1.01);
 const ids=[...new Map(A.map(c=>[c.mid,c.m.t])).entries()].sort((a,b)=>a[1]-b[1]).slice(0,4).map(x=>x[0]);
 if(!ids.length){$("k4sonuc").innerHTML='<div class="empty" style="margin-top:14px">Şu an başlamamış uygun maç yok. Akşamki güncellemeden sonra tekrar dene.</div>';return}
 const deger=c=>c.tahmin*c.oran,B=[],S=[];
 for(const id of ids){
  const L=A.filter(c=>c.mid===id);
  const b=L.filter(c=>c.oran>=1.2).sort((x,y)=>y.base-x.base||y.p-x.p)[0];
  const L2=L.filter(c=>c.oran>=3&&(!b||c.ad!==b.ad));
  const s=L2.sort((x,y)=>deger(y)-deger(x))[0];
  if(b)B.push(b);if(s)S.push(s);
 }
 $("k4sonuc").innerHTML=`<div class="kgrid">${B.length?havuzKart(`Banko, en yakın ${B.length} maç`,"Her maçın, oranı buna yakın geçmiş maçlarda en sık tutan bahsi. Oran en az 1,20.",B,"",""):""}${S.length?havuzKart(`Sürpriz, en yakın ${S.length} maç`,"Her maçın, gerçekçi ihtimaline göre oranı en cömert görünen yüksek oranlı bahsi. Oran en az 3,00. Tutma ihtimali çok düşük.",S," s",""):""}</div>`;canli($("k4sonuc"));
}
$("k4yap").addEventListener("click",yakin4);

fetch("havuz.json",{cache:"no-store"}).then(r=>r.ok?r.json():null).catch(()=>null).then(j=>{
 HV=j;if(!j){$("knot").textContent="Kupon verisi henüz hazır değil.";$("eilist").innerHTML='<div class="empty">Veri henüz hazır değil.</div>';return}
 const ad=g=>{const iso=g.tarih.split("/").reverse().join("-");return iso===BUGUN?`Bugün (${kisa(iso)})`:iso===YARIN?`Yarın (${kisa(iso)})`:kisa(iso)};
 const opt='<option value="hepsi">Bugün ve yarın</option>'+j.gunler.map((g,i)=>`<option value="${i}">${esc(ad(g))}</option>`).join("");
 $("kgun").innerHTML=opt;$("eigun").innerHTML=opt;bahisDoldur();enIyi();
 const simdi=Date.now()/1000;
 $("knot").textContent=`Şu an ${j.gunler.reduce((a,g)=>a+g.maclar.filter(m=>m.t>simdi).length,0)} maç içinden seçim yapılabilir: geçmişte aynı oranla en az 20 maç oynanmış olanlar. Oranlar ${j.guncelleme} itibarıyla.`;
});
}
