"""Günlük kupon motoru.
Seçimler: birebir aynı 1-X-2 kapanış oranlı geçmiş maçlar + bültendeki her bahis türü (geçmiş skorlardan hesaplanabilenler).
Kullanım:
  1) uygun maç listesi:  python3 kupon.py <kapanis_maclar.csv> <fikstur.txt> <GG/AA/YYYY> <uygun.json> [simdi 'YYYY-MM-DD HH:MM']
  2) kuponlar:           python3 kupon.py <kapanis_maclar.csv> <fikstur.txt> <GG/AA/YYYY> <kuponlar.json> <simdi> <bulten.json>
"""
import sys, json, io, math, itertools, datetime as dt
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd

DB, FIX, GUN, OUT = sys.argv[1:5]
SIMDI = dt.datetime.strptime(sys.argv[5], "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("Europe/Istanbul")) if len(sys.argv) > 5 else None
IDD = json.load(open(sys.argv[6], encoding="utf-8")) if len(sys.argv) > 6 else None
HAVUZ = sys.argv[7] if len(sys.argv) > 7 else None   # kupon oluşturma için seçenek havuzu
BANKO_MIN, BANKO_MAX = 2.0, 3.5
SURPRIZ_MIN, SURPRIZ_MAX = 200.0, 3000.0
MIN_N = 20          # birebir aynı oranlı en az bu kadar geçmiş maç yoksa o maç kupona alınmaz
SHRINK = 10         # tutma ihtimali tahmininde az örneğe aşırı güvenmemek için
ULKE = {"Argentina": "ARG", "Austria": "AUT", "Brazil": "BRA", "China": "CHN", "Denmark": "DNK", "Finland": "FIN",
        "Ireland": "IRL", "Japan": "JPN", "Mexico": "MEX", "Norway": "NOR", "Poland": "POL", "Romania": "ROU",
        "Russia": "RUS", "Sweden": "SWE", "Switzerland": "SWZ", "USA": "USA"}
LIG = {"E0": "İngiltere Premier Lig", "E1": "İngiltere Championship", "E2": "İngiltere League One", "E3": "İngiltere League Two",
       "EC": "İngiltere National League", "SC0": "İskoçya Premiership", "SC1": "İskoçya Championship", "SC2": "İskoçya League One",
       "SC3": "İskoçya League Two", "D1": "Almanya Bundesliga", "D2": "Almanya 2. Bundesliga", "I1": "İtalya Serie A",
       "I2": "İtalya Serie B", "SP1": "İspanya La Liga", "SP2": "İspanya Segunda", "F1": "Fransa Ligue 1", "F2": "Fransa Ligue 2",
       "N1": "Hollanda Eredivisie", "B1": "Belçika Pro League", "P1": "Portekiz Liga", "T1": "Türkiye Süper Lig",
       "G1": "Yunanistan Super League", "ARG": "Arjantin", "AUT": "Avusturya", "BRA": "Brezilya", "CHN": "Çin", "DNK": "Danimarka",
       "FIN": "Finlandiya", "IRL": "İrlanda", "JPN": "Japonya J1", "MEX": "Meksika", "NOR": "Norveç", "POL": "Polonya",
       "ROU": "Romanya", "RUS": "Rusya", "SWE": "İsveç", "SWZ": "İsviçre", "USA": "ABD MLS"}

# ---- veritabanı
db = pd.read_csv(DB)
O = {"1": db.b365ch.round(2).to_numpy(), "X": db.b365cd.round(2).to_numpy(), "2": db.b365ca.round(2).to_numpy()}
g1, g2 = db.fthg.to_numpy(), db.ftag.to_numpy()
hasHT = db.hthg.notna().to_numpy()
h1, h2 = db.hthg.fillna(0).to_numpy(), db.htag.fillna(0).to_numpy()
s1, s2 = g1 - h1, g2 - h2                      # ikinci yarı golleri
top, ht, st = g1 + g2, h1 + h2, s1 + s2


def sonuc(a, b):
    return np.where(a > b, "1", np.where(a < b, "2", "X"))


ms, iy, y2 = sonuc(g1, g2), sonuc(h1, h2), sonuc(s1, s2)
kg, iykg, y2kg = (g1 > 0) & (g2 > 0), (h1 > 0) & (h2 > 0), (s1 > 0) & (s2 > 0)
X = {"1": "1", "0": "X", "2": "2"}
AU = {"Alt": "alt", "Üst": "üst"}


def au(dizi, cizgi, n):
    return dizi < cizgi if n == "Alt" else dizi > cizgi


def katalog(key, sov, n):
    """Bültendeki bir bahis seçeneğini geçmiş skorlardan hesaplanabilir hale getirir.
    Dönüş: (Türkçe ad, sonuç dizisi, ilk yarı skoru gerekir mi) ya da None."""
    try:
        c = float(sov) if sov not in (None, "") else None
    except ValueError:
        c = None
    ev = {"Evet": True, "Hayır": False}
    if key == "1_1" and n in X: return f"Maç sonucu {X[n]}", ms == X[n], False
    if key == "2_92":
        d = {"1 ve 0": ("1-X", ms != "2"), "1 ve 2": ("1-2", ms != "X"), "0 ve 2": ("X-2", ms != "1")}
        if n in d: return f"Çifte şans {d[n][0]}", d[n][1], False
    if key == "2_101" and c is not None and n in AU: return f"Toplam {sov} gol {AU[n]}", au(top, c, n), False
    if key == "2_89" and n in ("Var", "Yok"): return f"Karşılıklı gol {n.lower()}", kg if n == "Var" else ~kg, False
    if key == "2_60" and c is not None and n in AU: return f"İlk yarı {sov} gol {AU[n]}", au(ht, c, n), True
    if key == "2_90" and n and "/" in n:
        a, b = n.split("/")
        if a in X and b in X: return f"İlk yarı / maç sonu {X[a]}/{X[b]}", (iy == X[a]) & (ms == X[b]), True
    if key == "2_88" and n in X: return f"İlk yarı sonucu {X[n]}", iy == X[n], True
    if key == "2_36" and n in X: return f"2. yarı sonucu {X[n]}", y2 == X[n], True
    if key == "2_720" and n in ("Var", "Yok"): return f"İlk yarı karşılıklı gol {n.lower()}", iykg if n == "Var" else ~iykg, True
    if key == "2_821" and n in ("Var", "Yok"): return f"2. yarı karşılıklı gol {n.lower()}", y2kg if n == "Var" else ~y2kg, True
    if key == "2_866" and n and " / " in n:
        a, b = n.split(" / ")
        if a in ev and b in ev:
            return (f"1. yarı KG {'var' if ev[a] else 'yok'} / 2. yarı KG {'var' if ev[b] else 'yok'}",
                    (iykg == ev[a]) & (y2kg == ev[b]), True)
    if key == "2_730" and n in ev: return f"Her iki yarıda 1.5 üst: {n.lower()}", ((ht >= 2) & (st >= 2)) == ev[n], True
    if key == "2_729" and n in ev: return f"Her iki yarıda 1.5 alt: {n.lower()}", ((ht <= 1) & (st <= 1)) == ev[n], True
    if key in ("2_7", "2_698", "2_699", "2_724", "2_700") and n and " ve " in n:
        a, b = n.split(" ve ")
        if key == "2_7" and a in X and b in AU and c is not None:
            return f"Maç sonucu {X[a]} ve {sov} {AU[b]}", (ms == X[a]) & au(top, c, b), False
        if key == "2_698" and a in X and b in ("Var", "Yok"):
            return f"Maç sonucu {X[a]} ve KG {b.lower()}", (ms == X[a]) & (kg if b == "Var" else ~kg), False
        if key == "2_699" and a in X and b in ("Var", "Yok"):
            return f"İlk yarı {X[a]} ve İY KG {b.lower()}", (iy == X[a]) & (iykg if b == "Var" else ~iykg), True
        if key == "2_724" and a in X and b in AU and c is not None:
            return f"İlk yarı {X[a]} ve İY {sov} {AU[b]}", (iy == X[a]) & au(ht, c, b), True
        if key == "2_700" and a in AU and b in ("Var", "Yok") and c is not None:
            return f"Toplam {sov} {AU[a]} ve KG {b.lower()}", au(top, c, a) & (kg if b == "Var" else ~kg), False
    if key == "2_6":
        d = {"1.": ht > st, "Eşit": ht == st, "2.": st > ht}
        if n in d: return f"En çok gol: {'1. yarı' if n == '1.' else '2. yarı' if n == '2.' else 'eşit'}", d[n], True
    if key in ("2_84", "2_85"):
        a, b = (h1, s1) if key == "2_84" else (h2, s2)
        kim = "Ev sahibi" if key == "2_84" else "Deplasman"
        d = {"1.": a > b, "Eşit": a == b, "2.": b > a}
        if n in d: return f"{kim} en çok golü: {'1. yarı' if n == '1.' else '2. yarı' if n == '2.' else 'eşit'}", d[n], True
    if key == "2_4":
        d = {"0-1 gol": top <= 1, "2-3 gol": (top >= 2) & (top <= 3), "4-5 gol": (top >= 4) & (top <= 5), "6+ gol": top >= 6}
        if n in d: return f"Toplam gol {n}", d[n], False
    if key in ("2_603", "2_604") and c is not None and n in AU:
        return f"{'Ev sahibi' if key == '2_603' else 'Deplasman'} {sov} gol {AU[n]}", au(g1 if key == "2_603" else g2, c, n), False
    if key in ("2_722", "2_723") and c is not None and n in AU:
        return f"{'Ev sahibi' if key == '2_722' else 'Deplasman'} ilk yarı {sov} gol {AU[n]}", au(h1 if key == "2_722" else h2, c, n), True
    if key == "2_91" and n in ("Tek", "Çift"): return f"Toplam gol {n.lower()}", (top % 2 == 1) == (n == "Tek"), False
    if key == "2_719" and n in ("Tek", "Çift"): return f"İlk yarı gol {n.lower()}", (ht % 2 == 1) == (n == "Tek"), True
    if key in ("2_69", "2_72") and n in ev:
        a = (h1 > h2) & (s1 > s2) if key == "2_69" else (h2 > h1) & (s2 > s1)
        return f"{'Ev sahibi' if key == '2_69' else 'Deplasman'} iki yarıyı da kazanır: {n.lower()}", a == ev[n], True
    if key in ("2_727", "2_728") and n in ev:
        a = (h1 > h2) | (s1 > s2) if key == "2_727" else (h2 > h1) | (s2 > s1)
        return f"{'Ev sahibi' if key == '2_727' else 'Deplasman'} en az bir yarıyı kazanır: {n.lower()}", a == ev[n], True
    if key in ("2_861", "2_862") and n in ev:
        a = (h1 > 0) & (s1 > 0) if key == "2_861" else (h2 > 0) & (s2 > 0)
        return f"{'Ev sahibi' if key == '2_861' else 'Deplasman'} iki yarıda da gol atar: {n.lower()}", a == ev[n], True
    if key == "2_11":
        f = g1 - g2
        d = {"Ev 3+": f >= 3, "Ev 2": f == 2, "Ev 1": f == 1, "0": f == 0, "Dep 1": f == -1, "Dep 2": f == -2, "Dep 3+": f <= -3}
        if n in d: return f"Fark: {n if n != '0' else 'beraberlik'}", d[n], False
    if key == "2_100" and c is not None and n in X:
        hs = sonuc(g1 + c, g2)
        return f"Handikaplı maç sonucu (ev sahibi {c:+g}) {X[n]}", hs == X[n], False
    return None


_ON = {}
def katalog_onbellek(key, sov, n):
    k = (key, sov, n)
    if k not in _ON: _ON[k] = katalog(key, sov, n)
    return _ON[k]


def wilson_alt(h, n, z=1.64):
    if n == 0: return 0.0
    p = h / n; d = 1 + z * z / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d


# ---- fikstür
def bolumler(txt):
    out, cur = {}, None
    for line in txt.splitlines():
        if line.startswith("### "): cur = line[4:].strip(); out[cur] = []
        elif cur: out[cur].append(line)
    return {k: pd.read_csv(io.StringIO("\n".join(v)), dtype=str) for k, v in out.items()}
bl = bolumler(open(FIX, encoding="utf-8").read())
fm = bl["/fixtures.csv"]; fm = fm[fm.Date == GUN]
fxx = bl["/new_league_fixtures.csv"]; fxx = fxx[fxx.Date == GUN]
fx = [dict(lig=r["Div"], saat=r["Time"], ev=r["HomeTeam"], dep=r["AwayTeam"], row=r, ht=True) for _, r in fm.iterrows()]
fx += [dict(lig=ULKE.get(r["Country"], r["Country"]), saat=r["Time"], ev=r["Home"], dep=r["Away"], row=r, ht=False) for _, r in fxx.iterrows()]


def fnum(v):
    try:
        v = float(v); return v if v > 1 else None
    except (TypeError, ValueError): return None


def tr_saat(saat):
    d = dt.datetime.strptime(GUN + " " + saat, "%d/%m/%Y %H:%M").replace(tzinfo=ZoneInfo("Europe/London"))
    return d.astimezone(ZoneInfo("Europe/Istanbul"))


def pct(v): return f"%{v*100:.0f}"


adaylar, incelenen, yetersiz, uygun = [], 0, 0, []
IDX = {(x["fd_ev"], x["fd_dep"]): x for x in (IDD or [])}
# Geçmiş maçlar kapanış oranıyla kayıtlı; yaklaşan maçın kapanış oranı henüz yok. Fikstürdeki oran günler önce
# alınmış olabilir. Bültendeki güncel 1-X-2 oranı farklıysa (piyasa en az 2 puan oynamışsa) "yakın oranlı
# maçlar" grubunu onun uluslararası karşılığının çevresinde kurarız: büro payı çıkarılıp uluslararası paya (MARJ) çevrilir.
# Birebir aynı oranlı grup (yalnızca bilgi amaçlı) fikstür oranıyla kalır.
MARJ = 1.074
_say = pd.Series(np.concatenate([O["1"], O["X"], O["2"]])).value_counts()
MERDIVEN = np.array(sorted(v for v, c in _say.items() if v > 1 and c >= 30))
def yuvarla(v): return float(MERDIVEN[np.abs(MERDIVEN - v).argmin()])
def guncel_oran(idd, o):
    x = {n: v for key, sov, n, v, mb in (idd or {}).get("secenekler", []) if key == "1_1"}
    if not all(k in x for k in ("1", "0", "2")): return o, False
    pi = [1 / x["1"], 1 / x["0"], 1 / x["2"]]; si = sum(pi)
    pf = [1 / v for v in o]; sf = sum(pf)
    if max(abs(a / si - b / sf) for a, b in zip(pi, pf)) < 0.02: return o, False
    return tuple(yuvarla(1 / (a / si * MARJ)) for a in pi), True
for f in fx:
    r = f["row"]; o = tuple(fnum(r.get(c)) for c in ("B365H", "B365D", "B365A"))
    if None in o: continue
    bas = tr_saat(f["saat"])
    if SIMDI and bas <= SIMDI: continue
    incelenen += 1
    oy, degisti = guncel_oran(IDX.get((f["ev"], f["dep"])), o)
    msk = (O["1"] == round(o[0], 2)) & (O["X"] == round(o[1], 2)) & (O["2"] == round(o[2], 2))
    n = int(msk.sum())
    if n < MIN_N: yetersiz += 1; continue
    for t in (0.03, 0.05, 0.08, 0.12, 0.20):
        yak = (np.abs(O["1"] / oy[0] - 1) <= t) & (np.abs(O["X"] / oy[1] - 1) <= t) & (np.abs(O["2"] / oy[2] - 1) <= t)
        if yak.sum() >= 150: break
    uygun.append(dict(ev=f["ev"], dep=f["dep"], utc=bas.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M")))
    idd = IDX.get((f["ev"], f["dep"]))
    if IDD is None or not idd: continue
    skorlar = pd.Series([f"{int(a)}-{int(b)}" for a, b in zip(g1[msk], g2[msk])]).value_counts().head(3)
    mac = dict(idd_id=idd.get("id"), mbc=idd.get("mbc", 1), idd_ad=f"{idd['idd_ev']} – {idd['idd_dep']}", mac=f"{f['ev']} – {f['dep']}",
               lig=LIG.get(f["lig"], f["lig"]), saat=bas.strftime("%d.%m %H:%M"), oran=o, n=n, t=int(bas.timestamp()), oran_guncel=[round(v, 2) for v in oy] if degisti else None, oran_ara=oy,
               fd_ev=f["ev"], fd_dep=f["dep"],
               skorlar=", ".join(f"{s} ({c} kez)" for s, c in skorlar.items()))
    for key, sov, ad_n, oran, mbc in idd.get("secenekler", []):
        k = katalog_onbellek(key, sov, ad_n)
        if not k: continue
        ad, dizi, ht_gerek = k
        if ht_gerek and not f["ht"]: continue   # bu ligde ilk yarı skoru tutulmuyor, sonucu kontrol edilemez
        mm = msk & hasHT if ht_gerek else msk
        nn = int(mm.sum())
        if nn < MIN_N: continue
        hits = int(dizi[mm].sum()); p = hits / nn
        ym = yak & hasHT if ht_gerek else yak
        if ym.sum() < 50: continue
        base = float(dizi[ym].mean())
        tahmin = base   # testte gerçek tutma oranı birebir aynı oranlı % değil, yakın oranlı % ile örtüştü
        adaylar.append(dict(mac=mac, ad=ad, tur=key, n=nn, hits=hits, p=p, wl=wilson_alt(hits, nn), base=base, yak_n=int(ym.sum()),
                            tol=t, tahmin=tahmin, oran=float(oran), deger=tahmin * float(oran), mbc=max(mac["mbc"], mbc or 1),
                            sov=sov, sec=ad_n))
if IDD is None:
    json.dump(uygun, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"uygun maç: {len(uygun)} -> {OUT}"); sys.exit(0)


if HAVUZ:
    ML, MI, SEC = [], {}, []
    for c in adaylar:
        if c["hits"] < 3 or not 1.05 <= c["oran"] <= 40: continue
        mc = c["mac"]
        if mc["mac"] not in MI:
            MI[mc["mac"]] = len(ML)
            ML.append(dict(ad=mc["idd_ad"], id=mc["idd_id"], lig=mc["lig"], saat=mc["saat"], t=mc["t"], n=mc["n"], oran=[round(v, 2) for v in mc["oran"]],
                           skorlar=mc["skorlar"]))
        SEC.append([MI[mc["mac"]], c["ad"], round(c["oran"], 2), int(c["mbc"]), c["hits"], c["n"], round(c["base"], 3), round(c["tahmin"], 3), c["tur"], c["sov"], c["sec"]])
    json.dump(dict(tarih=GUN, maclar=ML, secenekler=SEC), open(HAVUZ, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"havuz: {len(ML)} maç, {len(SEC)} seçenek -> {HAVUZ}")


def aciklama(c):
    mc = c["mac"]
    t = (f"Bu maçın uluslararası 1-X-2 oranları {mc['oran'][0]:.2f} – {mc['oran'][1]:.2f} – {mc['oran'][2]:.2f}. Geçmişte birebir aynı oranlarla "
         f"oynanmış {mc['n']} maç var. ")
    t += f"Bunların ilk yarı skoru bilinen {c['n']} tanesinin " if c["n"] != mc["n"] else "Bunların "
    t += (f"{c['hits']} tanesinde ({pct(c['p'])}) \"{c['ad']}\" oldu. Oranı buna yakın (her biri ±%{c['tol']*100:.0f}) {c['yak_n']} maçta "
          f"bu sonuç {pct(c['base'])} çıkmış")
    t += (". Gerçekçi ihtimal olarak yakın oranlı maçlardaki yüzdeyi kullanıyoruz: 2,5 yıllık testte gerçek sonuçlar ona uydu, "
          "birebir aynı oranlı az sayıda maçtan çıkan yüzde ise çoğunlukla şanstan dolayı fazla görünüyordu.")
    t += f" Bültendeki oranı {c['oran']:.2f}; bu oran bu sonuca yaklaşık {pct(1 / c['oran'])} ihtimal veriyor."
    t += f" Bu oranlı maçlarda en sık skorlar: {mc['skorlar']}."
    if c["n"] < 40: t += f" Not: örnek sayısı ({c['n']}) az, sonuç şanstan etkilenmiş olabilir."
    return t


def kur(havuz, anahtar, kullanildi, hedef=None, tavan=None, adet=None, en_cok=8, ayni_tur=2):
    """Farklı maçlardan seçim yapar. hedef: toplam oran bu değere ulaşınca dur; adet: bu kadar seçimde dur."""
    out, toplam = [], 1.0
    for c in sorted(havuz, key=anahtar, reverse=True):
        if c["mac"]["mac"] in kullanildi or any(x["mac"]["mac"] == c["mac"]["mac"] for x in out): continue
        if tavan and toplam * c["oran"] > tavan: continue
        if sum(x["tur"] == c["tur"] for x in out) >= ayni_tur: continue
        out.append(c); toplam *= c["oran"]
        if hedef and toplam >= hedef and len(out) >= max(x["mbc"] for x in out): break
        if adet and len(out) == adet: break
        if len(out) >= en_cok: break
    for c in out: kullanildi.add(c["mac"]["mac"])
    return out


def satir(c):
    return dict(mac=c["mac"]["mac"], idd_ad=c["mac"]["idd_ad"], mbs=c["mbc"], lig=c["mac"]["lig"], saat=c["mac"]["saat"], secim=c["ad"],
                oran=round(c["oran"], 2), gecmis=round(c["p"], 3), ortalama=round(c["base"], 3), yakin_n=c["yak_n"],
                olasilik=round(c["tahmin"], 3), n=c["n"], hits=c["hits"], aciklama=aciklama(c),
                key=c["tur"], sov=c["sov"], sec=c["sec"], fd_ev=c["mac"]["fd_ev"], fd_dep=c["mac"]["fd_dep"], gun=GUN, t=c["mac"]["t"], idd_id=c["mac"]["idd_id"])


# ---- bu oranlarla oynanmış son 5 maç: oranı en yakın olanlardan, en yenisinden başlayarak
_LO = {k: np.log(np.where(O[k] > 1, O[k], np.nan)) for k in ("1", "X", "2")}
_TARIH = db.date.astype(str).to_numpy()
_SIRA = np.argsort(_TARIH)[::-1]                     # en yeni maç önce


def son_maclar(c, adet=5):
    oy = c["mac"]["oran_ara"]
    d = (np.abs(_LO["1"] - math.log(oy[0])) + np.abs(_LO["X"] - math.log(oy[1])) + np.abs(_LO["2"] - math.log(oy[2])))
    k = katalog_onbellek(c["tur"], c["sov"], c["sec"])
    gerek_ht = bool(k and k[2])
    d = np.where(np.isnan(d) | (gerek_ht & ~hasHT), np.inf, np.round(d, 3))
    aday = np.argpartition(d, 200)[:200]                                  # en yakın 200 maç
    aday = sorted(aday, key=lambda i: (d[i], -int(_TARIH[i].replace("-", ""))))[:adet]
    out = []
    for i in aday:
        if not np.isfinite(d[i]): continue
        out.append(dict(tarih=_TARIH[i], mac=f"{db.home[i]} – {db.away[i]}",
                        oran=[round(float(O["1"][i]), 2), round(float(O["X"][i]), 2), round(float(O["2"][i]), 2)],
                        iy=f"{int(h1[i])}-{int(h2[i])}" if hasHT[i] else None, ms=f"{int(g1[i])}-{int(g2[i])}",
                        tuttu=bool(k[1][i]) if k else None))
    return sorted(out, key=lambda x: x["tarih"], reverse=True)


def kupon_ozet(s):
    return dict(toplam_oran=round(float(np.prod([c["oran"] for c in s])), 2) if s else None,
                tutma_olasiligi=round(float(np.prod([c["tahmin"] for c in s])), 5) if s else 0)


def satir2(c):
    s = satir(c)
    s.update(son5=son_maclar(c), oran_1x2=[round(v, 2) for v in c["mac"]["oran_ara"]])
    return s


# ---- günün 6 kuponu. Her kupon, ilk maçına yaklaşık 1 saat kala (o anki, kapanışa en yakın oranlarla)
# yayinla.py tarafından BİR KEZ kaydedilir. Seçim: oranı bu maça en yakın geçmiş maçlarda o bahsin tutma sıklığı
# (gerçekçi ihtimal) en yüksek olanlar. En az oran şartını sağlayan yeterli maç yoksa ihtimali en yüksek diğerleri eklenir.
def fl(v):
    try: return float(v)
    except (TypeError, ValueError): return None


ESIK = (SIMDI.timestamp() + 30 * 60) if SIMDI else 0          # 30 dakikadan az kalan maç kupona girmez
TANIM = [
    dict(kod="iki_yari_15", ad="İki yarıda da 1.5 üst · Sistem 2-3", tur="sistem", sistem_min=2, adet=3, min_oran=2.0,
         uy=lambda c: c["tur"] == "2_730" and c["sec"] == "Evet",
         not_="Hem ilk yarıda hem ikinci yarıda 2 ve üzeri gol. 3 maçın 2'li ve 3'lü kombinasyonları (4 kolon); 2 maç tutsa bir kolon kazanır. Maç başına oran en az 2,00."),
    dict(kod="ust25", ad="2.5 üst", tur="normal", adet=3, min_oran=1.30,
         uy=lambda c: c["tur"] == "2_101" and fl(c["sov"]) == 2.5 and c["sec"] == "Üst",
         not_="Maçta 3 ve üzeri gol. 3 maçın hepsinin tutması gerekir. Maç başına oran en az 1,30."),
    dict(kod="kg_kg", ad="İY KG var + 2Y KG var · Sistem 2-3", tur="sistem", sistem_min=2, adet=3, min_oran=0,
         uy=lambda c: c["tur"] == "2_866" and c["sec"] == "Evet / Evet",
         not_="İki takım hem ilk yarıda hem ikinci yarıda gol atar. 3 maçın 2'li ve 3'lü kombinasyonları (4 kolon); 2 maç tutsa bir kolon kazanır."),
    dict(kod="iyms", ad="İY/MS · Sistem 2-3", tur="sistem", sistem_min=2, adet=3, min_oran=2.0,
         uy=lambda c: c["tur"] == "2_90",
         not_="İlk yarı / maç sonu. 3 maçın 2'li ve 3'lü kombinasyonları (4 kolon); 2 maç tutsa bir kolon kazanır. Maç başına oran en az 2,00."),
    dict(kod="ms", ad="Maç sonucu", tur="normal", adet=3, min_oran=3.0,
         uy=lambda c: c["tur"] == "1_1",
         not_="Maç sonucu 1, X ya da 2. 3 maçın hepsinin tutması gerekir. Maç başına oran en az 3,00."),
    dict(kod="ust55", ad="5.5 üst · Sistem 3-4-5", tur="sistem", sistem_min=3, adet=5, min_oran=0,
         uy=lambda c: c["tur"] == "2_101" and fl(c["sov"]) == 5.5 and c["sec"] == "Üst",
         not_="Maçta 6 ve üzeri gol: sürpriz kupon. 5 maçın 3'lü, 4'lü ve 5'li kombinasyonları (16 kolon); 3 maç tutsa bir kolon kazanır."),
]


def sec_kupon(t):
    L = sorted([c for c in adaylar if t["uy"](c) and c["mac"]["t"] >= ESIK], key=lambda c: (c["base"], c["p"]), reverse=True)
    out, kul = [], set()
    for kosul in (lambda c: c["oran"] >= t["min_oran"], lambda c: True):   # önce oran şartı, yetmezse en olası diğerleri
        for c in L:
            if len(out) == t["adet"]: break
            if c["mac"]["mac"] in kul or not kosul(c): continue
            out.append(c); kul.add(c["mac"]["mac"])
    return out


def sistem_ozet2(s, kmin):
    ps = [c["tahmin"] for c in s]; od = [c["oran"] for c in s]; nn = len(s)
    kombo = [cmb for k in range(kmin, nn + 1) for cmb in itertools.combinations(range(nn), k)]
    dag = [1.0] + [0.0] * nn
    for p in ps: dag = [dag[i] * (1 - p) + (dag[i - 1] * p if i else 0) for i in range(nn + 1)]
    tablo = []
    for t in range(nn + 1):
        kaz = [sum(float(np.prod([od[i] for i in cmb])) for cmb in kombo if set(cmb) <= set(tt))
               for tt in itertools.combinations(range(nn), t)]
        tablo.append(dict(tutan=t, olasilik=round(dag[t], 4), en_az=round(min(kaz), 2), en_cok=round(max(kaz), 2)))
    return dict(kolon=len(kombo), tablo=tablo, sistem_min=kmin)


kuponlar = []
for t in TANIM:
    S = sec_kupon(t)
    k = dict(kod=t["kod"], ad=t["ad"], tur=t["tur"], not_=t["not_"], secimler=[satir2(c) for c in S],
             ilk_mac=min((c["mac"]["t"] for c in S), default=None))
    k.update(sistem_ozet2(S, t["sistem_min"]) if t["tur"] == "sistem" else kupon_ozet(S))
    if len(S) < t["adet"]:
        k["eksik"] = f"Bugün bu bahiste {len(S)} uygun maç vardı."
    kuponlar.append(k)

sonuc_json = dict(tarih=GUN, hazirlandi=dt.datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%d.%m.%Y %H:%M"),
                  mac_sayisi=incelenen, uygun_mac=incelenen - yetersiz, eslesen=len(IDD), min_n=MIN_N, kuponlar=kuponlar)
json.dump(sonuc_json, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(dict(incelenen=incelenen, uygun=incelenen - yetersiz, aday=len(adaylar)), ensure_ascii=False))
for k in kuponlar:
    print("\n==", k["ad"], {a: k[a] for a in ("toplam_oran", "tutma_olasiligi", "kolon") if a in k}, k.get("eksik", ""))
    for s in k["secimler"]:
        print(f"  {s['saat']} {s['mac']} -> {s['secim']} oran={s['oran']} gerçekçi={s['ortalama']} son5={[x['tuttu'] for x in s['son5']]}")
