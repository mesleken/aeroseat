# AeroSeat Phase 11 — Gelişmiş Gerçekçilik: Matematiksel Model Spesifikasyonu

Bu doküman, Phase 10 sonrası tespit edilen 9 açık maddenin her biri için **uygulanabilir matematiksel model** sunar. Amaç kod yazmak değil, kodu yazarken kullanacağınız denklemleri, parametre kaynaklarını ve entegrasyon noktalarını netleştirmek.

Notasyon, mevcut kod tabanınızla tutarlı tutulmuştur (`f_neck_z`, `a_head_z`, `dt = 0.0001 s`, semi-implicit Euler: önce `v += a*dt`, sonra `x += v*dt`).

---

## 1. Sekonder Kafa Çarpması / Flail Envelope Contact Modeli

**Neden kritik:** FAA 25.562 Test 2 (16G) senaryolarında HIC15'in en büyük kaynağı çoğu zaman restraint değil, kafanın öndeki yapıya (koltuk arkalığı, bölme, tepsi masası) çarpmasıdır. Şu anki modelde bu temas yok.

### 1.1 Flail Envelope Tanımı (FAA AC 25.562-1B)

Koltuk referans noktasına (SRP) göre, kafa ve dizin sled hareketi sırasında ulaşabileceği maksimum yörünge zarfı bir dizi yarıçap ile tanımlanır:

$$
\vec{r}_{head}(t) = \vec{r}_{SRP} + \vec{r}_{torso}(t) + \vec{r}_{neck \to head}(t)
$$

Bu, zaten çözücünüzün her adımda ürettiği bir çıktı (kafa CG pozisyonu). Yeni olan şey: sahnede tanımlı **statik engel geometrileri** (öndeki koltuk arkalığı düzlemi, bölme yüzeyi, tepsi masası köşesi) ile bu yörüngenin kesişip kesişmediğini her adımda kontrol etmek.

### 1.2 Temas Tespiti (Penetration Check)

Her engel yüzeyi bir düzlem + sınırlı alan (bounding polygon) olarak tanımlanır:

$$
\delta(t) = \vec{n} \cdot (\vec{r}_{obstacle,ref} - \vec{r}_{head}(t)) - R_{head}
$$

- $\vec{n}$: yüzey normali
- $R_{head}$: HIII-50M kafa yarıçapı (≈ 0.0813 m, sertifikasyon verisinden)
- $\delta > 0$ ise penetrasyon (temas) var.

### 1.3 Temas Kuvveti (Hunt-Crossley genişletmesi — zaten `constitutive.py`'de var, aynı fonksiyonu tekrar kullanın)

$$
F_{contact} = k_c \cdot \delta^{1.5} + c_c \cdot \delta^{1.5} \cdot \dot{\delta} \quad (\delta > 0 \text{ iken})
$$

**Parametre kaynağı:** $k_c$, $c_c$ jenerik değer olmamalı — yüzey tipine göre (sert plastik tepsi masası, yumuşak koltuk arkalığı döşemesi, sert bölme) FAA TSO onaylı headform impact test verilerinden (14 CFR Part 25 Appendix headform drop testleri, tipik enerji 15-25 J) geri hesaplanmalı. Yöntem: bilinen bir düşme enerjisi $E = \frac{1}{2}m_{headform}v^2$ ve test edilen malzemenin HIC/G-max sonucundan, force-deflection eğrisinin alanını enerji ile eşleyip $k_c$'yi fit edin.

### 1.4 Enjeksiyon Noktası

`lumped_mass_model.py` içinde kafa ivme integrasyonuna eklenir:

$$
a_{head,z}^{total} = a_{head,z}^{restraint} + \frac{F_{contact,z}}{m_{head}}
$$

HIC15 hesabı zaten toplam $a_{res}(t)$ üzerinden çalıştığı için `injury_metrics.py`'de değişiklik gerekmez — sadece girdi sinyali artık temas etkisini içerecek.

### 1.5 Test Stratejisi

