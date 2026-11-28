#!/usr/bin/env bash
# Her 20 dakikada bir: veriyi güncelle, kuponları seç, zamanı gelenleri yayınla, sonuçları ve listeleri güncelle.
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

# Günün 6 kuponu: her biri ilk maçına 1 saatten az kaldığında BİR KEZ yayınlanır (o anki, kapanışa en yakın oranlarla)
# ve bir daha hiç değişmez. Sonra arşivdeki bütün kuponların sonuçları güncellenir.
python3 scripts/yayinla.py "veri/kupon_$BUGUN_ISO.json" site/arsiv
python3 scripts/arsiv.py veri/kapanis_maclar.csv site/arsiv

# Kupon oluşturma havuzu (bugün + yarın)
python3 - "$SIMDI" "veri/havuz_$BUGUN_ISO.json" "veri/havuz_$YARIN_ISO.json" <<'EOF'
import sys, json
gunler = [json.load(open(p, encoding="utf-8")) for p in sys.argv[2:]]
json.dump(dict(guncelleme=sys.argv[1], gunler=gunler), open("site/havuz.json", "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))
print("site/havuz.json:", sum(len(g["maclar"]) for g in gunler), "maç")
EOF
