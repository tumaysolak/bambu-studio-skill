# Bambu Studio Uzman Rehberi (Mac + Bambu Lab A1 mini)

Bu rehber, Bambu Studio'yu bir Mac üzerinde uçtan uca otomatik kullanmak için yazıldı: beğenilen bir modeli değiştirmek, sıfırdan parametrik tasarım yapmak, A1 mini için dilimlemek ve baskıya hazırlamak. Her komut bu Mac'te gerçekten çalıştırılıp doğrulandı (20 Kasım 2026).

## 1. Ortam (doğrulanmış)

| Bileşen | Değer |
|---|---|
| Bambu Studio | 02.09.01.70, `/Applications/BambuStudio.app` |
| CLI ikilisi | `/Applications/BambuStudio.app/Contents/MacOS/BambuStudio` |
| Veri klasörü | `~/Library/Application Support/BambuStudio` |
| Sistem profilleri | `.../system/BBL/{machine,process,filament}/*.json` |
| Kullanıcı profilleri | `.../user/<kullanıcı-id>/{machine,process,filament}` |
| Yazıcı | Bambu Lab A1 mini, 0.4 mm nozul, AMS lite (4 yuva), Dokulu PEI tabla |
| Arayüz dili | Türkçe |
| Kod-CAD | OpenSCAD 2026.10 snapshot (`brew install --cask openscad@snapshot`, manifold motoru), build123d 0.13 |
| Mesh araçları | trimesh + manifold3d (`~/bambu-studio-skill/.venv`) |

Not: Homebrew'daki normal `openscad` cask'ı Gatekeeper nedeniyle kapatıldı; `openscad@snapshot` çalışıyor.

## 2. A1 mini fiziksel sınırları

- Baskı hacmi: 180 x 180 x 180 mm (tabla koordinatı 0..180).
- Nozul: 0.4 mm (0.2 / 0.6 / 0.8 profilleri de yüklü).
- Açık gövde (kapalı kasa yok): PLA, PETG, TPU rahat; ABS/ASA çarpılır, önerilmez.
- AMS lite: 4 renk; tek nesnede çok renk için silme kulesi (prime tower, 35 mm) otomatik açılır ve her renk değişimi ~28 sn yükleme süresi ekler.
- Varsayılan tabla: Dokulu PEI (Textured PEI Plate), PLA için 65 °C.

## 3. Mimari: neyi kim yapar

```
Fikir / beğenilen model
   │
   ├─ Sıfırdan tasarım ──> OpenSCAD (.scad) veya build123d (.py) ──> STL
   ├─ Mevcut modeli değiştir ──> mesh_tools.py (ölçek, kes, delik, yazı, boolean) ──> STL
   │
   ▼
bambu_slice.py ──> BambuStudio CLI (profil düzleştirme + dilimleme + 3MF onarımı)
   │                 ──> .gcode.3mf + süre/gram raporu
   ▼
Bambu Studio GUI (AppleScript ile açılır) ──> kontrol ──> "Baskı tablasını yazdır" ──> yazıcı
```

GUI'yi tıklayarak model çizmek yerine geometriyi kodla üretmek bilinçli bir karar: tekrarlanabilir, ölçüleri kesin, değiştirmesi tek parametre. GUI sadece son kontrol ve gönderim için kullanılır.

## 4. CLI: kritik bilgiler ve tuzaklar

### 4.1 Temel komut

```bash
B=/Applications/BambuStudio.app/Contents/MacOS/BambuStudio
$B --load-settings "machine.json;process.json" \
   --load-filaments "filament1.json;filament2.json" \
   --orient 0 --arrange 1 --slice 0 \
   --outputdir /mutlak/klasör --export-3mf sonuc.gcode.3mf \
   model.stl
```

Öncelik sırası: komut satırı > `--load-settings/--load-filaments` > 3MF içindeki ayarlar.

### 4.2 Bulunan tuzaklar (hepsi araçlarda çözüldü)