`test_phase11_head_strike.py`: bilinen bir mesafede (örn. 32 inç pitch) sabit engel tanımlayıp, temassız/temaslı iki koşuyu karşılaştıran regresyon testi; HIC'in temaslı durumda anlamlı şekilde artması beklenir.

---

## 2. Fiziksel Doğrulama / Korelasyon Metodolojisi (ISO/TS 18571 tarzı)

**Neden kritik:** Şu anki "koridor içine düştü mü" (range check) yöntemi zaman-serisi şeklini değerlendirmiyor. ISO/TS 18571, dört alt-metriğin ağırlıklı toplamıdır: Corridor (Z), Phase (P), Magnitude (M), Slope/Shape (S).

$$
R = w_Z \cdot Z + w_P \cdot E_P + w_M \cdot E_M + w_S \cdot E_S
$$

Ağırlıkları ($w_Z, w_P, w_M, w_S$) standardın kendisinden (ISO/TS 18571:2014/2024) alıp `correlation_engine.py`'de config olarak tanımlayın — burada uydurmayacağım, çünkü sertifikasyon bağlamında yanlış katsayı kullanmak yanıltıcı olur. Ama alt-metriklerin matematiği aşağıdaki gibi kurulur:

### 2.1 Corridor Rating (Z)

Referans sinyal $T(t)$ (gerçek test verisi) etrafında iç ve dış koridor tanımlanır:

$$
T_{norm} = \max_t |T(t)| \quad \text{(değerlendirme aralığında)}
$$
$$
\text{İç koridor:} \quad T(t) \pm a_0 \cdot T_{norm}, \quad a_0 = 0.05
$$
$$
\text{Dış koridor:} \quad T(t) \pm b_0 \cdot T_{norm}, \quad b_0 = 0.50
$$

Her zaman noktasında simülasyon sinyali $S(t)$ için puan:

$$
z(t) = \begin{cases}
1 & |S(t) - T(t)| \le a_0 T_{norm} \\
0 & |S(t) - T(t)| \ge b_0 T_{norm} \\
\left(1 - \dfrac{|S(t)-T(t)| - a_0 T_{norm}}{(b_0 - a_0) T_{norm}}\right)^{k_Z} & \text{aradaysa}, \quad k_Z = 2
\end{cases}
$$

$$
Z = \frac{1}{N}\sum_{t} z(t)
$$

### 2.2 Phase Rating (E_P)

Çapraz korelasyon ile faz kayması bulunur:

$$
\tau^* = \arg\max_{\tau} \left[ \frac{\sum_t S(t)\,T(t+\tau)}{\sqrt{\sum_t S(t)^2 \sum_t T(t+\tau)^2}} \right]
$$

$$
E_P = \max\left(0,\ 1 - \frac{|\tau^*|}{\tau_{max}}\right)
$$

$\tau_{max}$ genelde sinyal süresinin belli bir yüzdesi (ör. %20) olarak tanımlanır.

### 2.3 Magnitude Rating (E_M)

$$
E_M = \max\left(0,\ 1 - \frac{\left|\int S(t)\,dt - \int T(t)\,dt\right|}{\int |T(t)|\,dt}\right)
$$

### 2.4 Slope/Shape Rating (E_S)

Türev (şekil) uyumu, normalize edilmiş korelasyon katsayısı üzerinden:

$$
E_S = \frac{\sum_t (\dot S(t) - \bar{\dot S})(\dot T(t) - \bar{\dot T})}{\sqrt{\sum_t (\dot S(t)-\bar{\dot S})^2}\sqrt{\sum_t (\dot T(t)-\bar{\dot T})^2}}
$$

