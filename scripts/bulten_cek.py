"""Uygun maçların yasal bahis bültenindeki oranlarını çeker.
Kullanım: python3 scripts/bulten_cek.py veri/uygun.json veri/bulten.json
"""
import sys, json, time, re, unicodedata, datetime as dt, urllib.request

B = "https://sportsbookv2.iddaa.com/sportsbook/"
UA = {"User-Agent": "Mozilla/5.0 (oran-motoru)", "Accept": "application/json"}
ALIAS = {"man united": "manchester united", "man city": "manchester city", "ath bilbao": "athletic bilbao",
         "ath madrid": "atletico madrid", "ein frankfurt": "eintracht frankfurt", "sheffield weds": "sheffield wednesday",
         "peterboro": "peterborough", "bristol rvs": "bristol rovers", "milton keynes dons": "mk dons", "psv eindhoven": "psv",
         "paris sg": "paris saint germain", "sociedad b": "real sociedad b", "holstein kiel": "kiel", "inter": "inter milan",
         "vallecano": "rayo vallecano", "dundee united": "dundee utd", "fc koln": "koln", "qpr": "queens park rangers",
         "nott m forest": "nottingham forest", "wolves": "wolverhampton", "m gladbach": "monchengladbach",
         "sp lisbon": "sporting", "sp braga": "braga", "sociedad": "real sociedad", "for sittard": "fortuna sittard",
         "st gilloise": "union saint gilloise", "celta": "celta vigo"}
STOP = r"\b(fc|cf|sc|sk|ac|afc|as|ss|us|cd|ud|sd|rc|fk|if|bk|club|de|the|calcio)\b"


def al(url, deneme=3):
    for i in range(deneme):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"  {url}: {e}", flush=True)
            time.sleep(3 * (i + 1))
    return None


def norm(s):
    s = unicodedata.normalize("NFD", s.lower().replace("ı", "i"))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(STOP, " ", s)
    return re.sub(r"\s+", " ", s).strip()


def benzer(a, b):
    a = ALIAS.get(norm(a), norm(a)); b = norm(b)
    if a == b: return 1.0
    if a and b and (a in b or b in a): return 0.9
    A = {w for w in a.split() if len(w) > 2}; Bs = {w for w in b.split() if len(w) > 2}
    if not A: return 0.0
    c = sum(1 for w in A if w in Bs or any(x.startswith(w[:5]) or w.startswith(x[:5]) for x in Bs))
    return c / max(len(A), len(Bs))


def oranlar(d):
    """Maçtaki bütün bahis seçeneklerini ham haliyle döndürür: [anahtar, çizgi, seçenek adı, oran, MBS]."""
    out = []
    for m in d.get("m", []):
        key, sov, mb = f"{m.get('t')}_{m.get('st')}", m.get("sov"), m.get("mbc", 1)
        for x in m.get("o", []):
            v = x.get("odd")
            if v and v > 1:
                out.append([key, sov, x.get("n"), v, mb])
    return out


def main(giris, cikis):
    uygun = json.load(open(giris, encoding="utf-8"))
    ev = (al(B + "events?st=1&type=0&version=0") or {}).get("data", {}).get("events", [])
    ev = [e for e in ev if e.get("sid") == 1]
    print(f"bültende futbol maçı: {len(ev)}")
    out, yok = [], []
    for u in uygun:
        t = dt.datetime.fromisoformat(u["utc"]).replace(tzinfo=dt.timezone.utc).timestamp()
        best, bs = None, 0
        for e in ev:
            if abs(e["d"] - t) > 5400: continue
            sc = benzer(u["ev"], e["hn"]) + benzer(u["dep"], e["an"])
            if sc > bs: best, bs = e, sc
        if not best or bs < 1.1:
            yok.append(f"{u['ev']} - {u['dep']}"); continue
        d = (al(B + f"event/{best['i']}") or {}).get("data")
        if not d: yok.append(f"{u['ev']} - {u['dep']}"); continue
        o = oranlar(d)
        out.append(dict(fd_ev=u["ev"], fd_dep=u["dep"], idd_ev=best["hn"], idd_dep=best["an"], mbc=best.get("mbc", 1),
                        secenekler=o, benzerlik=round(bs, 2)))
        print(f"  {u['ev']} - {u['dep']}  =>  {best['hn']} - {best['an']} ({bs:.2f}), {len(o)} oran", flush=True)
        time.sleep(0.4)
    json.dump(out, open(cikis, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"bulunan: {len(out)} | bulunamayan: {yok}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