1. **Profiller "inherits/include" zinciriyle gelir.** CLI düz (tam) JSON ister. `bambu_profiles.py flatten` zinciri çözer.
2. **`--export-3mf` sadece dosya adı almalı.** Yol, `--outputdir`'e göre çözülür; mutlak yol verirsen `out//Users/...` gibi bozuk yol oluşur. `--outputdir` mutlak olmalı.
3. **CLI'nin yazdığı 3MF GUI'de açılmaz.** `compatible_printers` listesi `Metadata/model_settings.config` içine kaçışsız tırnakla yazılıyor (`value=""Bambu Lab A1 mini 0.4 nozzle""`), GUI "Model dosyasının yüklenmesi başarısız oldu" der. `fix_3mf.py` tırnakları `&quot;` yapar ve `printer_model_id`'yi (A1 mini = `N1`) doldurur.
4. **`compatible_printers` boşaltılamaz.** Boş liste "process not compatible with printer" hatası verir; listeyi koru, 3MF'i sonradan onar.
5. **Çok renkte ikinci filament sessizce düşer.** `filament_map`, `filament_nozzle_map`, `filament_volume_map` vektörleri filament sayısı kadar olmalı ve her filament JSON'una `filament_colour` yazılmalı. Yoksa `layer_filament_list` boş kalır, yazı katmanları basılmaz.
6. **`--arrange 0` ile STL tabla dışında kalır.** Mesh 0,0 merkezliyse tabla 0..180 olduğu için "no object fully inside" hatası gelir. Ya `--arrange 1` kullan ya da modeli 90,90'a taşı.
7. **Tek tasarımın renkli parçaları için `--assemble`.** Taban ve yazı ayrı STL olarak verilir, `--assemble` bunları koordinatlarını koruyarak tek nesnenin parçaları yapar, `--load-filament-ids "1,2"` parça başına renk atar.
8. **`open -a BambuStudio dosya` her seferinde yeni pencere/süreç açar.** Çalışan örneğe göndermek için:
   `osascript -e 'tell application id "com.bambulab.bambu-studio" to open POSIX file "/yol/dosya.3mf"'`
   STL mevcut projeye eklenir, 3MF proje olarak açılır.
9. `--orient 1` modeli kendi kafasına göre çevirir; tasarımı baskı yönünde yaptıysan `--orient 0` bırak.
10. Çıkış kodu 0 değilse `result.json` içindeki `error_string` ve log'daki `[error]` satırları sebebi söyler. Yaygın kodlar: 239 uyumsuz profil, 206 boş tabla, 243 dosya yazılamadı.
11. **CLI ile yeniden dilimlenen 3MF GUI'de açılınca bazı `--set` değerleri kaybolabiliyor.** Gerçek örnek: `wall_loops=4`, `bottom_shell_layers=5`, `sparse_infill_density=25%`, `gyroid` dosyada yazılıydı ama GUI 2 / 4 / %15 / ızgara gösterdi. Açtıktan sonra Dayanıklılık sekmesini kontrol et, alanları elle düzelt, GUI'de dilimle ve gramı CLI sonucuyla karşılaştır.
12. **Birden çok Bambu Studio örneği çalışabilir.** "Şu an açık olan" tasarım için `BambuStudio.conf` içindeki `recent_projects` ve dosyanın değişiklik saatine bak, sonra ekran görüntüsüyle doğrula.

### 4.3 Çıktıyı okumak

- `result.json`: plaka başına gram, nesneler, süre tahmini (saniye).
- G-code başlığı: `; total estimated time`, `; total filament weight [g]`, `; total layer number`.
- 3MF içi: `Metadata/plate_1.gcode` (yazıcıya giden), `Metadata/plate_1.png` (önizleme), `Metadata/slice_info.config` (filament/yuva eşlemesi), `Metadata/project_settings.config` (tüm ayarlar).

## 5. Araç seti (`~/bambu-studio-skill/scripts`)

### 5.1 `bambu_profiles.py`

```bash
python3 bambu_profiles.py list process --filter A1M
python3 bambu_profiles.py list filament --filter "PLA Basic"
python3 bambu_profiles.py show process "0.20mm Standard @BBL A1M" wall_loops sparse_infill_density
python3 bambu_profiles.py flatten process "0.16mm Optimal @BBL A1M" -o p.json --set wall_loops=3
```

### 5.2 `bambu_slice.py` (ana araç)