(negatifse 0'a kırpılır)

### 2.5 Golden Dataset Kaynağı

Bu metodoloji yalnızca gerçek zaman-serisi test verisi ile anlamlıdır. Kaynak olarak: FAA William J. Hughes Technical Center yayınlanmış sled test raporları, NIAR (National Institute for Aviation Research) açık literatür verileri, veya kendi OTEST deneyiminizden erişebileceğiniz gerçek 14g/16g dummy kanal verileri (baş ivmesi, boyun yükü, lumbar yük zaman-serileri) kullanılmalı. Bu veri olmadan R hesaplanamaz — bu, projenin en büyük veri açığı.

---

## 3. Kızak/Ray Esnekliği ve Taban Deformasyonu (AS8049E 10° Warpage)

### 3.1 Statik Ön-Eğrilik (Pre-Test Warpage)

Test öncesi ray/taban, sled koordinat sistemine göre sabit bir açısal ofset ile başlatılır — bu bir **başlangıç koşulu**, dinamik değil:

$$
\theta_{pitch,0} = \pm 10°, \quad \theta_{roll,0} = \pm 10°
$$

Koltuk-kızak bağlantı noktalarının başlangıç pozisyonu bu açılarla dönüştürülür (Tait-Bryan rotasyon matrisi zaten `pulse_library.py`'de mevcut — aynı matrisi statik ofset için de kullanın):

$$
\vec{r}_{mount,i}^{warped} = R(\theta_{pitch,0}, \theta_{roll,0}, 0) \cdot \vec{r}_{mount,i}^{nominal}
$$

Dört köşe bağlantı noktası için ayrı ayrı uygulanmalı (koltuk ayakları farklı yüksekliklerde başlar).

### 3.2 Dinamik Taban Esnekliği (Floor Elastic Layer)

Kızak ile "zemin" (gerçek uçak gövdesi) arasına ikinci bir yay-damper katmanı eklenir:

$$
F_{floor,z} = k_{floor} \cdot (z_{sled,base} - z_{sled}) + c_{floor} \cdot (\dot{z}_{base} - \dot{z}_{sled})
$$

$k_{floor}$, $c_{floor}$ tipik kompozit/alüminyum uçak taban paneli rijitliğinden gelir (mertebe: $k_{floor} \sim 10^6$–$10^7$ N/m; kesin değer üreticinin taban paneli test verisinden kalibre edilmeli).

### 3.3 Lumbar Yüküne Etkisi

Bu katman özellikle 14G testinde önemlidir çünkü pelvis-minder kuvvet transferi taban rijitliğine duyarlıdır. `lumbar_load` hesabına değişiklik gerekmez — sadece `f_spine_z` girdisi artık esnek taban etkisini taşır.

---

## 4. Occipital Condyle Moment Düzeltmesi — ✅ Zaten Yapıldı

(Referans için: $M_{y,OC} = M_{y,cell} - d_{oc}\cdot F_x$, $d_{oc}=0.01778$ m. Değişiklik gerekmiyor.)

---

## 5. SAE J211-1 CFC Filtre Düzeltmesi (-4dB Attenuation)

**Sorun:** `filtfilt` (forward-backward) 2. derece Butterworth uyguladığınızda etkin derece 4 olur ve $f_c$'de zayıflama -6dB'ye çıkar; SAE J211-1 analog CFC filtre -4dB spesifikasyonu ister.

### 5.1 SAE J211-1 Appendix C Dijital Filtre Katsayıları

Analog CFC filtresinin dijital eşdeğeri, tek yönlü (forward-only, faz kaymalı ama zaten iki kez ileri-geri uygulanarak faz düzeltilen) 2. derece Butterworth low-pass olarak tanımlanır, kesim frekansı:

$$
f_{cut} = \frac{2}{3}\cdot CFC \times 2.0 \quad \text{(SAE J211 CFC sınıfına göre — CFC1000 için } f_{cut}\approx 1650\text{ Hz)}
$$

Standardın verdiği tam prosedür: örnekleme frekansı $f_s$ biliniyorken

$$
\omega_d = \tan\left(\frac{\pi f_c}{f_s}\right), \quad f_c = CFC \times 1.25 \text{ (SAE J211-1 Bölüm 2'deki tanım)}
$$

katsayılar:
$$
a_0 = \frac{\omega_d^2}{1+\sqrt{2}\omega_d+\omega_d^2}, \quad a_1=2a_0, \quad a_2=a_0
$$
$$
b_1 = \frac{2(\omega_d^2-1)}{1+\sqrt{2}\omega_d+\omega_d^2}, \quad b_2=\frac{1-\sqrt{2}\omega_d+\omega_d^2}{1+\sqrt{2}\omega_d+\omega_d^2}
$$

Filtre: $y_n = a_0 x_n + a_1 x_{n-1} + a_2 x_{n-2} - b_1 y_{n-1} - b_2 y_{n-2}$

**Not:** Bu katsayı formülünü kodlamadan önce SAE J211-1 Appendix C'nin güncel baskısıyla birebir teyit edin — standardın kendi doküman numarası ve tam katsayı tablosu telifli olduğu için burada yaklaşık/genel formu veriyorum; kritik olan, tek geçişli (`lfilter`, `filtfilt` değil) uygulama ile hedef -4dB zayıflamayı tutturmaktır. Doğrulama: birim adım fonksiyonuna filtre uygulayıp $f_c$'deki gerçek zayıflamayı FFT ile ölçen bir unit test yazın (`test_cfc_filter_attenuation.py`).

---

## 6. Enerji Korunumu Denetiminin Ana Çözücüye Entegrasyonu

### 6.1 Enerji Bilançosu

Her zaman adımında:

$$
E_{kinetic}(t) = \sum_i \frac{1}{2} m_i \|\vec{v}_i(t)\|^2 + \frac{1}{2} I_i \omega_i(t)^2
$$

$$
E_{potential}(t) = \sum_i m_i g \cdot z_i(t)
$$

$$
E_{dissipated}(t) = E_{dissipated}(t-dt) + \sum_j F_{damper,j}\cdot v_{rel,j}\cdot dt + \sum_j E_{plastic,j}
$$

($E_{plastic}$: yay-sönümleyici değil, kalıcı plastik deformasyon yapan elemanların — seat track yielding, backrest hinge — bu adımda yuttuğu enerji)

$$
E_{input}(t) = E_{kinetic}(0) + E_{potential}(0) + \int_0^t \vec{F}_{sled}\cdot \vec{v}_{sled}\,dt
$$

### 6.2 Denetim Koşulu

$$
\epsilon(t) = \frac{\left| \big(E_{kinetic}(t)+E_{potential}(t)+E_{dissipated}(t)\big) - E_{input}(t) \right|}{E_{input}(t)}
$$

`lumped_mass_model.py` ana döngüsünde her 100 adımda bir (veya `EnergyMomentumAuditEngine` her çağrıldığında):

```
if epsilon(t) > 0.001:  # %0.1
    log_warning / raise SimulationIntegrityWarning
```

Bu, stiff temas olaylarında (foam bottom-out, ani plastik akma) sayısal patlamayı erken yakalar — dt=0.0001s'nin çok stiff bir olay için yetersiz kaldığı anları tespit eder. İsterseniz burada bir **adaptif alt-adımlama (substepping)** tetikleyicisi de kurabilirsiniz: $\epsilon(t)$ eşiği aşarsa o adımı $dt/10$ ile tekrar çözün.

---

## 7. Submarining Fiziksel Modeli

**Mevcut sezgisel formül yerine**, gerçek mekanizma: kucak kemerinin iliak kretten kayıp karın bölgesine girmesi, pelvis pitch açısı ve kemer dikey kuvvet bileşeninin fonksiyonudur.

### 7.1 Pelvis-Kemer Geometrik Bağıntı

Kucak kemeri kuvvetinin pelvis üzerindeki etkin açısı, pelvis pitch açısı $\theta_{pelvis}(t)$ ile değişir:

$$
\alpha_{belt}(t) = \alpha_{belt,0} - \theta_{pelvis}(t)
$$

$\alpha_{belt,0}$: statik oturuşta kemer-pelvis açısı (BeltAnchorGeometry'den, `lap_anchor` ve pelvis H-point arasındaki vektörden hesaplanır).

### 7.2 Kemer Kuvvetinin Dikey/Yatay Ayrışımı

$$
F_{belt,vertical} = F_{lap}\sin(\alpha_{belt}(t)), \quad F_{belt,horizontal}=F_{lap}\cos(\alpha_{belt}(t))
$$

### 7.3 Submarining Risk Endeksi (Fiziksel Temelli)

Submarining, kemerin iliak kret üzerinde "tutunma" sağlayamayıp öne kaymasıyla olur — bu, dikey bileşenin belirli bir eşiğin altına düşmesi ve pelvis öne kayma hızının (relative x-velocity) yüksek olmasıyla karakterize edilir:

$$
SI(t) = \frac{1}{F_{belt,vertical}(t) + \epsilon_0} \cdot \max(0, \dot{x}_{pelvis,rel}(t)) \cdot \mathbb{1}[\alpha_{belt}(t) < \alpha_{crit}]
$$

- $\alpha_{crit}$: iliak kret geometrisinden gelen kritik açı (~ 30°-45°, dokümanınızdaki değerle tutarlı)
- $\epsilon_0$: sıfıra bölmeyi önleyen küçük sabit

$SI$ eşik değerinin üzerine çıktığı an, submarining başlangıcı olarak işaretlenir (binary event), sürekli bir "risk skoru" değil — bu, gerçek biyomekanik literatürdeki (örn. Reed & Ebert-Hamilton pelvis-belt etkileşim çalışmaları) yaklaşımla daha tutarlıdır.

---

## 8. Kemer Ankraj Geometrisinin CAD'den Otomatik Çıkarımı

Bu bir "matematiksel model" değil, bir **geometri çıkarım algoritması** — ama aynı derecede kritik, çünkü 3D kemer vektör ayrıştırmanız şu an sabit varsayılan koordinatlarla çalışıyor.

### 8.1 Yaklaşım

STEP dosyasında D-Ring, toka ve kucak ankraj noktaları genelde adlandırılmış referans noktaları (datum points) veya küçük silindirik/dairesel yüzeyler (cıvata delikleri) olarak bulunur.

$$
\vec{r}_{anchor} = \frac{1}{|F|}\sum_{f \in F} \vec{c}_f
$$

- $F$: kullanıcı tarafından (veya isim eşleştirmesiyle: "D_RING", "BUCKLE_ANCHOR", "LAP_ANCHOR_L/R" gibi katman/isim konvansiyonuyla) seçilen yüzey kümesi
- $\vec{c}_f$: her yüzeyin centroid'i (STEP kernel'inizin — örn. `python-occ` veya `pythonOCC` — `BRepGProp` fonksiyonlarıyla doğrudan hesaplanır)

### 8.2 Pratik Öneri

Tam otomatik tanıma (STEP dosyasındaki isimlendirme standart değilse) yerine, kısa vadede **yarı-otomatik** bir akış kurun: müşteri CAD yükler → 3D viewer'da (zaten `ThreeSeatViewer.jsx` var) mühendis 4 ankraj noktasına tıklar → koordinatlar `BeltAnchorGeometry`'ye otomatik yazılır. Bu, tam otomatik feature-recognition'dan çok daha az riskli ve MVP için yeterli; feature-recognition'ı Phase 12+'ya bırakabilirsiniz.

---

## 9. Alt Bacak Segmentlerinin Gerçek Çok-Cisim Eklemi Olarak Modellenmesi

**Sorun:** Şu an femur/tibia kütleleri toplam kütle dağılımına eklendi ama femur yükü hâlâ "pelvis-minder kuvveti" üzerinden türetiliyor — bağımsız serbestlik derecesi (DOF) yok.

### 9.1 Önerilen Zincir Yapısı

$$
\text{Pelvis} \xrightarrow{\text{Hip Joint (rotasyonel + öteleme)}} \text{Femur} \xrightarrow{\text{Knee Joint}} \text{Tibia} \xrightarrow{\text{Ankle}} \text{Foot} \xrightarrow{\text{Floor Contact}}
$$

Her segment için kendi Newton-Euler denklemi:

$$
m_{femur}\ddot{\vec{r}}_{femur} = \vec{F}_{hip} + \vec{F}_{knee} + m_{femur}\vec{g}
$$

$$
I_{femur}\dot{\omega}_{femur} = \vec{M}_{hip} + \vec{M}_{knee}
$$

### 9.2 Diz Eklemi (Hunt-Crossley ile tutarlı, aynı fonksiyon yeniden kullanılabilir)

$$
M_{knee}(t) = k_{knee}\theta_{knee}^{1.5} + c_{knee}\theta_{knee}^{1.5}\dot\theta_{knee}
$$

$k_{knee}, c_{knee}$ Hybrid III diz sertifikasyon verisinden (knee pendulum test corridor) kalibre edilmeli — Bölüm 10'daki genel kalibrasyon prosedürü aynen uygulanır.

### 9.3 Ayak-Zemin Teması (14G Testinde Kritik)

$$
F_{floor,foot,z} = \begin{cases} k_{floor,foot}\cdot\delta_{foot} + c_{floor,foot}\cdot\dot\delta_{foot} & \delta_{foot} > 0 \\ 0 & \text{aksi halde} \end{cases}
$$

$$
F_{friction,x} = -\mu \cdot F_{floor,foot,z} \cdot \text{sign}(\dot x_{foot})
$$

### 9.4 Femur Yükü — Artık Türetilmiş Değil, Doğrudan Ölçülen

$$
F_{femur,axial}(t) = \vec{F}_{knee}(t)\cdot \hat{e}_{femur}(t)
$$

Bu, mevcut `femur_dynamic_n` formülünüzün (Phase 9'da düzeltilen 0.5·(0.35·f_cushion_z + 0.20·|f_spine_z|) sezgisel formülü) yerini alır — artık gerçek bir eklem reaksiyon kuvveti.

### 9.5 Kalibrasyon Prosedürü (Hunt-Crossley parametreleri için — hem boyun hem diz için genel)

$$
\min_{k,c,n} \sum_t \left(M_{model}(t;k,c,n) - M_{cert}(t)\right)^2
$$

`calibration_engine.py`'de zaten Nelder-Mead optimizasyon motorunuz var — bu amaç fonksiyonunu (boyun/diz sertifikasyon pendulum test verisine karşı) aynı motora ekleyin. $M_{cert}(t)$: NHTSA/Humanetics'in yayınladığı Hybrid III bileşen sertifikasyon test corridor verisi.

---

## Özet: Uygulama Sırası ve Bağımlılıklar

| # | Madde | Bağımlı Olduğu | Yeni Dosya/Değişiklik |
|---|---|---|---|
| 1 | Sekonder kafa çarpması | `constitutive.py` (Hunt-Crossley zaten var) | `contact_geometry.py` (yeni) |
| 2 | Korelasyon metodolojisi | Golden dataset (harici veri gerekli) | `correlation_engine.py` (yeni) |
| 3 | Kızak/ray esnekliği | `pulse_library.py` (rotasyon matrisi zaten var) | `lumped_mass_model.py` |
| 5 | CFC filtre düzeltmesi | — | `signal_processing.py` |
| 6 | Enerji denetimi entegrasyonu | `EnergyMomentumAuditEngine` (zaten var) | `lumped_mass_model.py` |
| 7 | Submarining fiziksel model | `BeltAnchorGeometry` (zaten var) | `injury_metrics.py` |
| 8 | Ankraj CAD çıkarımı | STEP parser | `geometry_extraction.py` (yeni) |
| 9 | Alt bacak DOF | Madde 8 (diz kalibrasyonu için) | `lumped_mass_model.py` (büyük değişiklik) |

**Önerilen sıra:** 5 → 6 (düşük risk, hızlı kazanç) → 1 → 3 → 9 → 7 → 8 → 2 (2 numaralı madde, golden dataset'e erişim sağlanana kadar zaten uygulanamaz, o yüzden veri tedarikini paralel yürütün).
