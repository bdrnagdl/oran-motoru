#!/usr/bin/env bash
# Her gün: veriyi güncelle, bugünün ve yarının kuponlarını hazırla, arşivi ve sonuçları güncelle.
set -euo pipefail
export TZ=Europe/Istanbul
SIMDI=$(date +"%Y-%m-%d %H:%M")
BUGUN_ISO=$(date +%Y-%m-%d)
YARIN_ISO=$(date -d tomorrow +%Y-%m-%d)
echo "Bugün: $BUGUN_ISO  Yarın: $YARIN_ISO  Şimdi: $SIMDI"
python3 scripts/veri_guncelle.py

for ISO in "$BUGUN_ISO" "$YARIN_ISO"; do
  GUN=$(date -d "$ISO" +%d/%m/%Y)
  echo "== $GUN"
  python3 scripts/kupon.py veri/kapanis_maclar.csv veri/fikstur.txt "$GUN" "veri/uygun_$ISO.json" "$SIMDI"
  python3 scripts/bulten_cek.py "veri/uygun_$ISO.json" "veri/bulten_$ISO.json"
  python3 scripts/kupon.py veri/kapanis_maclar.csv veri/fikstur.txt "$GUN" "veri/kupon_$ISO.json" "$SIMDI" \
    "veri/bulten_$ISO.json" "veri/havuz_$ISO.json"
done

# Günün kuponları, günün ilk uygun maçına 95 dakikadan az kaldığında (yaklaşık 1 saat önce) BİR KEZ kaydedilir
# ve bir daha hiç değişmez. Saatlik çalışmalar yalnızca listeleri, "kupon oluştur" havuzunu ve sonuçları günceller.
YAYIN=$(python3 - "veri/uygun_$BUGUN_ISO.json" <<'PYEOF'
import sys, json, datetime as dt
simdi = dt.datetime.now(dt.timezone.utc)
t = [dt.datetime.fromisoformat(x["utc"]).replace(tzinfo=dt.timezone.utc) for x in json.load(open(sys.argv[1], encoding="utf-8"))]
t = [x for x in t if x > simdi]
print(1 if t and (min(t) - simdi).total_seconds() <= 95 * 60 else 0)
PYEOF
)
echo "Bugünün kuponunu yayınlama zamanı mı: $YAYIN"
if [ "$YAYIN" = "1" ]; then
  python3 scripts/arsiv.py veri/kapanis_maclar.csv site/arsiv "veri/kupon_$BUGUN_ISO.json" 0
else
  python3 scripts/arsiv.py veri/kapanis_maclar.csv site/arsiv
fi

# Kupon oluşturma havuzu (bugün + yarın)
python3 - "$SIMDI" "veri/havuz_$BUGUN_ISO.json" "veri/havuz_$YARIN_ISO.json" <<'EOF'
import sys, json
gunler = [json.load(open(p, encoding="utf-8")) for p in sys.argv[2:]]
json.dump(dict(guncelleme=sys.argv[1], gunler=gunler), open("site/havuz.json", "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))
print("site/havuz.json:", sum(len(g["maclar"]) for g in gunler), "maç")
EOF
