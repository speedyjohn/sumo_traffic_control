import os
import sys
import traci
import numpy as np
import matplotlib.pyplot as plt
from stable_baselines3 import DQN
from models.simple.scripts import PROJECT_ROOT

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Установи переменную окружения SUMO_HOME")


def run_baseline(route_file, steps=300, gui=False):
    """
    Запуск симуляции БЕЗ ИИ (стандартное управление светофором)

    gui: True для визуализации в SUMO GUI
    """
    print(f"\n🚦 Запуск базовой симуляции (без ИИ): {route_file}")
    if gui:
        print("   👀 Открывается GUI - смотри как работает БЕЗ ИИ")

    sumo_binary = "sumo-gui" if gui else "sumo"
    sumo_cmd = [sumo_binary, "-c", f"{PROJECT_ROOT}/models/simple/xmls/simple.sumocfg",
                "--route-files", route_file,
                "--start", "--quit-on-end",
                "--waiting-time-memory", "1000",
                "--time-to-teleport", "-1"]

    if gui:
        sumo_cmd.extend(["--delay", "100"])  # Замедляем для просмотра

    traci.start(sumo_cmd)

    bus_waiting_times = []
    car_waiting_times = []
    total_waiting_time = 0

    for step in range(steps):
        traci.simulationStep()

        # Собираем статистику
        vehicles = traci.vehicle.getIDList()
        for veh_id in vehicles:
            waiting_time = traci.vehicle.getWaitingTime(veh_id)
            total_waiting_time += waiting_time

            if traci.vehicle.getTypeID(veh_id) == 'bus':
                bus_waiting_times.append(waiting_time)
            else:
                car_waiting_times.append(waiting_time)

    traci.close()

    stats = {
        'total_waiting': total_waiting_time,
        'bus_avg_waiting': np.mean(bus_waiting_times) if bus_waiting_times else 0,
        'car_avg_waiting': np.mean(car_waiting_times) if car_waiting_times else 0,
        'bus_count': len([t for t in bus_waiting_times if t > 0]),
        'car_count': len([t for t in car_waiting_times if t > 0]),
    }

    print(f"  ✓ Среднее ожидание автобусов: {stats['bus_avg_waiting']:.2f}с")
    print(f"  ✓ Среднее ожидание машин: {stats['car_avg_waiting']:.2f}с")

    return stats


def run_with_ai(route_file, model_path, steps=300):
    """
    Запуск симуляции С ИИ
    """
    print(f"\n🤖 Запуск симуляции с ИИ: {route_file}")

    # Загружаем модель
    model = DQN.load(model_path)

    # Импортируем среду
    from .green_corridor import TrafficEnv

    env = TrafficEnv(f"{PROJECT_ROOT}/models/simple/xmls/simple.sumocfg", gui=False, route_file=route_file)
    obs, _ = env.reset()

    bus_waiting_times = []
    car_waiting_times = []
    total_waiting_time = 0

    for step in range(steps):
        # ИИ принимает решение
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, _ = env.step(action)

        # Собираем статистику
        vehicles = traci.vehicle.getIDList()
        for veh_id in vehicles:
            waiting_time = traci.vehicle.getWaitingTime(veh_id)
            total_waiting_time += waiting_time

            if traci.vehicle.getTypeID(veh_id) == 'bus':
                bus_waiting_times.append(waiting_time)
            else:
                car_waiting_times.append(waiting_time)

        if terminated or truncated:
            break

    env.close()

    stats = {
        'total_waiting': total_waiting_time,
        'bus_avg_waiting': np.mean(bus_waiting_times) if bus_waiting_times else 0,
        'car_avg_waiting': np.mean(car_waiting_times) if car_waiting_times else 0,
        'bus_count': len([t for t in bus_waiting_times if t > 0]),
        'car_count': len([t for t in car_waiting_times if t > 0]),
    }

    print(f"  ✓ Среднее ожидание автобусов: {stats['bus_avg_waiting']:.2f}с")
    print(f"  ✓ Среднее ожидание машин: {stats['car_avg_waiting']:.2f}с")

    return stats


def compare_scenarios():
    """
    Сравнивает производительность на разных сценариях
    """
    scenarios = [
        f"{PROJECT_ROOT}/models/simple/xmls/simple.rou.xml",
        f"{PROJECT_ROOT}/models/simple/xmls/rush_hour.rou.xml",
        f"{PROJECT_ROOT}/models/simple/xmls/bus_priority.rou.xml",
    ]

    results = {
        'scenarios': [],
        'baseline_bus': [],
        'baseline_car': [],
        'ai_bus': [],
        'ai_car': [],
    }

    for scenario in scenarios:
        print(f"\n{'=' * 60}")
        print(f"Тестирование сценария: {scenario}")
        print('=' * 60)

        # Базовая версия
        baseline_stats = run_baseline(scenario, steps=300)

        # С ИИ
        ai_stats = run_with_ai(scenario, f"{PROJECT_ROOT}/models/simple/model/green_corridor_model", steps=300)

        # Сохраняем результаты
        results['scenarios'].append(scenario.replace('.rou.xml', ''))
        results['baseline_bus'].append(baseline_stats['bus_avg_waiting'])
        results['baseline_car'].append(baseline_stats['car_avg_waiting'])
        results['ai_bus'].append(ai_stats['bus_avg_waiting'])
        results['ai_car'].append(ai_stats['car_avg_waiting'])

        # Процент улучшения
        bus_improvement = ((baseline_stats['bus_avg_waiting'] - ai_stats['bus_avg_waiting'])
                           / baseline_stats['bus_avg_waiting'] * 100)
        car_improvement = ((baseline_stats['car_avg_waiting'] - ai_stats['car_avg_waiting'])
                           / baseline_stats['car_avg_waiting'] * 100)

        print(f"\n📊 Улучшение:")
        print(f"  • Автобусы: {bus_improvement:+.1f}%")
        print(f"  • Машины: {car_improvement:+.1f}%")

    # Визуализация
    plot_comparison(results)

    return results


