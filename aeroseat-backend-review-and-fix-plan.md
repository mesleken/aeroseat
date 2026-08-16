# AeroSeat Backend — Kod İncelemesi ve Geliştirme Planı

**İncelenen:** `app.zip` (FastAPI + SQLAlchemy backend, ~1100 satır API + ~600 satır domain/adapter kodu)
**Genel değerlendirme:** İskelet, master plana şaşırtıcı derecede sadık — DB şeması, üç hash kavramı (Artifact/Configuration/Execution Fingerprint), idempotency mekanizması ve `model_qa.py`'deki "sahte PASS verme" disiplini gerçekten iyi. Ama beş somut sorun var, ikisi **kritik** — bunlar "eksik özellik" değil, **şu anki haliyle üretilen sayıların ve kanıt paketinin yanıltıcı olmasına** yol açan sorunlar.

---

## KRİTİK — Hemen düzeltilmeli

### K1. Solver adı "LSDYNA" ama gerçekte kendi yazdığınız fizik motoru çalışıyor

**Dosya:** `adapters/solver/factory.py`, satır 15-19

```python
elif solver_upper == "LSDYNA":
    if app_env == "development":
        return PhysicsSolverAdapter(seed=42)   # ← sessizce kendi modelinize yönlendiriyor
    return LSDynaAdapter()
```

`SimulationConfiguration.solver_name = "LSDYNA"` seçildiğinde (ki varsayılan bu), development modunda **hiçbir uyarı vermeden** `PhysicsSolverAdapter` — yani `domain/physics/lumped_mass_model.py`'deki kendi yazdığınız 6-DOF lumped-mass modeliniz — devreye giriyor. Bu model kavramsal olarak iyi yazılmış (yay-damper sistemleri, gerçekçi stiffness değerleri), ama:

- **V1.0 Anayasası Kural 1'i ihlal ediyor**: "Fizik motoru yazılmaz." Burada gerçekten bir fizik motoru yazılmış ve production akışına LS-DYNA'nın yerine sessizce sokulmuş.
- **Evidence paketi yalan söylüyor**: `input_manifest.json` içinde `"solver_name": "LSDYNA", "solver_version": "R13.1"` yazıyor, ama sayılar aslında sizin lumped-mass modelinizden geliyor. Bir denetçi bu PDF'i açtığında LS-DYNA çıktısı okuduğunu sanacak.
- Fake `d3plot`/`binout` dosyaları üretiliyor (`physics_solver.py` satır 87-91) — gerçek LS-DYNA formatında değil, düz metin.

**Neden önemli:** Bu, "demo/geliştirme kolaylığı" ile "kanıt zincirinin bütünlüğü" arasındaki çizgiyi bulanıklaştırıyor — tam olarak sistemin var olma amacının karşıtı.

**Düzeltme:**
1. `PhysicsSolverAdapter`'ı ayrı, açıkça isimlendirilmiş bir solver olarak bırakın (`solver_name="PHYSICS_LUMPED_MASS"`), asla `"LSDYNA"` adı altında çalıştırmayın.
2. `solver_name == "LSDYNA"` seçildiğinde gerçek `LSDynaAdapter` yoksa (henüz lisans/HPC entegrasyonu yoksa) **hata fırlatın**, sessizce başka bir şeye düşmeyin: `raise NotImplementedError("LS-DYNA adapter not yet configured — use solver_name='PHYSICS_LUMPED_MASS' explicitly for development")`.
3. `PhysicsSolverAdapter` ile üretilen her `SimulationResult`/`EvidenceArtifact`'a görsel/programatik bir işaret ekleyin (örn. `is_reference_only: true`) ki hiçbir rapor yanlışlıkla "gerçek LS-DYNA sonucu" gibi sunulmasın.

### K2. Correlation Engine gerçek fiziksel test verisini hiç okumuyor

**Dosya:** `api/v1/endpoints/correlation.py`, satır 84-90

```python
sim_head = ts.get("head_acceleration", (42.0 * np.exp(...)).tolist())   # fallback sentetik
...
phys_head = 44.0 * np.exp(-((t - 0.0765)**2) / (2 * (0.0185**2)))        # HER ZAMAN sentetik, physical_test_id kullanılmıyor
phys_femur = 4.35 * np.exp(...)
```

