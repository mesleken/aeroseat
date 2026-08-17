% =========================================================================
% AeroSeat - BEPU Monte Carlo Sensitivity Analysis
% Reference: Lamanna et al. (2019) Plackett-Burman Design Factors
% =========================================================================
clear; clc; close all;

%% 1. PARAMETRE UZAYININ TANIMLANMASI
% 9 Tasarım faktörü ve Lamanna (2019) Tablo 1'e göre alt/üst sınırları [Min, Max]
param_names = {'Ap_x (Kemer Ankraj X)', 'Ap_y (Kemer Ankraj Y)', ...
               'd1 (Arka Kiris Kalinligi)', 'd2 (Arka Ayak Kalinligi)', ...
               'd3 (Arka Ayak Govdesi)', 'd4 (Sok Emici Kalinligi)', ...
               'd5 (Arka Ayak Genisligi)', 'd6 (Guclendirme Kirisi Kal.)', ...
               'd7 (Guclendirme Kirisi Uz.)'};

bounds = [
    26.0,  45.0;  % Ap_x (mm)
    44.0,  88.0;  % Ap_y (mm)
    2.0,   3.0;   % d1 (mm)
    3.0,   4.5;   % d2 (mm)
    1.8,   2.7;   % d3 (mm)
    2.0,   3.2;   % d4 (mm)
    18.0,  20.0;  % d5 (mm)
    1.0,   1.5;   % d6 (mm)
    150.0, 250.0  % d7 (mm)
];

num_params = size(bounds, 1);
num_samples = 1000; % Monte Carlo Iterasyon Sayisi

%% 2. LATIN HYPERCUBE SAMPLING (LHS)
fprintf('BEPU Analizi Baslatiliyor...\n');
fprintf('%d Adet LHS Örneklemi Olusturuluyor...\n', num_samples);

% LHS ile [0,1] arasinda uniform dagilmis ornekler al
if exist('lhsdesign', 'file') == 2
    lhs_samples = lhsdesign(num_samples, num_params);
else
    % Fallback if Statistics Toolbox is not installed
    lhs_samples = zeros(num_samples, num_params);
    for j = 1:num_params
        lhs_samples(:, j) = (randperm(num_samples)' - 1 + rand(num_samples, 1)) / num_samples;
    end
end

% [0,1] orneklerini gercek fiziksel sinirlara [Min, Max] genislet (Scaling)
X_inputs = zeros(num_samples, num_params);
for i = 1:num_params
    X_inputs(:, i) = bounds(i, 1) + lhs_samples(:, i) .* (bounds(i, 2) - bounds(i, 1));
end

%% 3. SIMULASYON DONGUSU (MONTE CARLO ENGINE)
% HIC sonuclarini tutacak dizi
Y_HIC = zeros(num_samples, 1);

tic;
for i = 1:num_samples
    current_design = X_inputs(i, :);
    Y_HIC(i) = surrogate_aeroseat_solver(current_design);
    
    if mod(i, 200) == 0
        fprintf('Simulasyon %d / %d tamamlandi.\n', i, num_samples);
    end
end
sim_time = toc;
fprintf('Tum simulasyonlar %.2f saniyede tamamlandi.\n\n', sim_time);

%% 4. ISTATISTIKSEL ANALIZ VE HASSASIYET (SENSITIVITY)
pass_rate = sum(Y_HIC < 1000) / num_samples * 100;
fprintf('--- AEROSEAT BEPU RAPORU ---\n');
fprintf('Maksimum Gözlenen HIC : %.1f\n', max(Y_HIC));
fprintf('Minimum Gözlenen HIC  : %.1f\n', min(Y_HIC));
fprintf('Ortalama HIC          : %.1f\n', mean(Y_HIC));
fprintf('Sertifikasyon Basarisi (PASS Rate): %%%.2f\n', pass_rate);

% Pearson Korelasyon Katsayilarinin Hesaplanmasi
correlation_coeffs = zeros(num_params, 1);
for i = 1:num_params
    R = corrcoef(X_inputs(:, i), Y_HIC);
    correlation_coeffs(i) = R(1,2);
end

%% 5. GORSELLESTIRME (TORNADO CHART & HISTOGRAM)
figure('Name', 'AeroSeat BEPU Analysis', 'Position', [100, 100, 1200, 500]);

% Grafik 1: HIC Dagilimi (Histogram)
subplot(1, 2, 1);
histogram(Y_HIC, 30, 'FaceColor', [0.16, 0.50, 0.73], 'EdgeColor', 'w');
hold on;
xline(1000, 'r--', 'LineWidth', 2, 'Label', 'FAA Limit (1000)');
title('HIC Degerleri Dagilimi (1000 Simulasyon)');
xlabel('HIC Degeri');
ylabel('Frekans (Adet)');
grid on;

% Grafik 2: Tornado Chart (Sensitivite Analizi)
subplot(1, 2, 2);
[sorted_corr, sort_idx] = sort(correlation_coeffs, 'ascend');
sorted_names = param_names(sort_idx);

barh(sorted_corr, 'FaceColor', [0.91, 0.30, 0.24]);
set(gca, 'YTick', 1:num_params, 'YTickLabel', sorted_names);
title('Parametrelerin HIC Uzerindeki Etkisi (Pearson R)');
xlabel('Korelasyon Katsayisi (Negatif: HICi Dusurur)');
grid on;

function hic_val = surrogate_aeroseat_solver(X)
    base_hic = 1200; 
    effect_apx = -2.5 * (X(1) - 26);   
    effect_apy = -1.8 * (X(2) - 44);   
    effect_d1  = -50.0 * (X(3) - 2.0); 
    effect_d2  = -40.0 * (X(4) - 3.0); 
    effect_d4  = -60.0 * (X(6) - 2.0);
    noise = randn() * 15;
    
    hic_val = base_hic + effect_apx + effect_apy + effect_d1 + effect_d2 + effect_d4 + noise;
    if hic_val < 0
        hic_val = 0;
    end
end
