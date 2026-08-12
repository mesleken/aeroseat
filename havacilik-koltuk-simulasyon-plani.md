# Havacılık Koltuğu Sertifikasyon Simülasyon Platformu — Kapsamlı Ürün ve Teknik Plan

**Hazırlanma amacı:** TCI, Airbus, Boeing gibi havacılık üreticilerine koltuk tedarik eden firmaların, 14g/16g dinamik sertifikasyon testlerini fiziksel test öncesinde sanal ortamda simüle edebilmesini sağlayan, uçtan uca bir yazılım platformu.

**Bu belge şunu hedefliyor:** Mühendislik veya yazılım geçmişi olmayan biri bile okuyup projeyi anlayabilsin, aynı zamanda geliştirici ekip için de somut bir mimari ve yol haritası bıraksın. Bu yüzden her teknik bölümün önce "sade anlatım", sonra "teknik detay" kutusu var.

---

## 1. Yönetici Özeti

Bugün bir uçak koltuğu üreticisi, koltuğunu sertifikalandırmak için fiziksel bir 14g veya 16g çarpma testi yaptırıyor (senin OTEST'te gördüğün gibi). Bu testler pahalı, yavaş ve genelde **tek seferlik** — koltuk prototipi test sırasında hasar görüyor. Eğer tasarım testten geçemezse (fail), koltuk yeniden tasarlanıp yeni bir prototip üretilip test tekrarlanmak zorunda. Bu hem zaman hem para kaybı.

Bizim kuracağımız platform, bu testi koltuk **daha üretilmeden**, bilgisayar ortamında, gerçeğe çok yakın şekilde önceden çalıştırıyor. Müşteri bize koltuğun 3D tasarımını (CAD modeli) ve test edilecek pulse (çarpma sırasında koltuğa etki eden ivme eğrisi) verisini gönderiyor. Biz bu ikisini birleştirip, üzerine bir "dummy" (test mankeni) yerleştirip, gerçek testte olacakları bilgisayarda simüle ediyoruz. Sonuçta müşteriye şunları veriyoruz:

- Koltuğun hangi noktasında ne kadar kuvvet oluştuğu
- Dummy'nin baş, sırt, femur (bacak) bölgelerinde oluşan yükler ve bunların FAA/EASA limitlerine göre **geçti/kaldı (pass/fail)** durumu
- Koltuğun nereye doğru, kaç derece eğildiği/katlandığı, hangi parçanın ne kadar deforme olduğu
- Bunların hepsinin bir **video/animasyon** olarak görselleştirilmesi

Bu, müşterinin fiziksel teste girmeden önce tasarımını defalarca "sanal olarak" deneyip düzeltebilmesini sağlıyor. Sertifikasyonun kendisi (yasal olarak FAA/EASA'ya sunulacak resmi kanıt) yine fiziksel test ile yapılacak — bizim ürünümüz **test öncesi tasarım/geliştirme aracı**, testin kendisinin yerine geçen bir şey değil. Bu, hem daha gerçekçi bir hedef hem de düzenleyici (regülasyon) açısından çok daha az riskli bir konumlandırma.

---

## 2. Sertifikasyon Bağlamının Sade Açıklaması

Havacılıkta koltuk testleri şu kurallara göre yapılıyor:

- **FAA (Amerika):** 14 CFR § 25.562 — "Emergency landing dynamic conditions"
- **EASA (Avrupa):** CS-25.562 — FAA'ninkine çok benzer
- **Uygulama detayları:** SAE AS8049 standardı (dummy tipi, pulse şekli, ölçüm noktaları, kabul kriterleri hep burada tarif edilir)

Testte iki ayrı senaryo (pulse) var:

1. **16g yatay (forward) pulse** — koltuk öne doğru şiddetli bir yavaşlamaya maruz kalıyor (uçağın aniden durması gibi)
2. **14g dikey (vertical) pulse** — koltuk aşağı yönlü şiddetli bir darbeye maruz kalıyor (sert iniş gibi)

Her ikisinde de üzerine oturtulan bir **Hybrid III test mankeni (dummy)** üzerinden ölçülüyor:

| Kriter | Ne ölçer | Basit anlamı | Limit (özet) |
|---|---|---|---|
| **HIC (Head Injury Criterion)** | Baş üzerindeki ivme, zaman içinde | Baş bir yere çarparsa ne kadar sert çarptığı | HIC ≤ 1000 |
| **Nij (Neck Injury Criterion)** | Boyundaki eksenel kuvvet + eğilme momenti | Boynun ne kadar zorlandığı | Nij ≤ 1.0 |
| **Femur Load** | Uyluk kemiğindeki eksenel yük | Diz/bacağın önündeki panele ne kadar sert çarptığı | ≤ 2250 lb (~10 kN) |
| **Lumbar Load** | Bel omurgasındaki eksenel yük | Dikey (14g) testte belin ne kadar zorlandığı | ≤ 1500 lb (~6.67 kN) |
| **Head/Knee Excursion** | Başın/dizin öne doğru ne kadar hareket ettiği | Öndeki objeye (panel, koltuk arkası) çarpıp çarpmayacağı | Genelde tanımlı bir sınır çizgisini geçmemeli |
| **Koltuk bütünlüğü** | Koltuğun kendisi kopmamalı, dummy koltuktan ayrılmamalı | Yapısal göçme olmamalı | Pass/Fail (kırılma yok) |

Senin istediğin tüm çıktılar (headrest/backrest, Nij, HIC, femur load, deformasyon, kırılma açısı, pass/fail) zaten bu resmi kriterlerin karşılığı — yani platform doğrudan bu tabloyu otomatik üretecek.

---

## 3. Motor Yaklaşımı: Kendi Solver'ımızı mı Yazalım, Var Olanı mı Otomatikleştirelim?

Bu, projenin en kritik kararı. İki yaklaşımı karşılaştıralım:

### Seçenek A — Sıfırdan kendi fizik motorumuzu (solver) yazmak

**Ne demek:** Malzemenin nasıl gerileceğini, parçaların birbirine nasıl çarpacağını, koltuğun nasıl kırılacağını hesaplayan matematik motorunu (LS-DYNA'nın yaptığı işi) kendimiz kod olarak yazmak.

| Artı | Eksi |
|---|---|
| Tam kontrol — istediğimiz her özelliği ekleyebiliriz | **10+ yıl ve onlarca uzman mühendis** gerektiren bir mühendislik problemi (LS-DYNA/RADIOSS'un arkasında 40 yıllık geliştirme var) |
| Lisans maliyeti yok (uzun vadede) | Doğrulama (validasyon) çok zor — sonuçların gerçek testle örtüştüğünü kanıtlamak yıllar sürer |
| Ürünü tamamen kendi IP'miz yapar | Sertifikasyon otoritelerinin (FAA/EASA) ve müşterilerin güvenini kazanmak neredeyse imkansız kadar zor olur ("bu senin yazdığın motor doğru mu?") |
| | Çok yüksek başlangıç riski — startup bu aşamada muhtemelen tükenir |

### Seçenek B — Var olan, sektörde zaten güvenilen solver'ları (LS-DYNA, RADIOSS) otomatikleştiren bir katman kurmak

**Ne demek:** Fizik hesaplamasını (asıl "çarpışma matematiği") halihazırda havacılık/otomotiv sektöründe **20-30 yıldır kullanılan, güvenilirliği kanıtlanmış** programlara (LS-DYNA gibi) bırakmak. Bizim yazılımımız bu motoru "kullanıcı dostu" hale getiren, koltuk sertifikasyonuna özel bir arayüz/otomasyon katmanı olur: CAD modelini otomatik hazırlar, dummy'yi otomatik yerleştirir, pulse'ı otomatik uygular, motoru arka planda çalıştırır, sonuçları otomatik okuyup pass/fail raporuna çevirir.

| Artı | Eksi |
|---|---|
| Fizik motoru zaten sektörde güvenilir ve doğrulanmış — güven sorunu yok | LS-DYNA/RADIOSS lisans maliyeti var (yıllık, kullanıcı/çekirdek başına ciddi bedel) |
| Çok daha hızlı pazara çıkış (aylar, yıllar değil) | Motorun "içine" giremeyiz — kara kutu olarak kullanırız, sadece dışarıdan yönetiriz |
| Bizim asıl değerimiz "otomasyon + kullanıcı deneyimi + sertifikasyon zekası" olur, ki startup için çok daha gerçekçi bir hedef | Üçüncü taraf yazılıma bağımlılık (fiyat artışı, lisans şartları riski) |
| Sertifikasyon otoriteleri ve büyük müşteriler (Airbus, Boeing) zaten bu motorları tanıyor, güveniyor | |

### Tavsiye edilen yol: **Hibrit strateji**

1. **Faz 1-2 (ilk 12-18 ay):** Seçenek B ile başla. LS-DYNA (veya RADIOSS) üzerine otomasyon katmanı kur. Bu, gelir getiren, satılabilir bir ürünü hızlıca ortaya çıkarır.
2. **Faz 3+ (ürün olgunlaştıkça, gelir/yatırım geldikçe):** Platformun kendi içinde, **belirli, dar kapsamlı** hesaplama modülleri geliştirmeye başla (örneğin sadece dummy-koltuk temas kuvveti hesaplayan basitleştirilmiş bir modül, ya da hızlı ön-tasarım taraması için basitleştirilmiş "hızlı tahmin" motoru). Tam bir genel-amaçlı FE solver'ı asla hedef olmasın — bu, dünyada elle sayılı şirketin (LSTC/Ansys, Altair, Dassault) yapabildiği bir iş.

Bu şekilde hem hızlı başlarsın hem de zamanla kendi teknik IP'ni biriktirirsin, ama şirketi bitirecek bir "önce motor yaz" tuzağına düşmezsin.

---

## 4. Matematiksel Model — Sistemin Arka Planda Ne Hesapladığı

Bu bölüm hem sade anlatım hem teknik formülleri içeriyor.

### 4.1 Genel fikir: "Zamanı çok küçük dilimlere bölüp, her dilimde ne olduğunu hesapla"

Bir çarpışma testi gerçekte 0.1-0.3 saniye gibi çok kısa bir süre. Bilgisayar bunu tek seferde çözemez; zamanı **binde bir, on binde bir saniyelik** dilimlere böler (buna "time step" denir) ve her dilimde:

1. Koltuğun her noktasına o an ne kadar kuvvet etki ediyor?
2. Bu kuvvet, o noktayı ne kadar hareket ettirir / deforme eder?
3. Yeni pozisyonda malzeme kırıldı mı, eğildi mi, hâlâ sağlam mı?
4. Bir sonraki çok küçük zaman dilimine geç, tekrarla.

Buna **"explicit dinamik sonlu elemanlar analizi" (explicit dynamic FEA)** deniyor — LS-DYNA'nın ve tüm crash-test yazılımlarının temeli budur.

**Teknik detay kutusu:**
> Temel denklem, Newton'un F = m·a yasasının, koltuğun binlerce küçük parçasına (eleman/node) uygulanmış hali:
>
> `M · a(t) = F_ext(t) − F_int(t)`
>
> - `M`: kütle matrisi (koltuğun her noktasının kütlesi)
> - `a(t)`: o andaki ivme
> - `F_ext(t)`: dışarıdan gelen kuvvet (pulse'ın uyguladığı ivme × kütle)
> - `F_int(t)`: malzemenin kendi iç direncinden (esneme, gerilme) doğan kuvvet
>
> Zaman ilerletme yöntemi genelde **"merkezi fark" (central difference)** yöntemidir:
>
> `v(t+Δt/2) = v(t−Δt/2) + a(t)·Δt`
> `x(t+Δt) = x(t) + v(t+Δt/2)·Δt`
>
> Bu yöntemin "explicit" (açık) olmasının sebebi: bir sonraki adımı hesaplamak için karmaşık denklem sistemleri çözmeye gerek olmaması — çok hızlı ama `Δt` (zaman adımı) çok küçük tutulmak zorunda (genelde 10⁻⁶ - 10⁻⁷ saniye), yoksa çözüm kararsızlaşır (patlar). Bu yüzden 0.2 saniyelik bir test bile bilgisayarda yüz binlerce adım gerektirir.

### 4.2 Koltuk malzemesinin "davranışı" nasıl tanımlanır?

Koltuk metal (alüminyum, çelik) ve/veya kompozit (karbon fiber) parçalardan oluşur. Her malzemenin bir "ne kadar zorlarsan o kadar esner, şu noktadan sonra kalıcı şekil değiştirir, şu noktadan sonra kopar" davranışı tanımlanmalı.

- **Metal parçalar için:** Elasto-plastik malzeme modeli — belirli bir noktaya kadar esner ve eski haline döner (elastik), o noktadan sonra kalıcı şekil değiştirir (plastik), sonunda kopar.
- **Kompozit (karbon fiber) parçalar için:** Daha karmaşık — fiber yönüne göre farklı davranır, "delaminasyon" denen katman ayrılması olabilir. Bunun için Hashin veya Puck gibi özel "hasar kriterleri" kullanılır.

**Teknik detay kutusu:**
> Metal için tipik model: **bilinear/multilinear isotropic hardening plasticity** — akma noktasına (`σ_y`) kadar Hooke yasası (`σ = E·ε`), sonrasında pekleşme eğrisi (`σ = σ_y + K·ε_p^n`). LS-DYNA'da bu `*MAT_024 (Piecewise Linear Plasticity)` gibi hazır malzeme kartlarıyla tanımlanır — biz sıfırdan yazmayız, doğru malzeme kartını ve doğru katsayıları (gerilme-gerinim eğrisi, kopma gerinimi) seçip motora besleriz.
> Kompozit için: `*MAT_054/055 (Composite Damage)` gibi kartlar, Chang-Chang veya Hashin hasar kriterleriyle fiber kopması / matris çatlaması / delaminasyonu ayrı ayrı modeller.

### 4.3 Pulse (çarpma eğrisi) nasıl tanımlanır?

Müşteri bize "16g forward pulse" dediğinde, bu aslında zamana karşı ivme grafiği anlamına gelir — genelde üçgen (triangular) veya trapez şeklinde, AS8049 standardında tarif edilen tolerans bandı içinde olması gereken bir eğri.

**Teknik detay kutusu:**
> Standart 16g pulse: tepe değeri 16g'ye ~0.08-0.09 saniyede ulaşan, belirli bir tolerans koridoru (upper/lower bound eğrileri) içinde kalması gereken bir ivme-zaman eğrisi. Bu eğri, koltuğun sabitlendiği rayın/tabanın (sled) hareketine "boundary condition" olarak uygulanır — yani koltuk gerçek testteki gibi sanki bir "sled" üzerindeymiş gibi bu ivmeye maruz bırakılır.

### 4.4 Dummy (test mankeni) nasıl modellenir?

Gerçek Hybrid III dummy'nin, sertifikalı bir "FE dummy modeli" (dijital ikizi) vardır — bunlar Humanetics/LSTC gibi firmalardan lisanslanır. Bu dummy modelleri, gerçek dummy'nin eklemlerini, kütle dağılımını, sensörlerini (baş, boyun, göğüs, femur, bel) birebir taklit eder. Biz bu hazır, sertifikalı dijital dummy'yi koltuğa oturtup, koltukla birlikte aynı simülasyona sokarız.

### 4.5 Sonuç kriterleri nasıl hesaplanır?

Simülasyon bittiğinde, dummy'nin sensör noktalarından "zamana karşı ivme/kuvvet" verisi çıkar. Bunlardan yaralanma kriterleri hesaplanır:

**Teknik detay kutusu — HIC formülü:**
> `HIC = max { [ (1/(t2−t1)) · ∫(t1→t2) a(t) dt ]^2.5 · (t2−t1) }`
>
> Burada `a(t)` başın bileşke ivmesi (g cinsinden), `t1` ve `t2` ise (t2−t1 ≤ 36 ms veya 15 ms sınırlaması olan) bir zaman penceresi. Formül, bu pencereyi kayan şekilde tüm sinyal boyunca gezdirip en yüksek HIC değerini bulur.

**Teknik detay kutusu — Nij formülü:**
> `Nij = Fz/Fzc + My/Myc`
>
> `Fz`: boyundaki eksenel (yukarı-aşağı) kuvvet, `My`: boyundaki eğilme momenti, `Fzc` ve `Myc` ise dummy tipine göre standartlarda tanımlı kritik (normalize edici) değerler. Dört farklı Nij türü vardır (tension-flexion, tension-extension, compression-flexion, compression-extension) — en yükseği rapor edilir.

Bu formüllerin hepsi zaten literatürde/standartlarda net tanımlı — bizim yazacağımız kod, ham sensör verisini bu formüllere sokup otomatik sonuç üretmekten ibaret (yani "biz formülü icat etmiyoruz, var olan resmi formülü otomatik uyguluyoruz").

---

## 5. Backend Mimarisi

### 5.1 Sade anlatım

Backend, "sahne arkasında" çalışan, kullanıcının görmediği ama tüm işi yapan kısım. Bizim durumumuzda backend'in görevi şu:

1. Müşterinin yüklediği CAD dosyasını ve pulse verisini al
2. Bunları simülasyon motorunun (LS-DYNA) anlayacağı dosya formatına otomatik çevir
3. Dummy'yi doğru pozisyonda otomatik yerleştir
4. Simülasyonu bir bilgisayar kümesinde (cloud/HPC) çalıştır — bu saatler sürebilir
5. Motor bitince çıkan devasa sonuç dosyasını oku, içinden gereken sayıları (HIC, Nij, deformasyon vb.) çıkar
6. Bunları pass/fail tablosuna ve görsel animasyona çevirip kullanıcıya sun

### 5.2 Mimari diyagramı (bileşenler)

```
[Web Arayüzü] 
      │  (CAD dosyası + pulse verisi yükleme)
      ▼
[API Gateway / Kimlik Doğrulama]
      │
      ▼
[Proje Yönetim Servisi] ──► [Veritabanı: proje, müşteri, dosya kayıtları]
      │
      ▼
[Ön-İşleme (Pre-processing) Servisi]
   - CAD temizleme / mesh (ağ) oluşturma
   - Malzeme kartı atama
   - Dummy'yi otomatik konumlandırma
   - Pulse eğrisini boundary condition olarak tanımlama
      │
      ▼
[İş Kuyruğu (Job Queue)] ──► [Solver Orkestrasyon Servisi]
      │
      ▼
[Hesaplama Kümesi (HPC/Cloud)]
   - LS-DYNA / RADIOSS çalıştırma (çok çekirdekli, saatler sürebilir)
      │
      ▼
[Son-İşleme (Post-processing) Servisi]
   - Ham sonuç dosyasını (binary, çok büyük) okuma
   - HIC / Nij / femur / lumbar hesaplama
   - Deformasyon, kırılma açısı çıkarma
   - Pass/Fail karar motoru (standart limitlerle otomatik kıyaslama)
   - Animasyon/video üretimi
      │
      ▼
[Sonuç Deposu] ──► [Bildirim Servisi] ──► [Web Arayüzü: Rapor + Görsel]
```

### 5.3 Teknoloji yığını önerisi

| Katman | Önerilen teknoloji | Neden |
|---|---|---|
| API / backend servisleri | Python (FastAPI) veya Node.js (NestJS) | Hızlı geliştirme, mühendislik ekosistemiyle (Python: NumPy, SciPy, VTK) uyumlu |
| İş kuyruğu / orkestrasyon | Celery + Redis, veya Temporal.io | Uzun süren (saatler süren) simülasyon işlerini güvenilir şekilde yönetmek için |
| Solver | LS-DYNA (lisanslı) — çağrı/otomasyon Python scriptleriyle | Sektör standardı, güvenilirliği kanıtlı |
| CAD işleme | Open CASCADE (STEP/IGES okuma), Gmsh (mesh oluşturma) | Açık kaynak, endüstriyel CAD formatlarını okuyabilir |
| Sonuç dosyası okuma | LS-DYNA'nın d3plot/binout formatları için `lasso-python` veya `qd-cae-python` kütüphaneleri | Ham sonuç dosyalarını Python'a aktarmak için mevcut açık kaynak araçlar |
| Hesaplama altyapısı | AWS/Azure/GCP HPC instance'ları (yüksek CPU çekirdekli) veya kendi sunucu kümesi | Simülasyonlar çok işlemci gücü ister, talebe göre ölçeklenebilir olmalı |
| Veritabanı | PostgreSQL (proje/kullanıcı verisi) + S3 uyumlu obje depolama (CAD, sonuç dosyaları — bunlar GB boyutunda olabilir) | Yapısal veri + büyük dosya ayrımı |
| Görselleştirme/animasyon üretimi | ParaView (script modunda) veya VTK.js | Simülasyon sonucundan video/3D görsel üretmek için endüstri standardı araçlar |

### 5.4 Backend yol haritası (fazlar)

1. **Faz 0 — Keşif (1-2 ay):** LS-DYNA lisansı ve dummy FE modeli (Humanetics/LSTC) tedarik sözleşmeleri; 2-3 gerçek koltuk/pulse verisiyle manuel deneme simülasyonları çalıştırıp iş akışını elle doğrulama.
2. **Faz 1 — Otomasyon çekirdeği (3-6 ay):** CAD → mesh → solver girdi dosyası otomatik üretimi; tek bir standart pulse (örn. sadece 16g forward) ve tek dummy tipi ile uçtan uca otomatik çalışan boru hattı (pipeline).
3. **Faz 2 — Sonuç zekası (2-4 ay):** Post-processing motoru — HIC/Nij/femur/lumbar otomatik hesaplama, pass/fail karar motoru, temel deformasyon/kırılma açısı çıkarımı.
4. **Faz 3 — Görselleştirme ve raporlama (2-3 ay):** Otomatik animasyon/video üretimi, PDF sertifikasyon-tarzı rapor üretimi.
5. **Faz 4 — Ölçekleme ve çoklu senaryo (3-6 ay):** 14g dikey pulse desteği, farklı dummy tipleri (5. persentil kadın, 50. persentil erkek vb.), çoklu koltuk (sıra/row) simülasyonu, kompozit malzeme desteği.
6. **Faz 5 — Kurumsal özellikler (devam eden):** Çoklu kullanıcı/şirket izolasyonu, IP/veri güvenliği sertifikasyonları (ITAR/export control uyumluluğu — havacılık verisi hassas olabilir), versiyon kontrolü, denetim izi (audit trail).

---

## 6. Frontend Mimarisi

### 6.1 Sade anlatım

Frontend, müşterinin/mühendisin gördüğü ve tıkladığı web arayüzü. Burada temel akış:

1. Proje oluştur, koltuk CAD dosyasını yükle
2. Test senaryosunu seç (14g mi 16g mi, hangi dummy, kaç koltuk vb.)
3. Pulse eğrisini yükle veya standart şablonlardan seç
4. "Simülasyonu Başlat" de
5. İlerleme çubuğunu izle (simülasyon saatler sürebileceği için, "işlem tamamlandı" bildirimi gelir)
6. Sonuç ekranında: pass/fail tablosu, grafikler (kuvvet-zaman), 3D deformasyon görselleştirmesi, indirilebilir video ve PDF rapor

### 6.2 Ana ekranlar

| Ekran | İçerik |
|---|---|
| **Proje Panosu** | Kullanıcının tüm projelerinin listesi, durumları (hazırlanıyor / çalışıyor / tamamlandı / pass / fail) |
| **CAD Yükleme & Önizleme** | 3B model yükleme (STEP/IGES/STL), tarayıcı içinde 3D önizleme, koltuğun doğru yüklendiğini görsel kontrol |
| **Senaryo Kurulumu** | Pulse seçimi/yükleme (grafik editörü ile), dummy tipi ve pozisyonu seçimi, koltuk sıra sayısı, malzeme bilgisi girişi |
| **Simülasyon İzleme** | İlerleme çubuğu, tahmini bitiş süresi, log/durum bilgisi |
| **Sonuç Dashboard'u** | Pass/Fail büyük özet kartı; HIC, Nij, femur, lumbar, excursion değerlerinin limitlerle yan yana gösterimi (yeşil/kırmızı); kuvvet-zaman grafikleri |
| **3D Sonuç Görüntüleyici** | Tarayıcı içinde deforme olmuş koltuğun 3D animasyonu — zaman çubuğunu ileri/geri oynatma, renklendirilmiş gerilme/deformasyon haritası (kırmızı = yüksek yük bölgesi) |
| **Rapor & Dışa Aktarım** | Otomatik oluşturulan PDF rapor, video (mp4) indirme, ham veri (CSV) indirme |

### 6.3 Teknoloji yığını önerisi

| Katman | Önerilen teknoloji | Neden |
|---|---|---|
| Web uygulaması çatısı | React (Next.js) | Geniş ekosistem, hızlı geliştirme |
| 3D görselleştirme | Three.js veya VTK.js (WebGL tabanlı) | Tarayıcıda büyük 3D mesh + zamana bağlı animasyon oynatmak için endüstri standardı |
| Grafik/chart | Recharts veya D3.js | Kuvvet-zaman, ivme-zaman grafiklerini interaktif göstermek için |
| Durum yönetimi | React Query + Zustand/Redux | Uzun süren arka plan işlerinin (simülasyon) durumunu takip etmek için |
| Gerçek zamanlı bildirim | WebSocket (Socket.io) | Simülasyon tamamlandığında anlık bildirim |

### 6.4 Frontend yol haritası (fazlar)

1. **Faz 1:** Proje oluşturma, CAD yükleme + 3D önizleme, temel pulse seçim ekranı.
2. **Faz 2:** Simülasyon başlatma + ilerleme takibi + basit sonuç tablosu (sayısal pass/fail).
3. **Faz 3:** İnteraktif 3D sonuç görüntüleyici (deformasyon animasyonu, zaman çubuğu, renk haritası).
4. **Faz 4:** Otomatik PDF rapor üretimi, video export, çoklu senaryo karşılaştırma ekranı (örn. "tasarım v1 vs v2" yan yana).
5. **Faz 5:** Kurumsal özellikler — takım/rol yönetimi, versiyon geçmişi, yorum/işbirliği özellikleri (mühendislerin sonuç üzerinde not bırakabilmesi).

---

## 7. Uçtan Uca Veri Akışı — "Müşteriden Ne Alırız, Ne Yaparız, Ne Veririz"

### Müşteriden alınanlar
1. Koltuğun 3D CAD modeli (STEP/IGES formatında, tüm parçalar ve malzemeleriyle)
2. Test edilecek pulse verisi (ivme-zaman eğrisi, genelde CSV/Excel veya standart şablon seçimi — 14g/16g)
3. Test konfigürasyonu (kaç koltuklu sıra, hangi dummy tipi/tipleri, hangi koltuklara dummy konacağı, kemer/bağlama sistemi bilgisi)
4. (Opsiyonel) Malzeme özellikleri — eğer müşteri kendi malzeme test verisini paylaşırsa daha hassas sonuç; paylaşmazsa standart havacılık malzeme kütüphanemizden seçilir

### Arka planda yapılanlar
1. CAD modelinin temizlenmesi ve **mesh** haline getirilmesi (yüzeyin binlerce küçük üçgen/dörtgene bölünmesi — hesaplama bunlar üzerinden yapılır)
2. Her parçaya doğru malzeme davranışının atanması
3. Dijital dummy'nin koltuğa doğru pozisyonda, doğru kemer bağlantısıyla yerleştirilmesi
4. Pulse eğrisinin, koltuğun "tabanına" hareket koşulu olarak uygulanması
5. Simülasyonun hesaplama kümesinde çalıştırılması (saatler sürebilir)
6. Çıkan ham sonuçtan yaralanma kriterlerinin hesaplanması ve resmi limitlerle karşılaştırılması
7. Görsel animasyon ve rapor üretimi

### Müşteriye verilenler
1. **Pass/Fail özet kararı** (genel + her kriter için ayrı ayrı)
2. Sayısal sonuçlar: HIC, Nij (4 türü), femur load, lumbar load, head/knee excursion — hepsi limitle karşılaştırmalı
3. Koltuk üzerindeki kuvvet dağılımı haritası (nerede ne kadar yük var)
4. Deformasyon miktarı ve yönü (koltuk hangi yöne, kaç derece eğildi/katlandı)
5. Kırılma/hasar bölgeleri (varsa) ve şiddeti
6. Dummy'nin hareketi (kaç derece öne eğildi, baş/diz nereye ne kadar gitti)
7. Zamana bağlı 3D animasyon/video
8. İndirilebilir PDF rapor ve ham veri

---

## 8. Riskler ve Dikkat Edilmesi Gerekenler

- **Bu bir sertifikasyon kanıtı değildir:** FAA/EASA, resmi sertifikasyon için hâlâ fiziksel test istiyor. Ürünümüz "testten önce güven kazanma ve tasarım optimizasyonu" aracı olarak konumlanmalı, testin yerine geçtiği iddia edilmemeli — aksi halde regülasyon/hukuki risk doğar.
- **Doğrulama (validasyon) şart:** Platformun sonuçlarının gerçek fiziksel testlerle örtüştüğünü göstermek (correlation study) kritik — ilk müşterilerle birlikte "bilinen bir testin sonucunu simüle edip gerçekle kıyaslama" çalışmaları yapılmalı.
- **Lisans maliyetleri:** LS-DYNA ve dummy FE modelleri (Humanetics/LSTC) ciddi yıllık lisans bedeli gerektirir — iş modeline (fiyatlandırmaya) baştan yansıtılmalı.
- **Hesaplama maliyeti:** Her simülasyon saatlerce yüksek performanslı bilgisayar gücü tüketir — bulut maliyeti fiyatlandırmaya dahil edilmeli.
- **Veri hassasiyeti:** Havacılık CAD verileri ticari sır ve bazen export-control (ITAR/EAR benzeri) kapsamında olabilir — veri güvenliği ve saklama politikaları en baştan sağlam kurulmalı.

---

## 9. Özet Zaman Çizelgesi

| Dönem | Hedef |
|---|---|
| Ay 1-2 | Lisans/veri tedariki, keşif, ilk manuel simülasyon denemeleri |
| Ay 3-8 | Backend otomasyon çekirdeği (tek pulse, tek dummy, uçtan uca) |
| Ay 6-10 | Frontend Faz 1-2 (paralel geliştirme) |
| Ay 9-12 | Sonuç zekası + temel görselleştirme, ilk pilot müşteri ile doğrulama çalışması |
| Ay 12-18 | Tam görselleştirme, raporlama, çoklu senaryo/dummy desteği, kompozit malzeme desteği |
| Ay 18+ | Ölçekleme, kurumsal özellikler, kendi hesaplama modüllerinin kademeli geliştirilmesi (Seçenek A'ya doğru kademeli geçiş) |

---

Bu plan, "tam kapsamlı, sertifikasyon-seviyesinde eksiksiz platform" hedefine, gerçekçi ve aşamalı bir yol üzerinden ulaşacak şekilde tasarlandı: önce güvenilir, sektörde kanıtlanmış bir motor üzerine otomasyon katmanı kurup hızlıca değer üretmek; zamanla kendi teknik derinliğini ve IP'ni biriktirmek.
