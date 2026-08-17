# AeroSeat Phase 12 — Endüstriyel Çözücü İncelemesi ve Entegrasyon Planı

Bu doküman 5 aracın (Virtual CRASH 6, ANSYS Explicit Dynamics/LS-DYNA, OpenRadioss, MATLAB/Simulink, CEFA FAS) derinlemesine incelemesini, gerçekten erişilebilir olan kaynaklardan (halka açık teori kılavuzları + OpenRadioss açık kaynak kodu) çıkarılan somut algoritmaları, ve bunların AeroSeat kod tabanınıza (`constitutive.py`, `lumped_mass_model.py`) nasıl entegre edileceğini içerir. Phase 10/11 dokümanlarınızdaki maddeleri günceller, yeni maddeler ekler.

**Erişim gerçeği (tekrar, netlik için):** Kapalı kaynak ticari yazılımların (ANSYS/LS-DYNA, Virtual CRASH) derlenmiş kodunu göremiyorum. Aşağıdaki her formül, ilgili yazılımın **halka açık teori kılavuzu, teknik destek dokümantasyonu veya akademik literatürden** derlenmiştir — yani "tersine mühendislik" değil, zaten yayınlanmış mühendislik bilgisidir.

---

## 1. OpenRadioss — Gerçek Açık Kaynak İnceleme

### 1.1 Mimari ve Erişim

OpenRadioss, Altair'in ticari Radioss çözücüsünün açık kaynak (GPLv2) çekirdeğidir; GitHub'da (`OpenRadioss/OpenRadioss`) gerçek Fortran/C++ kaynak kodu mevcuttur. Mimarisi iki aşamalıdır:

- **Starter:** Girdi dosyasını okur, model kurulumunu, başlangıç koşullarını ve malzeme/geometri doğrulamasını yapar.
- **Engine:** Asıl zaman entegrasyonu döngüsünü çalıştırır.

**Sizin mimarinize paralellik:** Bu, sizin zaten planladığınız `TestConfiguration` (kurulum/doğrulama) ile `PhysicalTest`/job lifecycle (`QUEUED → PREPARING → RUNNING → ...`) ayrımıyla kavramsal olarak birebir aynı. Yani mimari felsefeniz zaten endüstri standardına uygun — burada değişiklik önermiyorum, sadece teyit ediyorum.

### 1.2 Kritik Zaman Adımı (dt_crit) — Şu Anki Sabit dt=0.0001s Yerine

Endüstriyel explicit çözücülerde zaman adımı **sabit değildir**, her adımda sistemdeki en sert (stiffest) bağlantıya göre otomatik hesaplanır (merkezi fark integrasyonunun kararlılık koşulu — Courant-Friedrichs-Lewy kriterinin lumped-parameter karşılığı):

$$
dt_{crit} = TSSFAC \cdot \min_i \left( \frac{2}{\omega_{n,i}} \right) = TSSFAC \cdot \min_i \left( 2\sqrt{\frac{m_{eff,i}}{k_{eff,i}}} \right)
$$

- $m_{eff,i}$: birbirine bağlı iki kütlenin indirgenmiş kütlesi: $m_{eff} = \dfrac{m_1 m_2}{m_1+m_2}$
- $k_{eff,i}$: o anki (instantaneous) yay/temas sertliği — foam plato fazında düşük, bottom-out fazında çok yüksek olacağı için **her adımda yeniden hesaplanmalı**
- $TSSFAC$: güvenlik faktörü, tipik 0.6–0.9 (endüstri pratiği; siz 0.7 ile başlayıp kararlılığı test ederek ayarlayın)

**Neden şu an bu sizi etkiliyor:** Foam bottom-out veya seat-track yielding anında $k_{eff}$ aniden 1-2 mertebe artar. Sabit $dt=0.0001s$ bu anlarda kararsızlığa (enerji sapmasına) yol açabilir — Phase 10'daki enerji denetiminizin neden bazen "gürültülü" sonuç verebileceğinin teknik nedeni muhtemelen budur.

**Uygulama:** `lumped_mass_model.py` ana döngüsünde her adımın başında tüm aktif yay/temas elemanları için $k_{eff,i}$ hesaplayıp $dt_{crit}$'i güncelleyin; $dt = \min(dt_{crit}, dt_{max}=0.0001s)$ kullanın. Bu, Phase 10 planınızdaki "Enerji Korunumu Audit" maddesiyle (Bölüm 11'deki Madde 6) doğrudan birleşir — enerji denetimi artık *reaktif* (adım sonrası uyarı) değil, *proaktif* (adım öncesi $dt$ ayarı) hale gelir.