`physical_test_id` parametresi endpoint'e geliyor, `PhysicalTest` kaydı veritabanından çekiliyor (satır 57-59) — ama **hiçbir yerde `phys_test.raw_data_uri`'deki dosya okunmuyor.** Fiziksel test eğrisi, hangi test seçilirse seçilsin, her zaman kod içine gömülü aynı Gauss eğrisiyle değiştiriliyor.

**Neden kritik:** Bu, Correlation Contract'ın (Sprague-Geers, magnitude/phase error) şu an **hiçbir gerçek korelasyon hesaplamadığı**, sadece iki sentetik eğriyi karşılaştırdığı anlamına geliyor. `CorrelationVector` tablosuna yazılan sayılar gerçek bir bilimsel anlam taşımıyor.

**Düzeltme:**
1. `phys_test.raw_data_uri`'deki dosyayı (CSV) gerçekten okuyup parse eden bir fonksiyon yazın (`load_physical_test_signal(uri, channel) -> (time, values)`).
2. Simülasyon tarafı için de aynı şekilde `sim_res` üzerinden gerçek `raw_timeseries`'i kullanın — fallback sentetik veri sadece **hiç veri yoksa ve açıkça "DEMO_MODE" flag'i varsa** kullanılmalı, sessiz varsayılan olmamalı.
3. Gerçek veri eksikse endpoint 422 dönmeli ("physical test raw data could not be parsed"), sentetik veriyle sessizce devam etmemeli.

---

## ÖNEMLİ — V1 tamamlanmadan düzeltilmeli

### Ö1. Golden Dataset regresyon testi tautoloji (kendi kendini asla yalanlayamaz)

**Dosya:** `domain/contracts/golden_dataset.py`, satır 70-71

```python
sim_head = processed_head * 0.96   # "simülasyon" verisi = fiziksel veri × 0.96
vector = calculate_channel_correlation_vector(grid_t, sim_head, processed_head, "head_acceleration")
```

"Simülasyon" sinyali, fiziksel sinyalin kendisinden türetiliyor. Bu regresyon testi **matematiksel olarak asla anlamlı şekilde FAIL veremez** — her zaman ~%4 sabit bir hata gösterip PASS dönecektir, kodda gerçek bir bozulma olsa bile. Ayrıca `physical_test_sled16g.csv` da gerçek bir sled testi değil, kod içinde Gauss formülüyle üretilmiş (satır 21-24).

