"""
Реалистичный расчет эффекта внедрения Multi-Agent системы управления светофорами для города Астана
Консервативные оценки на основе международного опыта и реальных кейсов
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

# Настройка шрифтов для поддержки кириллицы
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

class AstanaTrafficAnalysisRealistic:
    def __init__(self):
        # ===== ПАРАМЕТРЫ АСТАНЫ =====
        self.population = 1_612_512
        self.bus_passengers_daily = 1_005_329
        self.private_transport_share = 0.624  # 62.4% используют личный транспорт
        self.private_transport_users = int(self.population * self.private_transport_share)

        # Автобусная сеть
        self.total_buses = 1_735
        self.total_routes = 133
        self.avg_bus_interval = 13  # минут
        self.total_route_length = 1_750  # км (все маршруты)
        self.avg_route_length = self.total_route_length / self.total_routes  # 13.16 км
        self.avg_bus_speed = 18  # км/ч
        self.avg_trip_time = 50  # минут (усредненное)
        self.passengers_per_bus_daily = 772

        # Дорожная инфраструктура
        self.total_traffic_lights = 728
        self.avg_signal_cycle = 36  # секунд
        self.road_capacity_vc = 0.77  # Volume/Capacity ratio
        self.avg_lanes = 2
        self.traffic_intensity = 7_000  # машин/час (пиковый час)
        self.avg_highway_speed = 23  # км/ч

        # Реалистичная оценка ежедневного автопарка
        # Не все машины едут одновременно, оцениваем активные авто в день
        self.daily_active_cars = int(self.traffic_intensity * 12)  # ~84,000 активных авто в день

        # Поведенческие параметры
        self.avg_passengers_per_car = 1.6

        # Экономические параметры
        self.parking_cost_per_hour = 100  # тенге
        self.parking_search_time = 7.6  # минут

        # ===== CO2 ПАРАМЕТРЫ =====
        self.car_co2_per_km = 170  # грамм CO2 на км
        self.bus_co2_per_passenger_km = 80  # грамм CO2 на пассажиро-км

        # Расход топлива
        self.car_fuel_consumption = 8.5  # литров на 100 км
        self.fuel_price = 250  # тенге за литр

        # ===== РЕАЛИСТИЧНЫЕ ЭФФЕКТЫ ОТ MULTI-AGENT СИСТЕМЫ =====
        # На основе международных исследований и кейсов (Барселона, Лос-Анджелес, Сингапур)

        # Усредненные показатели из трех сценариев симуляции
        self.bus_speed_improvement = 0.198  # +19.8% (среднее из симуляций)

        # РЕАЛИСТИЧНЫЙ Modal Shift:
        # Теоретически 56% готовы, но реально переходят только 10-12%
        # При улучшении на 20% скорости - примерно 10% пересаживаются
        self.realistic_modal_shift = 0.10  # 10% от пользователей личного транспорта

        # Влияние на пробки (консервативная оценка)
        self.congestion_reduction = 0.20  # -20% (вместо 49%)

        # Улучшение пропускной способности
        self.capacity_improvement = 0.15  # +15%

    def calculate_impact(self):
        """Расчет реального влияния системы"""
        results = {}

        # ====================================
        # 1. ПАССАЖИРОПОТОК АВТОБУСОВ
        # ====================================
        passengers_before = self.bus_passengers_daily

        # Прирост от улучшения скорости и комфорта
        # При улучшении скорости на 20% - прирост пассажиров 15-25%
        passenger_growth_rate = 0.20  # консервативно 20%
        passengers_after = passengers_before * (1 + passenger_growth_rate)
        passenger_increase = passengers_after - passengers_before

        results['passengers_before'] = passengers_before
        results['passengers_after'] = int(passengers_after)
        results['passenger_increase'] = int(passenger_increase)
        results['passenger_growth_pct'] = passenger_growth_rate * 100

        # ====================================
        # 2. СКОРОСТЬ АВТОБУСОВ
        # ====================================
        speed_before = self.avg_bus_speed
        speed_after = speed_before * (1 + self.bus_speed_improvement)

        results['bus_speed_before'] = speed_before
        results['bus_speed_after'] = round(speed_after, 1)
        results['speed_improvement_pct'] = self.bus_speed_improvement * 100

        # ====================================
        # 3. MODAL SHIFT (переход с авто на автобус)
        # ====================================
        # Реалистичная оценка: 10% пользователей личного транспорта
        actual_switchers = self.private_transport_users * self.realistic_modal_shift

        # Эти люди делают в среднем 2 поездки в день (туда-обратно)
        trips_per_person = 2

        # Количество машин, которые перестали использоваться
        # Учитываем, что не все сразу продают авто, но перестают ездить на нем ежедневно
        cars_removed_daily = actual_switchers / self.avg_passengers_per_car

        results['potential_switchers_56pct'] = int(self.private_transport_users * 0.56)
        results['realistic_switchers_10pct'] = int(actual_switchers)
        results['cars_removed'] = int(cars_removed_daily)

        # Снижение трафика в процентах от пикового часа
        traffic_reduction_hourly = cars_removed_daily / 24  # среднее в час
        traffic_reduction_pct = (traffic_reduction_hourly / self.traffic_intensity) * 100

        results['traffic_reduction_pct'] = round(traffic_reduction_pct, 2)

        # ====================================
        # 4. ВЛИЯНИЕ НА ПРОБКИ
        # ====================================
        congestion_before = 6.5  # базовый индекс
        congestion_after = congestion_before * (1 - self.congestion_reduction)

        results['congestion_before'] = congestion_before
        results['congestion_after'] = round(congestion_after, 1)
        results['congestion_reduction_pct'] = self.congestion_reduction * 100

        # ====================================
        # 5. ЭКОНОМИЯ ВРЕМЕНИ
        # ====================================
        # Время поездки на автобусе
        trip_time_before = self.avg_trip_time  # 50 минут
        trip_time_after = trip_time_before / (1 + self.bus_speed_improvement)
        time_saved_per_trip = trip_time_before - trip_time_after  # минуты

        # Количество поездок в день (все пассажиры после внедрения)
        # В среднем человек делает 2 поездки в день
        total_trips_daily = passengers_after * 2

        # Суммарная экономия времени
        total_time_saved_minutes = time_saved_per_trip * total_trips_daily
        total_time_saved_hours = total_time_saved_minutes / 60
        total_time_saved_hours_yearly = total_time_saved_hours * 365

        results['trip_time_before'] = round(trip_time_before, 1)
        results['trip_time_after'] = round(trip_time_after, 1)
        results['time_saved_per_trip'] = round(time_saved_per_trip, 2)
        results['total_time_saved_hours_daily'] = int(total_time_saved_hours)
        results['total_time_saved_hours_yearly'] = int(total_time_saved_hours_yearly)
        results['work_days_equivalent'] = int(total_time_saved_hours_yearly / 8)

        # ====================================
        # 6. ВЫБРОСЫ CO2
        # ====================================
        # Средняя дистанция поездки на авто
        avg_car_trip_distance = (24.79 / 60) * self.avg_highway_speed  # ~9.5 км
        trips_per_person = 2  # туда-обратно

        # CO2 ДО внедрения
        # Автомобили
        daily_car_trips = self.daily_active_cars * trips_per_person
        total_car_km_before = daily_car_trips * avg_car_trip_distance
        co2_from_cars_before = total_car_km_before * self.car_co2_per_km / 1_000_000  # тонны

        # Автобусы (фиксированный парк, но более реалистичный расчёт)
        # Средний автобус проезжает ~150 км/день, выбрасывает ~800 г CO2/км
        avg_bus_km_per_day = 150
        bus_co2_per_km = 800  # грамм/км
        co2_from_buses_before = (self.total_buses * avg_bus_km_per_day * bus_co2_per_km) / 1_000_000  # тонны

        total_co2_before = co2_from_cars_before + co2_from_buses_before

        # CO2 ПОСЛЕ внедрения
        # Автомобили (меньше машин на дорогах)
        daily_car_trips_after = (self.daily_active_cars - cars_removed_daily) * trips_per_person
        total_car_km_after = daily_car_trips_after * avg_car_trip_distance
        co2_from_cars_after = total_car_km_after * self.car_co2_per_km / 1_000_000

        # Автобусы (тот же парк, возможно небольшое увеличение из-за большей загрузки)
        # Но в первом приближении считаем константой
        co2_from_buses_after = co2_from_buses_before

        total_co2_after = co2_from_cars_after + co2_from_buses_after

        co2_reduction = total_co2_before - total_co2_after
        co2_reduction_yearly = co2_reduction * 365

        results['co2_cars_before_daily'] = round(co2_from_cars_before, 2)
        results['co2_buses_before_daily'] = round(co2_from_buses_before, 2)
        results['co2_total_before_daily'] = round(total_co2_before, 2)
        results['co2_cars_after_daily'] = round(co2_from_cars_after, 2)
        results['co2_buses_after_daily'] = round(co2_from_buses_after, 2)
        results['co2_total_after_daily'] = round(total_co2_after, 2)
        results['co2_reduction_daily'] = round(co2_reduction, 2)
        results['co2_reduction_yearly'] = round(co2_reduction_yearly, 2)
        results['co2_reduction_pct'] = round((co2_reduction / total_co2_before) * 100, 2)

        # ====================================
        # 7. ЭКОНОМИЯ ТОПЛИВА
        # ====================================
        # Километры, которые не проехали на авто
        total_km_saved_daily = cars_removed_daily * avg_car_trip_distance * trips_per_person
        total_km_saved_yearly = total_km_saved_daily * 365

        fuel_saved_liters_daily = total_km_saved_daily * (self.car_fuel_consumption / 100)
        fuel_saved_liters_yearly = total_km_saved_yearly * (self.car_fuel_consumption / 100)

        fuel_cost_saved_daily = fuel_saved_liters_daily * self.fuel_price
        fuel_cost_saved_yearly = fuel_saved_liters_yearly * self.fuel_price

        results['fuel_saved_daily_liters'] = int(fuel_saved_liters_daily)
        results['fuel_saved_yearly_liters'] = int(fuel_saved_liters_yearly)
        results['fuel_cost_saved_daily'] = int(fuel_cost_saved_daily)
        results['fuel_cost_saved_yearly'] = int(fuel_cost_saved_yearly)
        results['fuel_cost_saved_yearly_mln'] = round(fuel_cost_saved_yearly / 1_000_000, 1)

        # ====================================
        # 8. ЗАГРУЗКА ДОРОЖНОЙ СЕТИ
        # ====================================
        capacity_per_lane = 1_800  # машин/час/полоса
        total_capacity = capacity_per_lane * self.avg_lanes

        current_traffic_peak = self.traffic_intensity
        traffic_after_peak = current_traffic_peak - traffic_reduction_hourly

        load_before = (current_traffic_peak / total_capacity) * 100
        load_after = (traffic_after_peak / total_capacity) * 100
        capacity_freed = load_before - load_after

        results['road_capacity_total'] = total_capacity
        results['traffic_peak_before'] = current_traffic_peak
        results['traffic_peak_after'] = int(traffic_after_peak)
        results['load_before_pct'] = round(load_before, 1)
        results['load_after_pct'] = round(load_after, 1)
        results['capacity_freed_pct'] = round(capacity_freed, 1)

        # ====================================
        # 9. ЭКОНОМИЧЕСКИЕ ВЫГОДЫ
        # ====================================
        # Экономия на парковке для переключившихся
        avg_parking_hours_per_day = 2  # среднее время парковки
        parking_savings_daily = actual_switchers * avg_parking_hours_per_day * self.parking_cost_per_hour
        parking_savings_yearly = parking_savings_daily * 365

        # Экономия времени на поиск парковки
        parking_search_time_saved = actual_switchers * self.parking_search_time * trips_per_person  # минуты
        parking_search_hours_saved = parking_search_time_saved / 60
        parking_search_hours_yearly = parking_search_hours_saved * 365

        results['parking_savings_daily'] = int(parking_savings_daily)
        results['parking_savings_yearly'] = int(parking_savings_yearly)
        results['parking_savings_yearly_mln'] = round(parking_savings_yearly / 1_000_000, 1)
        results['parking_search_hours_saved_daily'] = int(parking_search_hours_saved)
        results['parking_search_hours_yearly'] = int(parking_search_hours_yearly)

        # Общая экономическая выгода
        total_economic_benefit = fuel_cost_saved_yearly + parking_savings_yearly
        results['total_economic_benefit_yearly'] = int(total_economic_benefit)
        results['total_economic_benefit_yearly_mln'] = round(total_economic_benefit / 1_000_000, 1)

        return results

    def create_visualizations(self, results):
        """Создание визуализаций результатов"""

        # Создаем фигуру с несколькими подграфиками (УМЕНЬШЕННЫЙ РАЗМЕР)
        fig = plt.figure(figsize=(16, 9))  # Было 20x12, стало 16x9
        gs = GridSpec(3, 3, figure=fig, hspace=0.35, wspace=0.35)

        # Цветовая схема
        color_before = '#E74C3C'  # красный
        color_after = '#2ECC71'  # зеленый
        color_neutral = '#3498DB'  # синий

        # Константа для расчетов
        trips_per_person = 2
        # ========================================
        # 1. ПАССАЖИРОПОТОК (верхний левый)
        # ========================================
        ax1 = fig.add_subplot(gs[0, 0])
        categories = ['ДО', 'ПОСЛЕ']
        values = [results['passengers_before'], results['passengers_after']]
        bars = ax1.bar(categories, values, color=[color_before, color_after], alpha=0.8, edgecolor='black')
        ax1.set_ylabel('Пассажиров в день', fontsize=9, fontweight='bold')
        ax1.set_title('1. Пассажиропоток', fontsize=10, fontweight='bold', pad=10)
        ax1.grid(axis='y', alpha=0.3, linestyle='--')
        ax1.tick_params(axis='both', which='major', labelsize=8)

        # Добавляем значения на столбцы
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width() / 2., height,
                     f'{int(height / 1000)}k',  # Сокращаем формат
                     ha='center', va='bottom', fontsize=8, fontweight='bold')

        # Процент прироста
        ax1.text(0.5, 0.92, f'+{results["passenger_growth_pct"]:.1f}%',
                 transform=ax1.transAxes, fontsize=11, color='green',
                 fontweight='bold', ha='center', va='top',
                 bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgreen', alpha=0.3))

        # ========================================
        # 2. СКОРОСТЬ АВТОБУСОВ (верхний центр)
        # ========================================
        ax2 = fig.add_subplot(gs[0, 1])
        categories = ['ДО', 'ПОСЛЕ']
        values = [results['bus_speed_before'], results['bus_speed_after']]
        bars = ax2.bar(categories, values, color=[color_before, color_after], alpha=0.8, edgecolor='black')
        ax2.set_ylabel('Скорость, км/ч', fontsize=9, fontweight='bold')
        ax2.set_title('2. Скорость автобусов', fontsize=10, fontweight='bold', pad=10)
        ax2.grid(axis='y', alpha=0.3, linestyle='--')
        ax2.set_ylim(0, max(values) * 1.2)
        ax2.tick_params(axis='both', which='major', labelsize=8)

        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width() / 2., height,
                     f'{height:.1f}',
                     ha='center', va='bottom', fontsize=8, fontweight='bold')

        ax2.text(0.5, 0.92, f'+{results["speed_improvement_pct"]:.1f}%',
                 transform=ax2.transAxes, fontsize=11, color='green',
                 fontweight='bold', ha='center', va='top',
                 bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgreen', alpha=0.3))

        # ========================================
        # 3. ИНДЕКС ПРОБОК (верхний правый)
        # ========================================
        ax3 = fig.add_subplot(gs[0, 2])
        categories = ['ДО', 'ПОСЛЕ']
        values = [results['congestion_before'], results['congestion_after']]
        bars = ax3.bar(categories, values, color=[color_before, color_after], alpha=0.8, edgecolor='black')
        ax3.set_ylabel('Индекс (0-10)', fontsize=9, fontweight='bold')
        ax3.set_title('3. Уровень пробок', fontsize=10, fontweight='bold', pad=10)
        ax3.grid(axis='y', alpha=0.3, linestyle='--')
        ax3.set_ylim(0, 10)
        ax3.tick_params(axis='both', which='major', labelsize=8)

        for bar in bars:
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width() / 2., height,
                     f'{height:.1f}',
                     ha='center', va='bottom', fontsize=8, fontweight='bold')

        ax3.text(0.5, 0.92, f'-{results["congestion_reduction_pct"]:.1f}%',
                 transform=ax3.transAxes, fontsize=11, color='green',
                 fontweight='bold', ha='center', va='top',
                 bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgreen', alpha=0.3))

        # ========================================
        # 4. ВЫБРОСЫ CO2 (средний левый - пирог)
        # ========================================
        ax4 = fig.add_subplot(gs[1, 0])

        sizes_before = [results['co2_cars_before_daily'], results['co2_buses_before_daily']]
        labels = ['Авто', 'Автобусы']
        colors_pie = ['#E74C3C', '#F39C12']

        wedges, texts, autotexts = ax4.pie(sizes_before, labels=labels, colors=colors_pie,
                                           autopct='%1.1f%%', startangle=90,
                                           textprops={'fontsize': 8, 'fontweight': 'bold'})
        ax4.set_title(f'4. CO2 ДО\n({results["co2_total_before_daily"]:.0f} т/день)',
                      fontsize=10, fontweight='bold', pad=10)

        # ========================================
        # 5. ВЫБРОСЫ CO2 ПОСЛЕ (средний центр - пирог)
        # ========================================
        ax5 = fig.add_subplot(gs[1, 1])

        sizes_after = [results['co2_cars_after_daily'], results['co2_buses_after_daily']]

        wedges, texts, autotexts = ax5.pie(sizes_after, labels=labels, colors=colors_pie,
                                           autopct='%1.1f%%', startangle=90,
                                           textprops={'fontsize': 8, 'fontweight': 'bold'})
        ax5.set_title(f'5. CO2 ПОСЛЕ\n({results["co2_total_after_daily"]:.0f} т/день)',
                      fontsize=10, fontweight='bold', pad=10)

        # ====================================
        # 6. ВЫБРОСЫ CO2
        # ====================================
        # ВАЖНО: Автобусы ездят по фиксированному расписанию независимо от загрузки
        # Поэтому общие выбросы автобусов НЕ меняются значительно
        # Снижение CO2 идет только за счет убранных автомобилей

        # Средняя дистанция поездки на авто в Астане
        avg_car_trip_distance = (24.79 / 60) * self.avg_highway_speed  # ~9.5 км

        # CO2 от автобусной сети (примерно постоянная величина)
        # Автобусы ездят по расписанию с фиксированным пробегом
        total_bus_fleet_km_daily = self.total_buses * 150  # примерно 150 км на автобус в день
        # Средний автобус выбрасывает ~1000 г CO2/км
        bus_co2_per_km = 1000  # грамм на км (для всего автобуса)
        co2_from_buses = total_bus_fleet_km_daily * bus_co2_per_km / 1_000_000  # тонны

        # CO2 от автомобилей ДО внедрения
        daily_car_trips = self.daily_active_cars * trips_per_person
        total_car_km_before = daily_car_trips * avg_car_trip_distance
        co2_from_cars_before = total_car_km_before * self.car_co2_per_km / 1_000_000  # тонны

        total_co2_before = co2_from_cars_before + co2_from_buses

        # CO2 от автомобилей ПОСЛЕ внедрения (меньше машин ездит)
        daily_car_trips_after = (self.daily_active_cars - results['cars_removed']) * trips_per_person
        total_car_km_after = daily_car_trips_after * avg_car_trip_distance
        co2_from_cars_after = total_car_km_after * self.car_co2_per_km / 1_000_000

        total_co2_after = co2_from_cars_after + co2_from_buses

        co2_reduction = total_co2_before - total_co2_after
        co2_reduction_yearly = co2_reduction * 365

        # Процентное соотношение для круговых диаграмм
        co2_cars_pct_before = (co2_from_cars_before / total_co2_before) * 100
        co2_buses_pct_before = (co2_from_buses / total_co2_before) * 100
        co2_cars_pct_after = (co2_from_cars_after / total_co2_after) * 100
        co2_buses_pct_after = (co2_from_buses / total_co2_after) * 100

        results['co2_cars_before_daily'] = round(co2_from_cars_before, 2)
        results['co2_buses_before_daily'] = round(co2_from_buses, 2)
        results['co2_total_before_daily'] = round(total_co2_before, 2)
        results['co2_cars_after_daily'] = round(co2_from_cars_after, 2)
        results['co2_buses_after_daily'] = round(co2_from_buses, 2)
        results['co2_total_after_daily'] = round(total_co2_after, 2)
        results['co2_reduction_daily'] = round(co2_reduction, 2)
        results['co2_reduction_yearly'] = round(co2_reduction_yearly, 2)
        results['co2_reduction_pct'] = round((co2_reduction / total_co2_before) * 100, 2)

        # ========================================
        # 7. MODAL SHIFT (нижний левый)
        # ========================================
        ax7 = fig.add_subplot(gs[2, 0])

        categories = ['Потенциал\n(56%)', 'Реальный\n(10%)']
        values = [results['potential_switchers_56pct'], results['realistic_switchers_10pct']]
        colors_bar = ['#95A5A6', color_after]
        bars = ax7.bar(categories, values, color=colors_bar, alpha=0.8, edgecolor='black')
        ax7.set_ylabel('Человек', fontsize=9, fontweight='bold')
        ax7.set_title('7. Modal Shift', fontsize=10, fontweight='bold', pad=10)
        ax7.grid(axis='y', alpha=0.3, linestyle='--')
        ax7.tick_params(axis='both', which='major', labelsize=8)

        for bar in bars:
            height = bar.get_height()
            ax7.text(bar.get_x() + bar.get_width() / 2., height,
                     f'{int(height / 1000)}k',
                     ha='center', va='bottom', fontsize=8, fontweight='bold')

        # ========================================
        # 8. ЗАГРУЗКА ДОРОГ (нижний центр)
        # ========================================
        ax8 = fig.add_subplot(gs[2, 1])

        categories = ['ДО', 'ПОСЛЕ']
        values = [results['load_before_pct'], results['load_after_pct']]
        bars = ax8.bar(categories, values, color=[color_before, color_after], alpha=0.8, edgecolor='black')
        ax8.set_ylabel('Загрузка, %', fontsize=9, fontweight='bold')
        ax8.set_title('8. Загрузка дорог (пик)', fontsize=10, fontweight='bold', pad=10)
        ax8.grid(axis='y', alpha=0.3, linestyle='--')
        ax8.axhline(y=100, color='red', linestyle='--', linewidth=1.5, label='100%')
        ax8.set_ylim(0, max(values) * 1.2)
        ax8.legend(loc='upper right', fontsize=7)
        ax8.tick_params(axis='both', which='major', labelsize=8)

        for bar in bars:
            height = bar.get_height()
            ax8.text(bar.get_x() + bar.get_width() / 2., height,
                     f'{height:.1f}%',
                     ha='center', va='bottom', fontsize=8, fontweight='bold')

        # ========================================
        # 9. ЭКОНОМИЧЕСКИЕ ВЫГОДЫ (нижний правый)
        # ========================================
        ax9 = fig.add_subplot(gs[2, 2])

        categories = ['Топливо', 'Парковка', 'ИТОГО']
        values = [
            results['fuel_cost_saved_yearly_mln'],
            results['parking_savings_yearly_mln'],
            results['total_economic_benefit_yearly_mln']
        ]
        colors_bar = [color_neutral, color_neutral, color_after]
        bars = ax9.bar(categories, values, color=colors_bar, alpha=0.8, edgecolor='black')
        ax9.set_ylabel('Млн ₸/год', fontsize=9, fontweight='bold')
        ax9.set_title('9. Экономия в год', fontsize=10, fontweight='bold', pad=10)
        ax9.grid(axis='y', alpha=0.3, linestyle='--')
        ax9.tick_params(axis='both', which='major', labelsize=8)

        for bar in bars:
            height = bar.get_height()
            ax9.text(bar.get_x() + bar.get_width() / 2., height,
                     f'{height:.0f}',
                     ha='center', va='bottom', fontsize=8, fontweight='bold')

        # Общий заголовок
        fig.suptitle('MULTI-AGENT СИСТЕМА: ЭФФЕКТ ДЛЯ АСТАНЫ',
                     fontsize=14, fontweight='bold', y=0.98)

        # Сохраняем
        plt.savefig('astana_traffic_analysis.png', dpi=200, bbox_inches='tight', facecolor='white')

        plt.show()

    def generate_report(self):
        """Генерация полного отчета"""
        print("="*100)
        print("РЕАЛИСТИЧНАЯ ОЦЕНКА ЭФФЕКТА MULTI-AGENT СИСТЕМЫ ДЛЯ ГОРОДА АСТАНА")
        print("="*100)
        print()

        print("📍 ПАРАМЕТРЫ ГОРОДА АСТАНА:")
        print("-"*100)
        print(f"  • Население:                                    {self.population:,} человек")
        print(f"  • Пользователи автобусов ежедневно:             {self.bus_passengers_daily:,} человек")
        print(f"  • Пользователи личного транспорта:              {self.private_transport_users:,} человек ({self.private_transport_share*100}%)")
        print(f"  • Активных автомобилей в день (оценка):         ~{self.daily_active_cars:,}")
        print(f"  • Количество автобусов:                         {self.total_buses}")
        print(f"  • Количество маршрутов:                         {self.total_routes}")
        print(f"  • Количество светофоров:                        {self.total_traffic_lights}")
        print(f"  • Средняя скорость автобусов:                   {self.avg_bus_speed} км/ч")
        print(f"  • Пиковая интенсивность движения:               {self.traffic_intensity:,} машин/час")
        print()

        results = self.calculate_impact()

        print("="*100)
        print("📊 РЕЗУЛЬТАТЫ ВНЕДРЕНИЯ СИСТЕМЫ")
        print("="*100)
        print()

        # 1. ПАССАЖИРОПОТОК
        print("1️⃣  ПАССАЖИРОПОТОК АВТОБУСОВ")
        print("-"*100)
        print(f"  • ДО внедрения:                                 {results['passengers_before']:,} чел/день")
        print(f"  • ПОСЛЕ внедрения:                              {results['passengers_after']:,} чел/день")
        print(f"  • Прирост:                                      +{results['passenger_increase']:,} чел/день (+{results['passenger_growth_pct']:.1f}%)")
        print()

        # 2. СКОРОСТЬ АВТОБУСОВ
        print("2️⃣  СКОРОСТЬ АВТОБУСОВ")
        print("-"*100)
        print(f"  • ДО внедрения:                                 {results['bus_speed_before']} км/ч")
        print(f"  • ПОСЛЕ внедрения:                              {results['bus_speed_after']} км/ч")
        print(f"  • Улучшение:                                    +{results['speed_improvement_pct']:.1f}%")
        print()

        # 3. MODAL SHIFT
        print("3️⃣  ПЕРЕХОД С ЛИЧНОГО ТРАНСПОРТА НА АВТОБУС")
        print("-"*100)
        print(f"  • Потенциально готовы (56% по опросам):         {results['potential_switchers_56pct']:,} человек")
        print(f"  • РЕАЛЬНО пересели (консервативная оценка 10%): {results['realistic_switchers_10pct']:,} человек")
        print(f"  • Убрано машин с дорог:                         {results['cars_removed']:,} автомобилей/день")
        print(f"  • Снижение пикового трафика:                    {results['traffic_reduction_pct']:.2f}%")
        print()

        # 4. ПРОБКИ
        print("4️⃣  ВЛИЯНИЕ НА ПРОБКИ")
        print("-"*100)
        print(f"  • Индекс пробок ДО:                             {results['congestion_before']:.1f}/10")
        print(f"  • Индекс пробок ПОСЛЕ:                          {results['congestion_after']:.1f}/10")
        print(f"  • Снижение индекса пробок:                      {results['congestion_reduction_pct']:.1f}%")
        print()

        # 5. ЭКОНОМИЯ ВРЕМЕНИ
        print("5️⃣  ЭКОНОМИЯ ВРЕМЕНИ")
        print("-"*100)
        print(f"  • Время поездки ДО:                             {results['trip_time_before']:.1f} минут")
        print(f"  • Время поездки ПОСЛЕ:                          {results['trip_time_after']:.1f} минут")
        print(f"  • Экономия на одну поездку:                     {results['time_saved_per_trip']:.2f} минут")
        print(f"  • Суммарная экономия в день:                    {results['total_time_saved_hours_daily']:,} часов")
        print(f"  • Суммарная экономия в год:                     {results['total_time_saved_hours_yearly']:,} часов")
        print(f"  • Эквивалент рабочих дней (8ч):                 {results['work_days_equivalent']:,} дней")
        print()
        print(f"  Дополнительно - экономия на поиске парковки:")
        print(f"  • В день:                                       {results['parking_search_hours_saved_daily']:,} часов")
        print(f"  • В год:                                        {results['parking_search_hours_yearly']:,} часов")
        print()

        # 6. ВЫБРОСЫ CO2
        print("6️⃣  ВЫБРОСЫ CO2")
        print("-"*100)
        print(f"  ДО ВНЕДРЕНИЯ:")
        print(f"    • От автомобилей:                             {results['co2_cars_before_daily']:.2f} тонн/день")
        print(f"    • От автобусов:                               {results['co2_buses_before_daily']:.2f} тонн/день")
        print(f"    • ИТОГО:                                      {results['co2_total_before_daily']:.2f} тонн/день")
        print()
        print(f"  ПОСЛЕ ВНЕДРЕНИЯ:")
        print(f"    • От автомобилей:                             {results['co2_cars_after_daily']:.2f} тонн/день")
        print(f"    • От автобусов:                               {results['co2_buses_after_daily']:.2f} тонн/день")
        print(f"    • ИТОГО:                                      {results['co2_total_after_daily']:.2f} тонн/день")
        print()
        print(f"  СНИЖЕНИЕ ВЫБРОСОВ:")
        print(f"    • В день:                                     {results['co2_reduction_daily']:.2f} тонн ({results['co2_reduction_pct']:.2f}%)")
        print(f"    • В год:                                      {results['co2_reduction_yearly']:,.2f} тонн")
        print()

        # 7. ЭКОНОМИЯ ТОПЛИВА
        print("7️⃣  ЭКОНОМИЯ ТОПЛИВА")
        print("-"*100)
        print(f"  • Экономия в день:                              {results['fuel_saved_daily_liters']:,} литров")
        print(f"  • Экономия в год:                               {results['fuel_saved_yearly_liters']:,} литров")
        print(f"  • Стоимость экономии в день:                    {results['fuel_cost_saved_daily']:,} тенге")
        print(f"  • Стоимость экономии в год:                     {results['fuel_cost_saved_yearly']:,} тенге")
        print(f"                                                  ({results['fuel_cost_saved_yearly_mln']:.1f} млн тенге)")
        print()

        # 8. ЗАГРУЗКА ДОРОГ
        print("8️⃣  ЗАГРУЗКА ДОРОЖНОЙ СЕТИ")
        print("-"*100)
        print(f"  • Пропускная способность (пик):                 {results['road_capacity_total']:,} машин/час")
        print(f"  • Пиковый трафик ДО:                            {results['traffic_peak_before']:,} машин/час ({results['load_before_pct']:.1f}%)")
        print(f"  • Пиковый трафик ПОСЛЕ:                         {results['traffic_peak_after']:,} машин/час ({results['load_after_pct']:.1f}%)")
        print(f"  • Высвобождено пропускной способности:          {results['capacity_freed_pct']:.1f}%")
        print()

        # 9. ЭКОНОМИЧЕСКИЕ ВЫГОДЫ
        print("9️⃣  ЭКОНОМИЧЕСКИЕ ВЫГОДЫ")
        print("-"*100)
        print(f"  Экономия на парковке (для переключившихся):")
        print(f"  • В день:                                       {results['parking_savings_daily']:,} тенге")
        print(f"  • В год:                                        {results['parking_savings_yearly']:,} тенге")
        print(f"                                                  ({results['parking_savings_yearly_mln']:.1f} млн тенге)")
        print()
        print(f"  ОБЩАЯ ЭКОНОМИЧЕСКАЯ ВЫГОДА:")
        print(f"  • Экономия топлива + парковка в год:            {results['total_economic_benefit_yearly']:,} тенге")
        print(f"                                                  ({results['total_economic_benefit_yearly_mln']:.1f} млн тенге)")
        print()

        # ЗАКЛЮЧЕНИЕ
        print("="*100)
        print("✅ ЗАКЛЮЧЕНИЕ")
        print("="*100)
        print()
        print("Реалистичная оценка внедрения Multi-Agent системы управления светофорами в Астане:")
        print()
        print(f"  ✓ Увеличение скорости автобусов на {results['speed_improvement_pct']:.1f}%")
        print(f"  ✓ Снижение уровня пробок на {results['congestion_reduction_pct']:.1f}%")
        print(f"  ✓ Прирост пассажиропотока на {results['passenger_growth_pct']:.1f}% (+{results['passenger_increase']:,} человек)")
        print(f"  ✓ Переход {results['realistic_switchers_10pct']:,} человек с авто на автобус (10% от потенциала)")
        print(f"  ✓ Сокращение использования {results['cars_removed']:,} автомобилей ежедневно")
        print(f"  ✓ Снижение выбросов CO2 на {results['co2_reduction_yearly']:,.0f} тонн в год")
        print(f"  ✓ Экономия {results['total_time_saved_hours_yearly']:,} часов городского времени в год")
        print(f"  ✓ Общая экономическая выгода: {results['total_economic_benefit_yearly_mln']:.1f} млн тенге в год")
        print("Система показывает значимый, но реалистичный эффект, подтвержденный")
        print("международной практикой внедрения интеллектуальных транспортных систем.")
        print("=" * 100)

        self.create_visualizations(results)


if __name__ == "__main__":
    analyzer = AstanaTrafficAnalysisRealistic()
    analyzer.generate_report()