### 1.3 Mass Scaling (İsteğe Bağlı İyileştirme)

Eğer bazı segmentler (örn. ayak/foot) çok küçük kütleye sahipse, bunlar $dt_{crit}$'i gereksiz yere küçültebilir. Endüstri pratiği: bu segmentlere yapay kütle ekleyip gerçekçiliği bozmadan $dt_{crit}$'i büyük tutmak:

$$
m_i^{scaled} = \max\left(m_i,\ k_{eff,i}\cdot\left(\frac{dt_{target}}{2}\right)^2\right)
$$

**Dikkat:** Bu sadece kütlesi toplam sistem kütlesinin küçük bir yüzdesi olan segmentlere (ayak, el gibi) uygulanmalı — pelvis/torso gibi ana kütlelere asla uygulanmamalı, çünkü HIC/Nij gibi kriterler doğrudan bu kütlelerin ivmesine bağlı. Şu anki 9 segmentli modelinizde muhtemelen gerek yok (kütle dağılımınız zaten fazla küçük segment içermiyor), ama alt bacak zincirini (Bölüm 9, önceki doküman) eklerken ayak segmenti için değerlendirin.

### 1.4 Contact Search (Bucket Sort / Spatial Hashing) — Sizin İçin Gerekli mi?

Endüstriyel çözücülerde binlerce/milyonlarca FE düğümü arasında temas aramak $O(n^2)$ karşılaştırmayla imkansız olduğu için bucket-sort/spatial-hashing (uzayı hücrelere bölüp sadece komşu hücreleri karşılaştırma) kullanılır.

**Sizin sisteminiz için değerlendirme:** Lumped-mass modelinizde ~10-20 rijit segment ve bir avuç temas yüzeyi (foam, seatback, floor, olası kafa-çarpma engelleri) var. $O(n^2)$ karşılaştırma bu ölçekte **hesaplama maliyeti açısından önemsiz** (yüzlerce karşılaştırma/adım). Yani bucket-sort algoritmasını şu an eklemenizi **önermiyorum** — gereksiz karmaşıklık olur. Bunu not etmemin sebebi: eğer ileride koltuk yapısını (seat pan, leg, backrest) tam FE (shell/solid mesh) ile modellemeye geçerseniz (yani gerçek bir "hibrit MBD+FE" motoruna evrilirseniz), o zaman bu algoritma zorunlu hale gelir. Şimdilik mimari notu olarak saklayın, uygulamayın.

---

## 2. LS-DYNA Theory Manual — Temas Sertliği Formülasyonları

LS-DYNA üç temas sertliği hesaplama yöntemi sunar (`*CONTACT` kartındaki `SOFT` parametresi):

### 2.1 SOFT=0 — Standart Penalty (Malzeme Tabanlı)

$$
k_{contact} = \frac{K_{bulk} \cdot A_{segment}^2}{V_{segment}} \cdot SLSFAC
$$

Malzeme elastik sabitlerine ve eleman boyutlarına dayanır. Metal-metal temaslarda iyi çalışır ama **foam gibi çok yumuşak malzemelerde sertliği olduğundan düşük tahmin eder** — bu, sizin 3-fazlı foam modelinizin geçiş bölgelerinde neden hassas kalibrasyon istediğinin nedenidir.

### 2.2 SOFT=1 — Soft Constraint (Kütle/Zaman Adımı Tabanlı) — **Size Önerdiğim Yöntem**

$$
k_{contact} = SOFSCL \cdot \frac{m_{eff}}{dt^2}
$$

