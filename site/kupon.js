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

// ---- tek seçim satırı (kartların içinde)
const secim=(s,ek)=>`<div class="sec${s.durum==="tuttu"?" ok":s.durum==="yatti"?" no":""}">
 <div class="r"><span class="m">${esc(s.mac)}</span><span class="o">${s.oran?o2(s.oran):"–"}</span></div>
 <div class="i"><span>${esc(s.saat)}</span><span>${esc(s.lig)}</span>${s.mbs?`<span>MBS ${esc(s.mbs)}</span>`:""}</div>
 <span class="pk">${esc(s.secim)}</span>${rozet(s.durum)}${s.skor?`<div class="i">${esc(s.skor)}</div>`:""}${ek||""}
</div>`;

// ---- sitenin kupon kartı (günün kuponları ve geçmiş)
function kart(k,tam){
 const S=k.secimler.map(s=>({...s,mac:s.idd_ad||s.mac}));
 const sec=S.map(s=>secim(s,tam&&s.n?`<div class="i">Aynı oranlı ${s.n} maçın ${s.hits} tanesinde oldu (${yuz(s.gecmis)}), yakın oranlarda ${yuz(s.ortalama)}</div><details><summary>Neden bu seçim?</summary><p>${esc(s.aciklama)}</p></details>`:"")).join("");
 let alt="";
 if(k.tur==="sistem"){
  let sonuc="";
  if(k.tutan!=null&&k.durum!=="bekliyor")sonuc=`<p class="knote"><b>${k.tutan}/${S.length} seçim tuttu.</b>${k.donus!=null?` Geri dönüş ${say(k.donus)} birim (${k.kolon} birim yatırılmıştı).`:""}</p>`;
  const rows=tam&&k.tablo?k.tablo.filter(t=>t.tutan>=1).map(t=>`<tr><td>${t.tutan} maç tutarsa</td><td class="n">${yuz(t.olasilik)}</td><td class="n">${t.en_cok===null?"–":t.en_cok?(t.en_az===t.en_cok?say(t.en_az):say(t.en_az)+" – "+say(t.en_cok)):"0"}</td></tr>`).join(""):"";
  alt=`<div class="tot"><div><b>${k.kolon??"–"}</b><span>kolon, her kolona 1 birim</span></div><div><b>${S.length}</b><span>maç</span></div></div>${sonuc}${rows?`<div class="scroll knote"><table class="st"><thead><tr><th>Durum</th><th class="n">İhtimal</th><th class="n">Geri dönüş (birim)</th></tr></thead><tbody>${rows}</tbody></table></div>`:""}`;
 }else{
  alt=`<div class="tot"><div><b>${k.toplam_oran?say(k.toplam_oran):"–"}</b><span>toplam oran</span></div>${tam?`<div><b>${yuz(k.tutma_olasiligi||0)}</b><span>tahmini tutma ihtimali</span></div>`:""}</div>`;
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
  $("kgrid").innerHTML=j.kuponlar.map(k=>kart(k,true)).join("");
 }).catch(()=>{$("kmeta").textContent="Bu günün kuponları henüz hazır değil."});
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
 $("kgecmis").innerHTML=h;
}
$("kgecmis").addEventListener("click",e=>{const b=e.target.closest("[data-f]");if(!b)return;FILTRE=b.dataset.f;gecmisGoster()});
function sekmeler(){
 const T=[];
 if(IDX.some(g=>g.tarih===BUGUN))T.push([BUGUN,`Bugün, ${kisa(BUGUN)}`]);
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
 const top=K.reduce((a,c)=>a*c.oran,1),ih=K.reduce((a,c)=>a*c.tahmin,1),mbs=Math.max(...K.map(c=>c.mbc));
 const sec=K.map(c=>secim({mac:c.m.ad,oran:c.oran,saat:c.m.saat,lig:c.m.lig,mbs:c.mbc,secim:c.ad},
  `<div class="i">Yakın oranlı maçlarda ${yuz(c.base)} tuttu; aynı oranlı ${c.n} maçın ${c.hits} tanesinde oldu (${yuz(c.hits/c.n)}).</div><details><summary>Neden bu seçim?</summary><p>Bu maçın uluslararası 1-X-2 oranları ${c.m.oran.map(o2).join(" – ")}. Oranı buna yakın çok sayıda geçmiş maçta "${esc(c.ad)}" ${yuz(c.base)} oranında oldu; birebir aynı oranlı ${c.n} maçta ${c.hits} kez. İkisi harmanlanınca tahmini ihtimal ${yuz(c.tahmin)}. Bültendeki ${o2(c.oran)} oranı ise yaklaşık ${yuz(1/c.oran)} ihtimal veriyor. Bu oranlı maçlarda en sık skorlar: ${esc(c.m.skorlar)}.</p></details>`)).join("");
 return `<article class="kart${cls}"><header><h3>${esc(baslik)}</h3><p>${esc(alt)}</p></header>${sec}<div class="tot"><div><b>${say(top)}</b><span>toplam oran</span></div><div><b>${yuz(ih)}</b><span>tahmini tutma ihtimali</span></div></div>${ekNot||""}${K.length<mbs?`<p class="knote warn">Dikkat: bir maçın MBS'si ${mbs}; bültende oynamak için kuponda en az ${mbs} maç olmalı.</p>`:""}<p class="knote">Oranlar ${esc(HV.guncelleme)} itibarıyla bültenden alındı; oynamadan önce güncel oranı kontrol et. Bu bir tahmindir, kesinlik vermez.</p><div class="kalt">${kopyaDugme(baslik,K.map(c=>`${c.m.ad}: ${c.ad} (${o2(c.oran)})`))}</div></article>`;
}
function havuz(gs,min){
 const A=[],simdi=Date.now()/1000+300;
 HV.gunler.forEach((g,gi)=>{if(gs!=="hepsi"&&+gs!==gi)return;
  for(const s of g.secenekler){const m=g.maclar[s[0]];if(m.t<=simdi||s[2]<min)continue;
   A.push({m,mid:gi+"|"+s[0],ad:s[1],oran:s[2],mbc:s[3],hits:s[4],n:s[5],base:s[6],tahmin:s[7],key:s[8],p:s[4]/s[5]})}});
 return A;
}