```bash
# Tek parça, varsayılan: A1 mini 0.4, 0.20mm Standard, Bambu PLA Basic, Dokulu PEI
python3 bambu_slice.py parca.stl --open

# Ayar değiştirerek
python3 bambu_slice.py parca.stl --process "0.16mm Optimal @BBL A1M" \
  --set sparse_infill_density=25% --set wall_loops=3 \
  --set enable_support=1 --set support_type="tree(auto)" --set brim_type=outer_only

# İki renkli tek parça (taban beyaz, yazı kırmızı)
python3 bambu_slice.py taban.stl yazi.stl --assemble \
  --filament "Bambu PLA Basic @BBL A1M" --filament "Bambu PLA Basic @BBL A1M" \
  --color "#FFFFFF" --color "#C12E1F" --filament-ids 1,2

# PETG, 6 kopya
python3 bambu_slice.py klips.stl --filament "Bambu PETG HF @BBL A1M" --copies 6
```

Çıktı JSON: `exit`, `out` (3MF yolu), `plates` (süre, gram, katman), `errors`. `--open` sonucu çalışan Bambu Studio'da açar.

### 5.3 `mesh_tools.py` (indirilen modeli değiştirme)

```bash
P=~/bambu-studio-skill/.venv/bin/python; M=~/bambu-studio-skill/scripts/mesh_tools.py
$P $M info model.stl                                   # ölçü, hacim, kapalı mı, tablaya sığar mı
$P $M scale model.stl out.stl --fit 170                # en uzun kenar 170 mm
$P $M scale model.stl out.stl --factor 1.25
$P $M rotate model.stl out.stl --x 90                  # sonra tablaya oturtur
$P $M flat model.stl out.stl                           # en stabil yüzü tabana yatır
$P $M cut model.stl out.stl --z 90 --keep both         # A1 mini'ye sığmayanı ikiye böl
$P $M hole model.stl out.stl --at 10,0 --d 5.2         # M5 için 5.2 mm delik
$P $M text model.stl out.stl --text "MERHABA" --size 8 --depth 0.8 --mode deboss
$P $M textpart model.stl yazi.stl --text "MERHABA" --size 8 --depth 1   # iki renk için ayrı parça
$P $M boolean a.stl b.stl out.stl --op union --move-b 0,0,10
$P $M repair bozuk.stl temiz.stl
$P $M convert model.step model.stl                     # STEP/OBJ/3MF/PLY -> STL
$P $M preview model.stl onizleme.png --view iso        # görsel kontrol
$P $M firstlayer model.3mf [--d 5]                     # baskı öncesi tutunma kontrolü: ince uçlar, havada başlayan bölgeler, brim önerisi
```

`firstlayer` tablaya değen ilk katman kesitini çıkarır ve `--d` mm'den (varsayılan 5) dar uçları bulur. Yaprak ucu, parmak, sivri köşe gibi uçlar ilk katmanlarda kalkar, nozul onları sürükleyip örümcek ağına çevirir; yazıcı bunu fark etmez. İnce uç varsa ADVICE `brim_type=outer_only` ve `initial_layer_speed=30` önerir.

## 6. Sıfırdan tasarım

### 6.1 OpenSCAD (varsayılan seçim)

Basit-orta karmaşıklıkta, ölçü odaklı parçalar için en hızlı yol. Her zaman `--backend=manifold` kullan (eski CGAL motorundan 10-100 kat hızlı).

```bash
openscad --backend=manifold -D 'name="MERHABA"' -D 'part="base"' -o taban.stl templates/name_tag.scad
openscad --backend=manifold -o onizleme.png --render --viewall --autocenter --imgsize=900,700 dosya.scad
```

Doğrulanmış şablonlar (`templates/`):

| Şablon | Ne | A1 mini sonucu |
|---|---|---|
| `name_tag.scad` | İki renkli isimlik/anahtarlık, `part="base"/"text"` | 16 dk, 4 g |
| `box_lid.scad` | Kapaklı kutu, 0.2 mm sürgülü geçme | 37 dk, 21 g |
| `phone_stand.scad` | Desteksiz telefon standı, kablo yarığı | 1 sa 44 dk, 54 g |

### 6.2 build123d (gelişmiş)

Pah/radius, STEP çıktısı, gerçek B-rep gereken mekanik parçalarda. `~/bambu-studio-skill/.venv/bin/python` ile çalışır.

```python
from build123d import *
with BuildPart() as p:
    Box(40, 20, 6)
    fillet(p.edges().filter_by(Axis.Z), radius=3)
    with Locations((0, 0, 3)):
        Hole(radius=2.6)
export_stl(p.part, "parca.stl")
```

## 7. FDM tasarım kuralları (A1 mini, 0.4 nozul)