- $SOFSCL$: varsayılan 0.1 (dissimilar malzeme temaslarında 0.04–0.07'ye düşürülebilir — kararsızlık varsa)
- $m_{eff}$: temas eden iki segmentin indirgenmiş kütlesi
- $dt$: o anki simülasyon zaman adımı

**Neden bu sizin için SOFT=0'dan daha iyi:** Sizin foam-dummy, kafa-yapı gibi **çok farklı malzeme/kütle** temaslarınız var (yumuşak foam vs. sert kafa, sert bölme vs. yumuşak doku). SOFT=1 formülasyonu malzeme sabitlerinden bağımsız olduğu için bu tür "dissimilar" temaslarda **1-2 mertebe daha kararlı** sonuç verir — LS-DYNA dokümantasyonu bunu tam olarak sizin senaryonuza benzer durumlar için önerir (yumuşak/yoğun foam ile metal temasında).

**AeroSeat'e entegrasyon (`constitutive.py`):** Önceki dokümanınızdaki (Bölüm 1.3) kafa-çarpma temas modelinde sabit $k_c$ kalibrasyonu yerine bunu kullanın:

$$
k_c(t) = 0.1 \cdot \frac{m_{head} \cdot m_{obstacle,eff}}{(m_{head}+m_{obstacle,eff}) \cdot dt(t)^2}
$$

Bu, hem headform test verisi kalibrasyonuna olan bağımlılığınızı azaltır hem de sayısal kararlılığı otomatik garanti eder (çünkü $k_c$, $dt$ ile ters orantılı büyüdüğü için stabilite koşulunu kendiliğinden sağlar).

### 2.3 SOFT=2 — Segment-Based Penalty

SOFT=1'e benzer şekilde kütle/zaman adımı tabanlı sertlik hesaplar, ama temas arama algoritması nokta-yüzey yerine segment-segment karşılaştırması yapar; keskin köşelerde (örn. koltuk arkalığının üst kenarı, tepsi masası köşesi) daha güvenilirdir. Kafa-çarpma senaryonuzda engel geometrisi köşeli (tepsi masası, bölme kenarı) olduğu için, temas noktası tespiti yaparken düzlem-nokta yerine **segment-segment** (engelin sonlu bir dörtgen/üçgen yüzeyi olarak tanımlanması, kafanın küre olarak) formülasyonunu tercih edin — bu zaten önceki dokümanınızdaki Bölüm 1.2'de "bounding polygon" olarak önerdiğim şeyle aynı, burada sadece endüstri standardının da aynı yaklaşımı doğruladığını teyit ediyorum.

---

## 3. ANSYS Explicit Dynamics — Ek Not

ANSYS Explicit Dynamics arka planda ya LS-DYNA çözücüsünü ya da AUTODYN'i kullanır — yani teorik altyapısı Bölüm 2'dekiyle büyük ölçüde örtüşür. Farklı olan tek şey Euler-Lagrange kuplajı (akışkan-yapı etkileşimi, örn. airbag şişme dinamiği) — bu sizin şu anki kapsamınızda (koltuk-manken çarpışması, minder değil şişen airbag) gerekli değil. Bu bölümde ekstra bir formül önermiyorum; Bölüm 2 zaten kapsıyor.

---

## 4. MATLAB/Simulink (Simscape Multibody) — Mimari Ders

### 4.1 Bağıl Koordinat (Joint-Space) Formülasyonu

Sizin şu anki modeliniz muhtemelen her segmentin konumunu **global (mutlak) koordinatlarda** tutuyor ve eklemler arası bağlantıyı kısıt kuvvetleriyle (penalty spring) sağlıyor. Simscape Multibody (ve genel olarak robotik/çoklu-cisim literatüründeki "reduced coordinate" yaklaşımı) bunun yerine her eklemi **kendi bağıl serbestlik derecesiyle** (`Revolute Joint`, `Prismatic Joint`) tanımlar:

$$
\vec{r}_{child} = \vec{r}_{parent} + R(\theta_{joint}) \cdot \vec{r}_{offset}
$$

Yani her segmentin konumu, bir üst segmentin konumu + eklem açısının fonksiyonu olarak **hiyerarşik** tanımlanır (kinematic chain), global penalty kısıtına gerek kalmaz.

**Bu, sizin için ne değiştirir:** Şu anki Hunt-Crossley eklem modeliniz zaten penaltı tipi (kısıt kuvveti) bir yaklaşım — bunu değiştirmenizi önermiyorum, çünkü penalty yöntemi explicit zaman entegrasyonuyla (sizin `v+=a*dt` şemanız) doğal olarak uyumlu ve endüstri standardı zaten bu (LS-DYNA joint'leri de penalty tipi, bkz. Theory Manual Bölüm "Rigid Body Joints — Penalty types"). Asıl değerli olan şey **yazılım mimarisi**: Bölüm 9'daki (önceki doküman) alt bacak zincirini kodlarken her eklemi ayrı, yeniden kullanılabilir bir sınıf olarak tasarlayın:

```
class ArticulatedJoint:
    def __init__(self, k, c, n, parent_segment, child_segment, axis):
        ...
    def compute_reaction(self, theta, theta_dot):
        return k * theta**n + c * theta**n * max(0, theta_dot)  # Hunt-Crossley
```

Bu sayede `Hip`, `Knee`, `Ankle`, `Neck` eklemlerinin hepsi aynı sınıftan türetilir, farklı $k,c,n$ parametreleriyle. İleride 5F/95M gibi farklı manken boyutlarına geçtiğinizde (sadece parametre setini değiştirerek) yeniden kullanılabilir — bu, kod tekrarını önler ve kalibrasyon motorunuzun (`calibration_engine.py`) her eklemi aynı arayüzle optimize edebilmesini sağlar.

---

## 5. Virtual CRASH 6 — Neden Uygulanabilir Değil

Virtual CRASH, Kudlich-Slibar modeline dayalı **katı cisim, kapalı-form momentum/enerji dengesi** çözücüsüdür — araç-araç veya araç-yaya çarpışmalarında çarpışma öncesi/sonrası hızları geri hesaplamak için tasarlanmıştır (trafik kazası rekonstrüksiyonu). İçinde yolcu biyomekaniği, HIC/Nij hesabı, veya FE/MBD tipi zaman-serisi entegrasyonu yok. Alanınızla (uçak koltuğu sertifikasyonu, dinamik yolcu yaralanma kriterleri) metodolojik olarak örtüşmüyor. Buradan alınabilecek somut bir algoritma yok.

## 6. CEFA FAS — Neden Uygulanabilir Değil

CEFA FAS, uçuş kaydedici (FDR) verisinden 3D uçuş animasyonu üreten bir **görselleştirme/pilot eğitimi** yazılımıdır — yapısal/biyomekanik simülasyon yapmaz. "Aviation" ortak paydası dışında projenizle hiçbir teknik kesişimi yok.

---

## 7. Somut Kod Güncellemeleri — Özet Patch Listesi

| Dosya | Değişiklik | Kaynak |
|---|---|---|
| `lumped_mass_model.py` | Sabit `dt=0.0001s` → adaptif `dt_crit` hesaplama (Bölüm 1.2 formülü), her adım başında | OpenRadioss / Courant kriteri |
| `lumped_mass_model.py` | Ayak/el gibi küçük kütleli segmentlere opsiyonel mass scaling (Bölüm 1.3) | OpenRadioss |
| `constitutive.py` | Kafa-çarpma temas sertliği: sabit $k_c$ → SOFT=1 tipi kütle/dt tabanlı otomatik hesap (Bölüm 2.2) | LS-DYNA Theory Manual |
| `constitutive.py` | Engel geometrisi: nokta-yüzey yerine segment-segment (sonlu dörtgen/üçgen) temas tespiti (Bölüm 2.3) | LS-DYNA SOFT=2 |
| `lumped_mass_model.py` | Alt bacak eklemleri (`Hip/Knee/Ankle`) için ortak `ArticulatedJoint` sınıfı (Bölüm 4.1) | Simscape Multibody mimari deseni |
| — | Bucket-sort contact search | **Uygulanmıyor** — mevcut ölçekte gereksiz, sadece gelecekteki FE-hibrit senaryo için not edildi |

## 8. Güncellenmiş Öncelik Sırası (Phase 10/11 dokümanlarını ekler, değiştirir)

1. **Adaptif $dt_{crit}$** (Bölüm 1.2) — düşük risk, sayısal kararlılığı doğrudan iyileştirir, diğer her şeyin temelini güçlendirir
2. **SOFT=1 tipi kafa-çarpma temas sertliği** (Bölüm 2.2) — önceki dokümandaki Madde 1'i (sekonder kafa çarpması) güçlendirir
3. Önceki dokümandaki Madde 9 (alt bacak DOF) — artık `ArticulatedJoint` mimarisiyle (Bölüm 4.1)
4. Önceki dokümandaki geri kalan maddeler (kızak esnekliği, CFC filtre, submarining, korelasyon metodolojisi) — sıralama değişmedi

---

## Genel Değerlendirme

Beş araçtan ikisi (Virtual CRASH, CEFA FAS) alanınızla örtüşmüyor — bunları listeden çıkarabilirsiniz. Kalan üçü (OpenRadioss, LS-DYNA, Simscape) size **algoritma değil, çoğunlukla sayısal kararlılık ve mimari olgunluk** dersleri veriyor: adaptif zaman adımı ve kütle/zaman-adımı tabanlı temas sertliği, muhtemelen şu anki motorunuzun en büyük "gizli" kararsızlık kaynağı. Bunlar uygulandığında hem Phase 10'daki enerji denetiminiz daha anlamlı çalışacak hem de kafa-çarpma modeliniz (Phase 11 Madde 1) daha az kalibrasyona muhtaç, daha kendiliğinden kararlı olacak.