// ---- en başarılı bahisler: her maç için yakın oranlı maçlarda en sık tutan bahis
function enIyi(){
 if(!HV)return;
 const A=havuz($("eigun").value,num($("eimin").value)||1),best={};
 for(const c of A){const b=best[c.mid];if(!b||c.base>b.base||(c.base===b.base&&c.p>b.p))best[c.mid]=c}
 const R=Object.values(best).sort((a,b)=>b.base-a.base||b.p-a.p);
 if(!R.length){$("eilist").innerHTML='<div class="empty">Bu ayarlarla maç yok. En az oranı düşür ya da günü değiştir.</div>';return}
 $("eilist").innerHTML=`<p class="note" style="margin:0 0 8px">${R.length} maç, en sık tutandan aşağı doğru.</p><div class="scroll"><table class="tablo eit"><thead><tr><th>Saat</th><th>Maç</th><th>En sık tutan bahis</th><th class="n">Tutma ihtimali</th><th class="n gizle">Aynı oranlı maçlarda</th><th class="n">Oran</th></tr></thead><tbody>${R.map(c=>`<tr>
 <td class="saat">${esc(c.m.saat)}</td>
 <td><b>${esc(c.m.ad)}</b><small>${esc(c.m.lig)}</small></td>
 <td><span class="tag">${esc(c.ad)}</span></td>
 <td class="n"><div class="cub"><span style="width:${(c.base*100).toFixed(0)}%"></span></div><b class="yuzde">${yuz(c.base)}</b></td>
 <td class="n gizle">${yuz(c.p)} <small class="ic">${c.hits}/${c.n}</small></td>
 <td class="n"><b class="oranb">${o2(c.oran)}</b>${c.mbc>1?`<small>MBS ${c.mbc}</small>`:""}</td></tr>`).join("")}</tbody></table></div>`+
  `<h3 class="gunbaslik">En sık tutan ${Math.min(5,R.length)} bahisle kupon</h3><div class="tekkart">${havuzKart(`${Math.min(5,R.length)} maçlık kupon`,"Yukarıdaki listenin ilk bahisleri. Hepsinin birden tutması gerekir.",R.slice(0,5),"","")}</div>`;
}
for(const k of ["eigun","eimin"])$(k).addEventListener("input",enIyi);