**Düzeltme:**
1. Bunu açıkça "**smoke test**" olarak yeniden adlandırın (pipeline'ın çalıştığını doğrular, bilimsel doğruluğu değil) — `run_golden_dataset_regression()` fonksiyonunun döndürdüğü `"status": "PASS"` yerine `"status": "SMOKE_TEST_PASS (not scientifically validated — awaiting real physical test data)"` gibi dürüst bir etiket kullanın.
2. Gerçek golden dataset'i (gerçek OTEST/pilot sled verisi) bağımsız bir iş akışı olarak takip edin — master planda zaten böyle işaretlenmişti, kod bu gerçeği net yansıtmalı.

### Ö2. Aynı "SAE J211 CFC filtresi" için iki farklı, çelişen formül

- `domain/physics/signal_processing.py` satır 36: `f_cutoff = cfc * 1.0`
- `domain/contracts/scientific_processing.py` satır 19: `cutoff_hz = cfc * 2.0775`

Aynı kavram (CFC → kesim frekansı dönüşümü), pipeline'ın iki farklı yerinde (biri simülasyon çıktısını filtrelerken, diğeri korelasyon karşılaştırmasında) **birbiriyle tutarsız** şekilde uygulanıyor. Bu tam olarak Golden Dataset contract'ının yakalaması gereken türde bir bilimsel hata — ama Ö1'deki tautoloji yüzünden yakalanamıyor.

**Düzeltme:** Tek bir `sae_j211_filter()` fonksiyonu bırakın (`domain/contracts/scientific_processing.py`'deki, çünkü "hard-code yok" ilkesine daha sadık), `domain/physics/signal_processing.py`'yi bunu çağıracak şekilde güncelleyin. Doğru CFC→cutoff katsayısını (SAE J211 spesifikasyonundan) netleştirip tek yerde sabitleyin.

### Ö3. Artifact Hash, dosya içeriği değil dosya yolu string'i hashleniyor

**Dosya:** `api/v1/endpoints/correlation.py`, satır 33-35

```python
data_bytes = payload.raw_data_uri.encode('utf-8')   # URI string'i hashleniyor
sha256 = hashlib.sha256(data_bytes).hexdigest()      # dosya içeriği değil
```

Contract 4'ün tanımı: "Artifact Hash = SHA256(dosyanın kendisi)". Burada `cad_upload.py`'de doğru yapılmış (satır 42-44, gerçek `content` byte'ları hashleniyor) ama `physical-tests` endpoint'inde yanlış yapılmış — muhtemelen çünkü bu endpoint dosya upload'ı değil, sadece bir URI string'i kabul ediyor.

**Düzeltme:** `POST /physical-tests` endpoint'ini de `cad_upload.py`'deki gibi gerçek dosya upload'ı (`UploadFile`) kabul edecek şekilde değiştirin; hash'i gerçek içerikten hesaplayın.

### Ö4. `execution_fingerprint` alanına yanlışlıkla `configuration_hash` yazılıyor

**Dosya:** `api/v1/endpoints/evidence.py`, satır 117

```python
"execution_fingerprint": config.configuration_hash if config else "N/A",
```

`SolverJob.execution_fingerprint` zaten hesaplanıp saklanmış durumda (`simulations.py` satır 138-144) ama evidence manifest'i onu kullanmıyor, yanlışlıkla `configuration_hash`'i tekrar yazıyor. Üç ayrı hash kavramını ayırmanın tüm amacı bu noktada kayboluyor.

**Düzeltme:** `EngineeringAssessment`'tan ilgili `SolverJob`'a kadar zinciri takip edip gerçek `execution_fingerprint`'i çekin.

---

## ORTA ÖNCELİK — V1 kapsamında ama daha az acil

| # | Bulgu | Dosya | Not |
|---|---|---|---|
| O1 | İmmutability sadece SQLAlchemy ORM event listener seviyesinde; gerçek Postgres trigger DDL'i (`get_postgres_trigger_ddl()`) üretiliyor ama hiç çağrılmıyor/uygulanmıyor | `db/triggers.py`, `db/database.py` | Ham SQL veya farklı bir erişim yolu bu korumayı bypass edebilir. SQLite'ta zaten trigger DDL çalışmaz. |
| O2 | Asenkron worker mimarisi (Celery/Redis, Submitter/Poller/PostProcessor) hiç yok — her şey FastAPI request handler'ı içinde senkron çalışıyor | `simulations.py` `run_simulation()` | Mock/physics adapter anlık olduğu için şimdilik sorun değil; gerçek LS-DYNA (saatler) devreye girdiğinde HTTP timeout / worker bloklanması kaçınılmaz. |
| O3 | `SolverJob.status` şeması zengin (QUEUED/PREPARING/SUBMITTED/.../VALIDATING) ama kodda sadece RUNNING→COMPLETED kullanılıyor, ara durumlar hiç set edilmiyor | `simulations.py` | Şema hazır, akış onu kullanmıyor. |
| O4 | CAD `part_manifest` tamamen sahte/sabit — dosya içeriğine hiç bakılmıyor, her yüklemede aynı 4 parça listesi dönüyor | `cad_upload.py` satır 52-63 | Beklenen bir V1 sınırlaması (gerçek CAD parser büyük iş) ama şu an kullanıcıya "gerçek" gibi sunuluyor; en azından `"is_placeholder": true` etiketiyle işaretlenmeli. |
| O5 | `requirements.txt` / bağımlılık dosyası yok | proje kökü | Kurulum tekrarlanabilirliği risk altında. |

---

## OLUMLU — Korunması/övülmesi gereken kararlar

- **`model_qa.py`'deki dürüstlük ilkesi çok değerli**: gerçek FE parser gerektiren kontroller (negative Jacobian, penetrasyon, bağlantısız mesh) sahte `PASS` yerine açıkça `UNVERIFIED` dönüyor. Bu tam olarak "sessiz başarısızlık yok" felsefesiyle uyumlu — koruyun, genişletin.
- DB şeması (immutable revision'lar, `SolverMaterialRepresentation` ile `MaterialDataset` ayrımı, `TestConfiguration`/`PhysicalTest` ayrımı) plana neredeyse birebir sadık.
- HIC15 ve Nij formülleri doğru uygulanmış, gerçek FMVSS/AS8049E kritik limit değerleri (6811N tension, 6160N compression vb.) kullanılmış — uydurma değil.
- Idempotency/fingerprint mekanizması (`get_completed_job_by_fingerprint`) tam olarak planlandığı gibi çalışıyor.
- Evidence PDF üretimi (`reportlab` ile) gerçek, düzgün biçimlendirilmiş, dekoratif değil.
- `simulations.py` içindeki "P0 item" yorumları (NOT_ASSESSABLE handling, lineage filtering) daha önce bir iterasyon geçtiğinin işareti — iyi bir sinyal.

---

## Önceliklendirilmiş Geliştirme Planı

### Sprint 1 (kanıt zincirinin dürüstlüğünü kurtarmak — her şeyden önce)
1. **K1**: `PhysicsSolverAdapter`'ı `"LSDYNA"` isminden ayırın; gerçek adapter yoksa hata fırlatın, sessiz ikame yapmayın.
2. **K2**: Correlation endpoint'ini gerçek `raw_data_uri` dosyasını okuyacak şekilde düzeltin; sentetik fallback'i sadece açık `DEMO_MODE` bayrağı altında bırakın.
3. **Ö1**: Golden dataset regresyonunu "smoke test" olarak yeniden etiketleyin; tautolojik karşılaştırmayı (`sim = phys × 0.96`) kaldırın veya en azından bağımsız bir sentetik model kullanın (fiziksel veriden türetilmemiş).

### Sprint 2 (bilimsel/kriptografik tutarlılık)
4. **Ö2**: CFC filtre formülünü tek yere indirin, doğru katsayıyı doğrulayın.
5. **Ö3**: Fiziksel test yüklemesini gerçek dosya upload'ına çevirin, hash'i içerikten hesaplayın.
6. **Ö4**: Evidence manifest'inde gerçek `execution_fingerprint`'i kullanın.

### Sprint 3 (operasyonel olgunluk)
7. **O1**: Gerçek Postgres trigger DDL'ini migration'a bağlayın (Alembic), sadece ORM-seviyesi korumayla yetinmeyin.
8. **O2 + O3**: Celery/Redis + Submitter/Poller/PostProcessor mimarisini kurun, zengin job status enum'unu gerçekten kullanın. (LS-DYNA entegrasyonundan önce bu şart — yoksa ilk gerçek uzun simülasyonda sistem kilitlenir.)

### Sprint 4 (dürüstlük etiketleme + temizlik)
9. **O4**: CAD part manifest'e `is_placeholder: true` ekleyin; gerçek CAD parser'ı ayrı bir iş kalemi olarak planlayın.
10. **O5**: `requirements.txt`/`pyproject.toml` ekleyin, sürüm sabitleyin.

---

## Genel değerlendirme

Bu, "boş bir iskeletten" çok daha ileride — plan gerçekten okunmuş ve şemaya, hash mimarisine, idempotency'ye sadık kalınmış. Ama şu anki haliyle sistemin **en kritik iddiası** ("bu sonuç gerçekten LS-DYNA'dan geldi" ve "bu korelasyon gerçek bir fiziksel testle karşılaştırıldı") **henüz doğru değil** — iki yerde sessizce sentetik/kendi yazılmış veriyle değiştiriliyor. Bunlar kötü niyetli değil, gelişim kolaylığı için mantıklı kısayollar, ama **sessiz** olmaları asıl sorun. Sprint 1'deki üç madde, kodun geri kalanının kalitesine yakışır bir dürüstlük seviyesine sistemi taşıyacaktır.