def plot_comparison(results):
    """
    Создает графики сравнения
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    x = np.arange(len(results['scenarios']))
    width = 0.35

    # График для автобусов
    ax1.bar(x - width / 2, results['baseline_bus'], width, label='Без ИИ', color='#ff6b6b')
    ax1.bar(x + width / 2, results['ai_bus'], width, label='С ИИ', color='#4ecdc4')
    ax1.set_ylabel('Среднее время ожидания (сек)')
    ax1.set_title('Время ожидания АВТОБУСОВ')
    ax1.set_xticks(x)
    ax1.set_xticklabels(results['scenarios'], rotation=15)
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)

    # График для машин
    ax2.bar(x - width / 2, results['baseline_car'], width, label='Без ИИ', color='#ff6b6b')
    ax2.bar(x + width / 2, results['ai_car'], width, label='С ИИ', color='#4ecdc4')
    ax2.set_ylabel('Среднее время ожидания (сек)')
    ax2.set_title('Время ожидания МАШИН')
    ax2.set_xticks(x)
    ax2.set_xticklabels(results['scenarios'], rotation=15)
    ax2.legend()
    ax2.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(f'{PROJECT_ROOT}/models/simple/comparison/comparison_results.png', dpi=300, bbox_inches='tight')
    print(f"\n✓ График сохранен: comparison_results.png")
    plt.show()


def generate_report(results):
    """
    Генерирует текстовый отчет
    """
    report = []
    report.append("\n" + "=" * 70)
    report.append("ИТОГОВЫЙ ОТЧЕТ: СРАВНЕНИЕ ПРОИЗВОДИТЕЛЬНОСТИ")
    report.append("=" * 70)

    for i, scenario in enumerate(results['scenarios']):
        report.append(f"\nСценарий: {scenario}")
        report.append("-" * 70)

        bus_baseline = results['baseline_bus'][i]
        bus_ai = results['ai_bus'][i]
        bus_improvement = (bus_baseline - bus_ai) / bus_baseline * 100

        car_baseline = results['baseline_car'][i]
        car_ai = results['ai_car'][i]
        car_improvement = (car_baseline - car_ai) / car_baseline * 100

        report.append(f"АВТОБУСЫ:")
        report.append(f"  Без ИИ:  {bus_baseline:.2f}с")
        report.append(f"  С ИИ:    {bus_ai:.2f}с")
        report.append(f"  Улучшение: {bus_improvement:+.1f}%")

        report.append(f"\nМАШИНЫ:")
        report.append(f"  Без ИИ:  {car_baseline:.2f}с")
        report.append(f"  С ИИ:    {car_ai:.2f}с")
        report.append(f"  Улучшение: {car_improvement:+.1f}%")

    report.append("\n" + "=" * 70)

    # Средние значения
    avg_bus_improvement = np.mean([
        (results['baseline_bus'][i] - results['ai_bus'][i]) / results['baseline_bus'][i] * 100
        for i in range(len(results['scenarios']))
    ])

    avg_car_improvement = np.mean([
        (results['baseline_car'][i] - results['ai_car'][i]) / results['baseline_car'][i] * 100
        for i in range(len(results['scenarios']))
    ])

    report.append(f"СРЕДНЕЕ УЛУЧШЕНИЕ:")
    report.append(f"  Автобусы: {avg_bus_improvement:+.1f}%")
    report.append(f"  Машины:   {avg_car_improvement:+.1f}%")
    report.append("=" * 70)

    report_text = "\n".join(report)

    # Сохраняем в файл
    with open(f"{PROJECT_ROOT}/models/simple/comparison/comparison_report.txt", "w", encoding="utf-8") as f:
        f.write(report_text)

    print(report_text)
    print(f"\n✓ Отчет сохранен: comparison_report.txt")


if __name__ == "__main__":
    print("🚀 СРАВНЕНИЕ ПРОИЗВОДИТЕЛЬНОСТИ: ИИ vs БАЗОВАЯ СИСТЕМА")

    try:
        results = compare_scenarios()
        generate_report(results)

        print("\n" + "=" * 70)
        print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!")
        print("=" * 70)

    except FileNotFoundError as e:
        print(f"\n❌ Ошибка: {e}")
        print("Убедись что:")
        print("  1. Модель обучена (green_corridor_model.zip существует)")
        print("  2. Сценарии сгенерированы (simple.rou.xml и др.)")
        print("\nЗапусти сначала:")
        print("  python generate_traffic.py --type all")
        print("  python green_corridor.py --mode train")