// ---- kupon oluştur
const VARS={guvenli:{adet:3,min:"1,20"},surpriz:{adet:5,min:"3,00"}};
$("kadet").innerHTML=[...Array(10)].map((_,i)=>`<option${i+1===3?" selected":""}>${i+1}</option>`).join("");
$("kturu").addEventListener("click",e=>{const b=e.target.closest("[data-tur]");if(!b)return;TUR=b.dataset.tur;
 for(const x of $("kturu").children){x.classList.toggle("on",x===b);x.setAttribute("aria-pressed",x===b)}
 $("kadet").value=VARS[TUR].adet;$("kmin").value=VARS[TUR].min;$("ksonuc").innerHTML=""});
function olustur(karistir){
 if(!HV){$("ksonuc").innerHTML='<div class="empty">Kupon verisi henüz hazır değil.</div>';return}
 const n=+$("kadet").value,min=num($("kmin").value),A=havuz($("kgun").value,min);
 const puan=c=>(TUR==="guvenli"?c.tahmin:c.tahmin*c.oran)*(karistir?0.8+Math.random()*0.4:1);
 const sec=liste=>{const out=[],kul=new Set(),tur={};
  for(const c of liste.map(c=>[puan(c),c]).sort((a,b)=>b[0]-a[0]).map(x=>x[1])){
   if(kul.has(c.mid)||(tur[c.key]||0)>=2)continue;out.push(c);kul.add(c.mid);tur[c.key]=(tur[c.key]||0)+1;if(out.length===n)break}
  return out};
 let K=TUR==="surpriz"?sec(A.filter(c=>c.hits>=4&&c.tahmin>c.base)):sec(A);
 if(K.length<n)K=sec(A);
 if(!K.length){$("ksonuc").innerHTML=`<div class="empty">Bu ayarlarla uygun seçim bulunamadı. En az oranı düşür ya da "Bugün ve yarın"ı seç.</div>`;return}
 const macSay=new Set(A.map(c=>c.mid)).size;
 $("ksonuc").innerHTML=`<div class="tekkart">${havuzKart(`${TUR==="surpriz"?"Sürpriz":"Güvenli"} kupon, ${K.length} maç`,`${macSay} uygun maç arasından, her seçimin oranı en az ${o2(min)}.`,K,TUR==="surpriz"?" s":"",
  K.length<n?`<p class="knote warn">İstediğin ${n} maç için yeterli seçim yok; ${K.length} maçlık kupon hazırlandı. En az oranı düşürmeyi dene.</p>`:"")}<button type="button" class="ikincil" id="kbaska">Başka bir kupon öner</button></div>`;
 $("kbaska").addEventListener("click",()=>olustur(true));
}
$("kyap").addEventListener("click",()=>olustur(false));

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
  const s=L2.filter(c=>c.hits>=4&&c.tahmin>c.base).sort((x,y)=>deger(y)-deger(x))[0]||L2.sort((x,y)=>deger(y)-deger(x))[0];
  if(b)B.push(b);if(s)S.push(s);
 }
 $("k4sonuc").innerHTML=`<div class="kgrid">${B.length?havuzKart(`Banko, en yakın ${B.length} maç`,"Her maçın, oranı buna yakın geçmiş maçlarda en sık tutan bahsi. Oran en az 1,20.",B,"",""):""}${S.length?havuzKart(`Sürpriz, en yakın ${S.length} maç`,"Her maçın, geçmişte beklenenden sık görülmüş yüksek oranlı bahsi. Oran en az 3,00.",S," s",""):""}</div>`;
}
$("k4yap").addEventListener("click",yakin4);

fetch("havuz.json",{cache:"no-store"}).then(r=>r.ok?r.json():null).catch(()=>null).then(j=>{
 HV=j;if(!j){$("knot").textContent="Kupon verisi henüz hazır değil.";$("eilist").innerHTML='<div class="empty">Veri henüz hazır değil.</div>';return}
 const ad=g=>{const iso=g.tarih.split("/").reverse().join("-");return iso===BUGUN?`Bugün (${kisa(iso)})`:iso===YARIN?`Yarın (${kisa(iso)})`:kisa(iso)};
 const opt='<option value="hepsi">Bugün ve yarın</option>'+j.gunler.map((g,i)=>`<option value="${i}">${esc(ad(g))}</option>`).join("");
 $("kgun").innerHTML=opt;$("eigun").innerHTML=opt;enIyi();
 const simdi=Date.now()/1000;
 $("knot").textContent=`Şu an ${j.gunler.reduce((a,g)=>a+g.maclar.filter(m=>m.t>simdi).length,0)} maç içinden seçim yapılabilir: geçmişte aynı oranla en az 20 maç oynanmış olanlar. Oranlar ${j.guncelleme} itibarıyla.`;
});
}
