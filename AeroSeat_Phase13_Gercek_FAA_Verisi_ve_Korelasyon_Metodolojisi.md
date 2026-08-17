# AeroSeat Phase 13 — Gerçek FAA Verisi ve Resmi Korelasyon Metodolojisi

Bu doküman "gerçek veriye erişebilir misin" sorusuna doğrudan cevaptır. Cevap: **evet, kısmen** — tam ham zaman-serisi (CSV/binary sensor çıktısı) değil ama şunları buldum:

1. **FAA'nın kendi resmi korelasyon metodolojisi** (AC 20-146A, Appendix B) — önceki dokümanımdaki ISO/TS 18571 önerisinin yerini alması gereken, sizin sertifikasyon bağlamınıza özel, tam formülasyonlu ve **gerçekten uygulanmış bir sayısal örnekle** (Appendix A) birlikte.
2. **Gerçek CAMI (FAA Civil Aerospace Medical Institute) sled test sonuçları** — tablo halinde gerçek tepe değerleri (peak lumbar/T12 yükü, kemer yükü, kolçak kuvveti), 16g ve 9.6g darbeleri için, birden fazla konfigürasyonda.
3. FAA'nın **mass scaling ve adaptif $dt$** konusundaki resmi kılavuzu — Phase 12 dokümanımdaki önerileri artık "endüstri pratiği" değil, **doğrudan FAA referansı** olarak teyit ediyor.

Bunların hiçbiri "OTEST'teki gerçek deneyiminizin yerini tutmaz" ama kodlanabilir, sayısal, alıntılanabilir gerçek veri.

---

## 1. FAA'nın Resmi Korelasyon Metodolojisi: Sprague & Geers Comprehensive Error

**Kaynak:** AC 20-146A, "Methodology for Dynamic Seat Certification by Analysis" (FAA, 2018) — bu doküman tam olarak sizin ürününüzün varlık nedeni olan konuyu düzenliyor: **bilgisayar modellemesiyle koltuk sertifikasyonu**. Appendix B, test-simülasyon karşılaştırma yöntemini tanımlıyor.

### 1.1 Neden ISO/TS 18571 Yerine Bunu Kullanmalısınız

ISO/TS 18571 otomotiv endüstrisi için geliştirildi. AC 20-146A ise **doğrudan FAA'nın kendi kabul ettiği, uçak koltuğu sertifikasyonuna özel** yöntemdir — yani bir ACO'ya (Aircraft Certification Office) "modelimiz doğrulanmıştır" derken referans göstereceğiniz standart bu olmalı, ISO 18571 değil.

### 1.2 Sprague & Geers Comprehensive Error — Tam Formülasyon

Referans (test) sinyali $m(t)$, simülasyon sinyali $c(t)$, değerlendirme aralığı $[t_1, t_2]$:

$$
I_{mm} = \frac{1}{t_2-t_1}\int_{t_1}^{t_2} m(t)\,m(t)\,dt
$$
$$
I_{cc} = \frac{1}{t_2-t_1}\int_{t_1}^{t_2} c(t)\,c(t)\,dt
$$
$$
I_{mc} = \frac{1}{t_2-t_1}\int_{t_1}^{t_2} m(t)\,c(t)\,dt
$$