| Konu | Kural |
|---|---|
| Duvar | En az 0.8 mm (2 çizgi), sağlam parça 1.6 mm (4 çizgi) |
| Taban/üst | En az 0.8-1.0 mm (4-5 katman @0.2) |
| Çıkıntı | 45°'ye kadar desteksiz; daha yatay yüzeyler için pah ver veya destek aç |
| Köprü | 20-30 mm'ye kadar sorunsuz |
| Delik | Dikey delikler ~0.1-0.2 mm küçük çıkar; M3 için 3.2, M5 için 5.2 mm |
| Geçme toleransı | Sıkı 0.1, sürgülü 0.2, rahat 0.3-0.4 mm |
| Kabartma yazı | Harf boyu en az 5 mm, yükseklik 0.6-1.2 mm; kazıma derinliği 0.6-1 mm |
| Pim/çubuk | 3 mm altı çap kırılgan; dikey ince çubuklarda brim aç |
| Yön | Kuvvet katman çizgilerine paralel gelsin; en geniş düz yüz tabana |
| Fil ayağı | İlk katman hafif taşar; geçmeli parçada alt kenara 0.4 mm pah ver |
| Çok renk | Renk değişimini mümkünse sadece üst katmanlara koy (yazı, logo); her değişim süre ve atık ekler |
| Büyük parça | 180 mm'yi aşarsa `cut` ile böl, birleşim için pim deliği ekle |

## 8. En çok kullanılan ayar anahtarları

Varsayılanlar `0.20mm Standard @BBL A1M` profilinden okundu.

| Anahtar | Varsayılan | Not |
|---|---|---|
| `layer_height` | 0.2 | 0.08-0.28 arası profiller var |
| `wall_loops` | 2 | Sağlamlık için 3-4 |
| `top_shell_layers` / `bottom_shell_layers` | 5 / 3 | |
| `sparse_infill_density` | 15% | Fonksiyonel parça 25-40% |
| `sparse_infill_pattern` | grid | gyroid, cubic, honeycomb, lightning, adaptivecubic |
| `top_surface_pattern` | monotonicline | |
| `enable_support` | 0 | 1 = aç |
| `support_type` | tree(auto) | normal(auto), tree(manual), normal(manual) |
| `support_threshold_angle` | 30 | |
| `support_on_build_plate_only` | 0 | |
| `brim_type` | None | auto_brim, outer_only, inner_only, outer_and_inner, no_brim |
| `brim_width` | 5 | |
| `raft_layers` | 0 | |
| `seam_position` | aligned | nearest, back, random |
| `ironing_type` | no ironing | top, topmost, solid |
| `print_sequence` | by layer | by object (A1 mini'de kafa boşluğuna dikkat) |
| `enable_prime_tower` | 1 | Çok renkte gerekli |
| `fuzzy_skin` | none | external, all |
| `spiral_mode` | 0 | 1 = vazo modu |
| `elefant_foot_compensation` | 0 | 0.1-0.15 geçmeli parçada |
| `xy_hole_compensation` | 0 | Delik dar çıkıyorsa 0.1 |
| `outer_wall_speed` | 200 | Görsel kalite için 120-150 |
| `curr_bed_type` | (tabla) | Textured PEI Plate, Cool Plate, Engineering Plate, High Temp Plate, Supertack Plate |

Filament (`Bambu PLA Basic @BBL A1M`): nozul 220 °C, Dokulu PEI 65 °C, maks hacimsel hız 21 mm³/s, akış 0.98. PETG HF: 240 °C, tabla 70 °C, 18 mm³/s. A1 mini için 60 civarı hazır filament profili var (TPU 90A/95A, Generic PETG, PLA-CF, PVA dahil): `bambu_profiles.py list filament --filter A1M`.

## 9. GUI haritası (Türkçe arayüz)

Üst sekmeler: Ana sayfa · **Hazırla** · **Önizleme** · **Cihaz** · Proje · Kalibrasyon. Sağ üstte **Baskı tablasını dilimle** ve **Baskı tablasını yazdır** düğmeleri.

Sol panel (Hazırla): Yazıcı (Bambu Lab A1 mini, tabla tipi, AMS senkronizasyonu) · Püskürtme Ucu (Çap 0.4, Akış Standart) · Proje Filamentleri (1-7 yuva, "Karışık Filament Ekle") · İşlem (Küresel / Nesneler, "Gelişmiş" anahtarı tüm ayarları açar; sekmeler: Kalite, Dayanıklılık, Destek, Diğerleri).

Menüler ve kısayollar:

| Menü | Öğe | Kısayol |
|---|---|---|
| Dosya | Yeni Proje / Proje Aç / Projeyi Kaydet | ⌘N / ⌘O / ⌘S |
| Dosya > İçe Aktar | 3MF/STL/STEP/SVG/OBJ/AMF dosyalarını içe aktar | |
| Dosya > Dışa Aktar | Tek STL, ayrı STL'ler, Genel 3MF, Dilimlenmiş dosya, G-kodu, Ön Ayar Paketi | |
| Dosya | MakerWorld'de yayınla | |
| Düzenle | Geri Al, Yinele, Tümünü sil (⇧⌘D), Seçilenleri klonla (⌘K) | |
| Görüntüle | Varsayılan 0, Üst 1, Alt 2, Ön 3, Arka 4, Sol 5, Sağ 6, İzometrik 7 | ⌘0..⌘7 |
| Görüntüle | Çıkıntıyı Göster | ⌘L |

Menüyü komutla tetiklemek (Accessibility izni gerekir):

```bash
osascript -e 'tell application "System Events" to tell process "BambuStudio" to click menu item "Projeyi Kaydet" of menu 1 of menu bar item "Dosya" of menu bar 1'
```

**Cihaz sekmesi:** kamera, baskı ilerlemesi (yüzde, katman, kalan süre), sıcaklıklar, eksen kontrolü, AMS lite yuvaları ve renkleri. Baskı sürerken buradaki duraklat/durdur düğmelerine asla dokunma.

**Yazdırma akışı:** 3MF açık → "Baskı tablasını dilimle" → "Baskı tablasını yazdır" → gönderim penceresinde yazıcıyı, filament-AMS yuva eşlemesini ve seçenekleri (yatak seviyeleme, timelapse, akış kalibrasyonu) kontrol et → "Gönder". Pencerenin düzeni sürüme göre değişebilir; her seferinde ekran görüntüsüyle doğrula. Gönderim fiziksel bir makineyi çalıştırır: kullanıcı onayı olmadan basılmaz, yazıcı meşgulse gönderilmez.

## 10. Uçtan uca iş akışları

### A. "Şu modeli beğendim, şöyle değiştir"

1. Modeli indir (MakerWorld'den Bambu Studio içinden ya da tarayıcıdan; dosya genelde `~/Downloads`'a düşer). Lisansına bak (ticari kullanım, remix izni).
2. 3MF ise ve sadece ayar değişecekse: doğrudan `bambu_slice.py model.3mf --set ...`.
3. Geometri değişecekse STL'e çevir, `mesh_tools.py info` ile ölç.
4. İstenen değişikliği uygula (ölçek, delik, yazı, kesme, birleştirme).
5. `mesh_tools.py preview` ile görsel kontrol.
6. `bambu_slice.py ... --open` ile dilimle ve GUI'de aç.
7. Süre/gram raporunu kullanıcıya ver, onay gelirse gönder.

### C. Baskı öncesi kontrol listesi (her baskıda)

1. Açık tasarımı doğru tespit et (`recent_projects` + dosya saati + ekran görüntüsü).
2. Tasarımcının ayarlarını oku (`project_settings.config`, `slice_info.config`), değişiklikleri tasarımcı vs yeni tablosuyla raporla.
3. İşlevsel parçada dayanıklılık: 4 duvar, %25 jiroid, üst/alt 6/5. Çoğu zaman sadece +%10-20 gram.
4. `mesh_tools.py firstlayer` çalıştır ve önerilerini uygula, otomatiğe bırakma:
   - ince uç varsa `brim_type=outer_only` (`auto_brim` PLA + Dokulu PEI'de genelde hiç brim basmaz);
   - taban 120 mm'den genişse ya da temas alanı 3000 mm²'yi geçiyorsa `raft_layers=3` (ya da `brim_type=outer_only`, `brim_width=8`), parçanın çevresinde en az 8 mm boşluk bırak, gerekirse modeli birkaç yüzde küçült;
   - bu durumların hepsinde `initial_layer_speed=30`, `initial_layer_infill_speed=50`;
   - 45°'den dik sarkma 50 mm²'yi geçiyorsa `enable_support=1`, `support_type=tree(auto)`, `support_on_build_plate_only=1`.
   Gerçek örnekler: yaprak ucu kalktı (ince uç); 173 mm'lik top askısı köşeden kalktı, baskı durduruldu, raft + destek + yavaş ilk katmanla tekrar basıldı.
5. GUI'de aç, Dayanıklılık sekmesindeki değerleri doğrula, GUI'de dilimle, gramı karşılaştır, kaydet.
6. Cihaz sekmesinde yazıcı boşta mı, kullanıcının istediği AMS yuvası (ör. A3 yeşil) eşleşmiş mi bak.
7. Gönder penceresinde yatak düzleme açık; "yüzey kusuru" uyarısı gelirse hızlandırılmış çekimi kapat.
8. Kullanıcıya ilk 3 katmanı izlemesini söyle; tabla bulaşık deterjanıyla yıkanmış ve kurumuş olsun.

### B. "Sıfırdan şunu tasarla"

1. İhtiyacı ölçülere çevir (ne tutacak, hangi ölçüler, hangi malzeme, kaç renk). Eksik kritik ölçü varsa sor.
2. Şablon uygunsa parametreleri değiştir, değilse yeni `.scad` yaz (parametreler en üstte, birim mm).
3. STL üret, `info` ile tablaya sığdığını ve kapalı (watertight) olduğunu doğrula.
4. PNG önizleme üret ve bak; şekil yanlışsa düzelt.
5. Baskı yönünü tasarımda belirle (desteksiz basılacak şekilde).
6. Dilimle, süre/gram raporla, GUI'de aç, onayla gönder.

## 11. Sorun giderme

| Belirti | Sebep | Çözüm |
|---|---|---|
| GUI "Model dosyasının yüklenmesi başarısız" | CLI 3MF tırnak hatası | `fix_3mf.py dosya.3mf --model-id N1` |
| `process not compatible with printer` (239) | Profil başka yazıcı için ya da compat listesi silinmiş | Doğru `@BBL A1M` profilini seç |
| `Nothing to be sliced` (206) | Nesne tabla dışında | `--arrange 1` ya da modeli 90,90'a taşı |
| `Unable to open the file ...tmp` (243) | `--export-3mf` yol içeriyor | Sadece dosya adı ver, `--outputdir` mutlak olsun |
| İkinci renk basılmıyor | filament_map eksik | `bambu_slice.py` kullan (vektörleri doldurur) |
| Her açılışta yeni pencere | `open -a` | AppleScript `open POSIX file` |
| Mesh `watertight=False` | Açık yüzey | `mesh_tools.py repair`, olmazsa Bambu Studio'da sağ tık > Onar |
| OpenSCAD yavaş | CGAL motoru | `--backend=manifold` |
| İnce uç (yaprak ucu, sivri köşe) ilk katmanlarda kalkıp örümcek ağı gibi iplik oluyor, yazıcı hata vermiyor | Uç tablaya az alanla değiyor, kalkınca nozul sürüklüyor; A1 mini kalkan ucu algılamaz | Baskı devam edebilir, uç sonradan temizlenir. Sonraki baskıda `firstlayer` kontrolü, `brim_type=outer_only`, `initial_layer_speed=30`, tablayı deterjanla yıka |
| Büyük parça köşeden kalkıyor (warping) | Geniş taban, kenarlar soğurken büzülüyor | `raft_layers=3` ya da 8 mm dış brim, ilk katman 30 mm/s, destek gerekiyorsa tree; tablayı deterjanla yıka |
| GUI'deki değerler CLI'de verdiğin `--set` değerlerinden farklı | Yeniden açılan 3MF'te GUI bazı değerleri ön ayardan okuyor | GUI'de elle düzelt, GUI'de dilimle, gramı karşılaştır |
| "Anlık hızlandırılmış çekim yüzey kusuru" uyarısı | Timelapse açık | Gönder penceresinde Hızlandırılmış çekim: Off |
| Tıklama başka uygulamaya gidiyor | Önde başka pencere (ör. Word) | Yeni ekran görüntüsü al, tekrar tıkla |

## 12. Güvenlik ve sınırlar

- Yazıcıya gönderim, baskıyı durdurma/duraklatma ve kalibrasyon her zaman kullanıcı onayıyla yapılır.
- LAN erişim kodu ve hesap bilgileri hiçbir dosyaya, skill'e ya da repoya yazılmaz.
- İndirilen modellerin lisansı korunur; remix yayınlanacaksa orijinal tasarımcıya atıf verilir.