**Büyüklük hatası (test'e göre):**
$$
SG_M = \sqrt{\frac{I_{cc}}{I_{mm}}} - 1
$$

**Faz hatası:**
$$
SG_P = \frac{1}{\pi}\arccos\left(\frac{I_{mc}}{\sqrt{I_{mm}\cdot I_{cc}}}\right)
$$

**Kapsamlı hata (nihai skor):**
$$
SG_C = \sqrt{SG_M^2 + SG_P^2}
$$

Bu, önceki dokümanımdaki 4 alt-metrikli (Z/P/M/S) ISO yaklaşımından **daha basit ve daha az parametre belirsizliği** içeriyor — sadece iki bileşen (büyüklük + faz), ve FAA'nın kendi örneğinde gerçek sayılarla gösterilmiş.

### 1.3 FAA'nın Resmi Kabul Kriterleri (Appendix A/8.3'ten, Doğrudan Alınabilir)

Bunlar `calibration_engine.py`'nizdeki hedef toleransları olmalı — artık tahmin etmenize gerek yok, FAA'nın kendi sayıları:

| Parametre | Kabul Kriteri |
|---|---|
| Peak tepe değeri (yük, moment, ivme, hız) | Test'e göre **≤10%** fark |
| Eğri şekli (Sprague-Geers Comprehensive) | **≤10%** |
| HIC | Test değerine göre **≤100 HIC birimi** fark |
| HIC integrasyon zaman penceresi ($t_1,t_2$) | Test ile **≤5 ms** fark |
| Çarpma hızı (head strike velocity) | **≤10%** fark |
| Lumbar yük (1500 lbs limitine karşı) | Test'e göre ≤10%; doğrulama için sadece **≤1430 lbs** üreten test verisi kullanılmalı (ölçüm belirsizliği payı) |
| HIC (model kullanım limiti) | Doğrulama için sadece **≤890 HIC birimi** üreten test verisi kullanılmalı |
| Taban (floor) reaksiyon yükü | **≤10%** |
| Femur basma yükü | **≤10%** |

**Kritik detay — istatistiksel güvenlik payı mantığı:** FAA, lumbar yük ölçüm belirsizliğinin (~±125 lbs, tekrarlanan testlerden) $\%95$ güven aralığında $\sigma \approx 42$ lbs standart sapmaya karşılık geldiğini gösteriyor; bu yüzden 1500 lbs yasal limitin $\%95$ güvenle altında kalmak için **1430 lbs**'i pratik hedef olarak kullanıyorlar. Aynı istatistiksel mantığı kendi BEPU Monte Carlo motorunuzda (Phase 10) zaten kullanıyorsunuz — burada FAA'nın bunu regülasyon seviyesinde onayladığını görüyoruz, yönteminiz doğru yöndeydi.

### 1.4 Gerçek Sayısal Örnek — Appendix A (Kod Testi İçin Kullanılabilir Referans)

FAA'nın kendi validasyon örneği, MADYMO ile bir ön sıra koltuk + bulkhead köpüğü senaryosunda:

| Kanal | Test | Simülasyon | Fark |
|---|---|---|---|
| Kafa tepe rezültan ivmesi | 82.3 g | 83.8 g | %2 (konservatif) |
| İvme eğrisi şekli (curve shape error) | — | — | %9.8 |
| Kafa çarpma hızı | 38.5 fps | 37.7 fps | %2.0 |
| HIC | 700 | 650 | 50 birim (limit: 100) |
| $t_1$ (HIC penceresi başlangıcı) | 144 ms | 139 ms | 5 ms (limit: 5 ms — sınırda) |
| $t_2$ (HIC penceresi bitişi) | 164 ms | 164 ms | 0 ms |
| Baş yolu (x-pozisyon) şekil hatası | — | — | %5.1 |
| Baş yolu (z-pozisyon) şekil hatası | — | — | %8.5 |

**Bunu ne için kullanabilirsiniz:** Bu, `test_correlation_methodology.py` gibi bir dosyada **regresyon testi** olarak kodlanabilir — Sprague-Geers formülünüzün doğru çalıştığını, bu bilinen test/simülasyon çiftinden gelen bilinen sonuçları (SG_M, SG_P, SG_C değerleri) yeniden üretip üretmediğini kontrol ederek doğrulayabilirsiniz. Bu, "algoritma doğru mu" sorusunu (2 hafta önceki tartışmamızdaki endişem) gerçek bir referans noktasıyla kapatır.

---

## 2. Gerçek CAMI Sled Test Verisi (DOT/FAA/21/07)

**Kaynak:** Moorcroft, D. (2021), "Simulation of Oblique Loading Configurations Using an FAA Hybrid III Virtual ATD", DOT/FAA/21/07, FAA Civil Aerospace Medical Institute.

Bu rapor, CAMI'nin gerçek rijit koltuk sled testlerini MADYMO simülasyonuyla karşılaştırıyor. Test açısı sizin ana senaryonuzdan (0° = düz ileri) farklı yönlere de gidiyor ama **0° konfigürasyonu ve 16g/9.6g darbe tanımları doğrudan sizin kullanım senaryonuzla örtüşüyor**.

### 2.1 Darbe (Pulse) Tanımı

$$
\text{16g darbe: izosel üçgen, tepe } 16g, \quad \text{9.6g darbe: aynı şekil, tepe } 9.6g \text{ (16g'nin \%60'ı)}
$$

Her ikisi de $t=0$'da başlayıp $t=180\text{ms}$'de bitiyor.

### 2.2 Gerçek Tepe Yük Tablosu (0°, Kucak Kemeri, Kolçaksız) — `test_correlation_methodology.py` için Kullanılabilir Kalibrasyon Hedefi

| Darbe | Lumbar $F_z$ | T12 $F_z$ |
|---|---|---|
| 16g | 2564 lbs | 3699 lbs |
| 9.6g | 1193 lbs | 1644 lbs |

### 2.3 Omuz Kemerli Konfigürasyon (0°, Kolçaksız)

| Darbe | Lumbar $F_z$ | T12 $F_z$ | Kemer Yükü |
|---|---|---|---|
| 16g | -273 lbs (basma) | -265 lbs | 1315 lbs |
| 9.6g | -379 lbs | -382 lbs | 836 lbs |

**Dikkat edilmesi gereken gerçek bir fiziksel bulgu:** Bu veri setinde omuz kemerli konfigürasyonda **9.6g darbesi 16g'den daha yüksek lumbar basma yükü üretiyor** — sezgiye aykırı görünüyor ama rapor bunu açıklıyor: 16g'de daha güçlü öne fırlama hem gerilme (flail) hem de omuz kemerinden gelen basma kuvvetini artırıyor, bu ikisinin toplamı 16g'de daha yüksek net basma vermiyor. **Bu, sizin motorunuzun da yakalaması gereken bir davranış** — eğer modeliniz "darbe şiddeti arttıkça her zaman yük artar" gibi monoton bir varsayımla kodlanmışsa, bu gerçek veri noktası o varsayımı çürütüyor ve `lumped_mass_model.py`'nizde bir doğrulama testi olarak kullanılmalı.

### 2.4 Bu Verinin Sınırlamaları (Dürüstçe)

- Bu **rijit koltuk** testi — sizin 3-fazlı foam modelinizin, elasto-plastik seat-track'inizin doğrudan karşılığı yok burada. Yani foam/yapısal deformasyon kalibrasyonu için kullanılamaz, sadece **manken-kemer-pelvis dinamiği** için kullanılabilir.
- Ham zaman-serisi (CSV) yok, sadece tepe değer tabloları — Sprague-Geers gibi eğri-şekli metrikleri için yeterli değil, sadece **büyüklük (magnitude) korelasyonu** için kullanılabilir.
- Raporun kendi sonucu da dürüst bir uyarı içeriyor: **MADYMO modeli bu senaryolarda test verisiyle iyi örtüşmedi** (lumbar/T12 yük dağılımı gerçek testte farklı çıktı) — yani bu veriyi kullanırken "endüstri lideri yazılım bile mükemmel eşleşmiyor" gerçeğini de göz önünde bulundurun; sizin motorunuzdan da birebir eşleşme beklemeyin, FAA'nın kendi toleransları (±10%) zaten bu belirsizliği kabul ediyor.

---

## 3. FAA'nın Mass Scaling ve Adaptif $dt$ Kılavuzu — Phase 12'yi Teyit Ediyor ve Netleştiriyor

AC 20-146A doğrudan şunu söylüyor: kritik zaman adımı Courant kararlılık koşuluna göre hesaplanır,

$$
\Delta t_{cr} = \frac{2}{\omega} = \min\left(\frac{L}{c}\right)
$$

ve **LS-DYNA, RADIOSS, MADYMO, PAM-CRASH gibi ticari kodların hepsi** zaman adımını sabit tutmak yerine her döngüde yeniden hesapladığını doğruluyor — Phase 12'de OpenRadioss'tan çıkardığım öneri, aslında FAA'nın kendi kabul ettiği endüstri pratiğiymiş.

**Yeni, kesin sayısal sınırlar (Phase 12'deki genel öneriyi netleştiriyor):**

- Mass scaling **sadece** kritik olmayan küçük elemanlara uygulanmalı
- Kritik koltuk bileşenleri için toplam kütle artışı **%5'i geçmemeli**
- Kritik olmayan bileşenler için **%10'a kadar** kabul edilebilir
- Quasi-statik simülasyonlarda (kinetik enerji küçükse) **%10'a kadar** kabul edilebilir

`lumped_mass_model.py`'deki mass scaling implementasyonunuzda bu yüzdeleri bir doğrulama kontrolü olarak ekleyin: her segment için $\dfrac{m_i^{scaled}-m_i}{m_i}$ oranını hesaplayıp bu eşiklerin üzerine çıkarsa uyarı verin.

**Ayrıca yeni bir dokümantasyon gereksinimi (VAR — Validation and Analysis Report) için not:** FAA, enerji dengesi raporlamasını **zorunlu** tutuyor — başlangıç/bitiş enerji oranı ve hourglass enerjisinin toplam enerjiye oranı VAR'da açıkça belirtilmeli. Bu, Phase 10/11'deki enerji denetimi maddenizin "isteğe bağlı iyi pratik" değil, **sertifikasyon dokümantasyonu gereksinimi** olduğunu gösteriyor — `EnergyMomentumAuditEngine` çıktısını doğrudan VAR formatına uyacak şekilde raporlayan bir modül ekleyin (`energy_balance_report.py`).

---

## 4. Somut Sonraki Adımlar

### 4.1 Hemen Yapılabilir (Bu Hafta)

1. `correlation_engine.py`'yi ISO 18571 yerine **Sprague-Geers formülasyonuyla** yeniden yazın (Bölüm 1.2)
2. FAA'nın Appendix A örneğini (Bölüm 1.4 tablosu) birim test olarak kodlayın — algoritmanızın doğruluğunu bilinen bir referansla doğrulayın
3. `calibration_engine.py`'ye Bölüm 1.3'teki resmi tolerans tablosunu (±10%, HIC±100, vb.) hedef fonksiyon eşiği olarak ekleyin
4. Bölüm 2.3'teki gerçek CAMI tepe yük tablosunu (16g/9.6g, lumbar/T12) bir regresyon test verisi olarak `test_golden_reference.py`'ye ekleyin — en azından büyüklük (magnitude) korelasyonu için gerçek bir dış referans noktanız olur

### 4.2 Orta Vadeli — Gerçek Ham Veri Tedariki

Bulduğum kaynaklar **tablo/özet veri**, tam zaman-serisi (dijital, örnekleme frekansı 10kHz) değil. Tam ham veri için üç somut yol:

- **CAMI'ye doğrudan başvuru:** DOT/FAA/21/07 ve benzeri raporların yazarı (FAA Civil Aerospace Medical Institute, Biodynamics Research Team) — bu, akademik/düzenleyici kurum olduğu için araştırma amaçlı ham veri paylaşım talebi makul bir yoldur. Rapor referanslarındaki isimlere (D. Moorcroft, R. DeWeese) atıfla iletişime geçebilirsiniz.
- **Grafik dijitalleştirme (WebPlotDigitizer vb.):** FAA raporlarındaki (Figure 19, 20, 24, 26 gibi) yük-zaman grafiklerinden piksel-koordinat tabanlı veri çıkarımı — akademik camiada yaygın, meşru bir teknik. Tam çözünürlük vermez ama Sprague-Geers eğri-şekli metriği için ham CSV'den çok daha iyi bir başlangıç noktasıdır.
- **OTEST deneyiminiz:** Sizin kendi geçmiş internship'inizden erişebileceğiniz gerçek 14g/16g test kayıtları var mı — bu, dış kaynaklardan daha değerli olur çünkü zaten sizin/şirketinizin verisi.

Golden dataset tedariki hâlâ en büyük açık ama artık elinizde (a) doğru resmi metodoloji, (b) o metodolojinin gerçek bir sayısal örneği, (c) en azından tepe-değer seviyesinde gerçek fiziksel referans noktaları var — sıfırdan başlamıyorsunuz.
