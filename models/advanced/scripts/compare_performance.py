"""
Сравнение производительности Multi-Agent системы с baseline
"""
import os
import sys
import traci
import numpy as np
import matplotlib.pyplot as plt
from stable_baselines3 import DQN
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Установи SUMO_HOME")


def run_baseline(route_file, steps=1000):
    """Запуск БЕЗ ИИ (фиксированные светофоры)"""
    print(f"\n🚦 Baseline (без ИИ): {route_file}")

    sumo_cmd = [
        "sumo", "-c", f"{PROJECT_ROOT}/models/advanced/xmls/advanced.sumocfg",
        "--route-files", route_file,
        "--start", "--quit-on-end",
        "--waiting-time-memory", "1000",
        "--time-to-teleport", "-1",
        "--no-warnings", "true"
    ]

    traci.start(sumo_cmd)

    bus_waiting_times = []
    car_waiting_times = []
    total_vehicles = 0

    for step in range(steps):
        traci.simulationStep()

        vehicles = traci.vehicle.getIDList()
        total_vehicles = max(total_vehicles, len(vehicles))

        for veh_id in vehicles:
            waiting = traci.vehicle.getWaitingTime(veh_id)
            if waiting > 0:
                if traci.vehicle.getTypeID(veh_id) == 'bus':
                    bus_waiting_times.append(waiting)
                else:
                    car_waiting_times.append(waiting)

    traci.close()

    stats = {
        'bus_avg': np.mean(bus_waiting_times) if bus_waiting_times else 0,
        'car_avg': np.mean(car_waiting_times) if car_waiting_times else 0,
        'bus_max': np.max(bus_waiting_times) if bus_waiting_times else 0,
        'car_max': np.max(car_waiting_times) if car_waiting_times else 0,
        'total_vehicles': total_vehicles
    }

    print(f"  ✓ Автобусы: {stats['bus_avg']:.2f}с (макс: {stats['bus_max']:.1f}с)")
    print(f"  ✓ Машины: {stats['car_avg']:.2f}с (макс: {stats['car_max']:.1f}с)")
    print(f"  ✓ Всего ТС: {stats['total_vehicles']}")

    return stats


def run_multi_agent(route_file, steps=1000):
    """Запуск С Multi-Agent ИИ"""
    print(f"\n🤖 Multi-Agent (с ИИ): {route_file}")

    # Загружаем модель
    try:
        model = DQN.load(f"{PROJECT_ROOT}/models/advanced/model/multi_agent_model")
        print("  ✓ Загружена multi-agent модель")
    except:
        try:
            model = DQN.load(f"{PROJECT_ROOT}/models/simple/model/green_corridor_model")
            print("  ✓ Используется модель из simple/")
        except:
            print("  ❌ Модель не найдена!")
            return None

    from multi_agent_env import MultiAgentTrafficEnv

    env = MultiAgentTrafficEnv(
        f"{PROJECT_ROOT}/models/advanced/xmls/advanced.sumocfg",
        gui=False,
        route_file=route_file,
        use_pretrained=False
    )

    # Присваиваем модель всем агентам
    for agent in env.agents.values():
        agent.model = model

    obs, _ = env.reset()

    bus_waiting_times = []
    car_waiting_times = []
    total_vehicles = 0

    for step in range(steps):
        # Каждый агент принимает решение
        actions = []
        for tl_id in env.traffic_lights:
            agent = env.agents[tl_id]
            agent_obs = agent.get_observation()
            action, _ = model.predict(agent_obs, deterministic=True)
            actions.append(action)

        obs, reward, terminated, truncated, _ = env.step(np.array(actions))

        # Собираем статистику
        try:
            vehicles = traci.vehicle.getIDList()
            total_vehicles = max(total_vehicles, len(vehicles))

            for veh_id in vehicles:
                waiting = traci.vehicle.getWaitingTime(veh_id)
                if waiting > 0:
                    if traci.vehicle.getTypeID(veh_id) == 'bus':
                        bus_waiting_times.append(waiting)
                    else:
                        car_waiting_times.append(waiting)
        except:
            pass

        if terminated or truncated:
            break

    env.close()

    stats = {
        'bus_avg': np.mean(bus_waiting_times) if bus_waiting_times else 0,
        'car_avg': np.mean(car_waiting_times) if car_waiting_times else 0,
        'bus_max': np.max(bus_waiting_times) if bus_waiting_times else 0,
        'car_max': np.max(car_waiting_times) if car_waiting_times else 0,
        'total_vehicles': total_vehicles
    }

    print(f"  ✓ Автобусы: {stats['bus_avg']:.2f}с (макс: {stats['bus_max']:.1f}с)")
    print(f"  ✓ Машины: {stats['car_avg']:.2f}с (макс: {stats['car_max']:.1f}с)")
    print(f"  ✓ Всего ТС: {stats['total_vehicles']}")

    return stats


def compare_scenarios():
    """Сравнение на разных сценариях"""

    scenarios = [
        (f"{PROJECT_ROOT}/models/advanced/xmls/advanced.rou.xml", "Balanced"),
        (f"{PROJECT_ROOT}/models/advanced/xmls/advanced_rush.rou.xml", "Rush Hour"),
        (f"{PROJECT_ROOT}/models/advanced/xmls/advanced_bus.rou.xml", "Bus Priority"),
    ]

    results = {
        'scenarios': [],
        'baseline_bus': [],
        'baseline_car': [],
        'ai_bus': [],
        'ai_car': [],
    }

    print("\n" + "=" * 70)
    print("🔬 СРАВНЕНИЕ ПРОИЗВОДИТЕЛЬНОСТИ: ADVANCED MULTI-AGENT")
    print("=" * 70)

    for route_file, name in scenarios:
        if not os.path.exists(route_file):
            print(f"\n⚠️ Файл не найден: {route_file}")
            print("Запусти: python generate_traffic.py --type all")
            continue

        print(f"\n{'=' * 70}")
        print(f"Сценарий: {name}")
        print('=' * 70)

        # Baseline
        baseline_stats = run_baseline(route_file, steps=1000)

        # Multi-Agent
        ai_stats = run_multi_agent(route_file, steps=1000)

        if ai_stats is None:
            continue

        # Сохраняем результаты
        results['scenarios'].append(name)
        results['baseline_bus'].append(baseline_stats['bus_avg'])
        results['baseline_car'].append(baseline_stats['car_avg'])
        results['ai_bus'].append(ai_stats['bus_avg'])
        results['ai_car'].append(ai_stats['car_avg'])

        # Улучшения
        bus_imp = ((baseline_stats['bus_avg'] - ai_stats['bus_avg'])
                   / baseline_stats['bus_avg'] * 100)
        car_imp = ((baseline_stats['car_avg'] - ai_stats['car_avg'])
                   / baseline_stats['car_avg'] * 100)

        print(f"\n📊 УЛУЧШЕНИЯ:")
        print(f"  • Автобусы: {bus_imp:+.1f}%")
        print(f"  • Машины: {car_imp:+.1f}%")

    # Визуализация
    if len(results['scenarios']) > 0:
        plot_comparison(results)
        generate_report(results)

    return results


def plot_comparison(results):
    """Создание графиков"""

    os.makedirs(f"{PROJECT_ROOT}/models/advanced/comparison", exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    x = np.arange(len(results['scenarios']))
    width = 0.35

    # График 1: Автобусы
    axes[0, 0].bar(x - width / 2, results['baseline_bus'], width,
                   label='Без ИИ', color='#ff6b6b', alpha=0.8)
    axes[0, 0].bar(x + width / 2, results['ai_bus'], width,
                   label='Multi-Agent', color='#4ecdc4', alpha=0.8)
    axes[0, 0].set_ylabel('Среднее ожидание (сек)', fontsize=11)
    axes[0, 0].set_title('🚌 Время ожидания АВТОБУСОВ', fontsize=12, fontweight='bold')
    axes[0, 0].set_xticks(x)
    axes[0, 0].set_xticklabels(results['scenarios'])
    axes[0, 0].legend()
    axes[0, 0].grid(axis='y', alpha=0.3)

    # График 2: Машины
    axes[0, 1].bar(x - width / 2, results['baseline_car'], width,
                   label='Без ИИ', color='#ff6b6b', alpha=0.8)
    axes[0, 1].bar(x + width / 2, results['ai_car'], width,
                   label='Multi-Agent', color='#4ecdc4', alpha=0.8)
    axes[0, 1].set_ylabel('Среднее ожидание (сек)', fontsize=11)
    axes[0, 1].set_title('🚗 Время ожидания МАШИН', fontsize=12, fontweight='bold')
    axes[0, 1].set_xticks(x)
    axes[0, 1].set_xticklabels(results['scenarios'])
    axes[0, 1].legend()
    axes[0, 1].grid(axis='y', alpha=0.3)

    # График 3: Улучшения автобусов
    bus_improvements = [
        ((results['baseline_bus'][i] - results['ai_bus'][i])
         / results['baseline_bus'][i] * 100)
        for i in range(len(results['scenarios']))
    ]
    axes[1, 0].bar(x, bus_improvements, color='#51cf66', alpha=0.8)
    axes[1, 0].set_ylabel('Улучшение (%)', fontsize=11)
    axes[1, 0].set_title('📈 Улучшение для автобусов', fontsize=12, fontweight='bold')
    axes[1, 0].set_xticks(x)
    axes[1, 0].set_xticklabels(results['scenarios'])
    axes[1, 0].axhline(y=0, color='black', linestyle='--', linewidth=0.5)
    axes[1, 0].grid(axis='y', alpha=0.3)

    # График 4: Улучшения машин
    car_improvements = [
        ((results['baseline_car'][i] - results['ai_car'][i])
         / results['baseline_car'][i] * 100)
        for i in range(len(results['scenarios']))
    ]
    axes[1, 1].bar(x, car_improvements, color='#51cf66', alpha=0.8)
    axes[1, 1].set_ylabel('Улучшение (%)', fontsize=11)
    axes[1, 1].set_title('📈 Улучшение для машин', fontsize=12, fontweight='bold')
    axes[1, 1].set_xticks(x)
    axes[1, 1].set_xticklabels(results['scenarios'])
    axes[1, 1].axhline(y=0, color='black', linestyle='--', linewidth=0.5)
    axes[1, 1].grid(axis='y', alpha=0.3)

    plt.tight_layout()

    output_file = f"{PROJECT_ROOT}/models/advanced/comparison/comparison_results.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ Графики сохранены: {output_file}")
    plt.show()


def generate_report(results):
    """Генерация текстового отчета"""

    report = []
    report.append("=" * 80)
    report.append("ИТОГОВЫЙ ОТЧЕТ: ADVANCED MULTI-AGENT vs BASELINE")
    report.append("=" * 80)
    report.append(f"\nСеть: 3x3 перекрестка (9 светофоров)")
    report.append(f"Агентов: 9 независимых")
    report.append("")

    for i, scenario in enumerate(results['scenarios']):
        report.append(f"\n{'=' * 80}")
        report.append(f"Сценарий: {scenario}")
        report.append("-" * 80)

        baseline_bus = results['baseline_bus'][i]
        ai_bus = results['ai_bus'][i]
        bus_imp = (baseline_bus - ai_bus) / baseline_bus * 100

        baseline_car = results['baseline_car'][i]
        ai_car = results['ai_car'][i]
        car_imp = (baseline_car - ai_car) / baseline_car * 100

        report.append("\n🚌 АВТОБУСЫ:")
        report.append(f"  Baseline:     {baseline_bus:.2f}с")
        report.append(f"  Multi-Agent:  {ai_bus:.2f}с")
        report.append(f"  Улучшение:    {bus_imp:+.1f}%")

        report.append("\n🚗 МАШИНЫ:")
        report.append(f"  Baseline:     {baseline_car:.2f}с")
        report.append(f"  Multi-Agent:  {ai_car:.2f}с")
        report.append(f"  Улучшение:    {car_imp:+.1f}%")

    # Средние улучшения
    avg_bus_imp = np.mean([
        (results['baseline_bus'][i] - results['ai_bus'][i]) / results['baseline_bus'][i] * 100
        for i in range(len(results['scenarios']))
    ])

    avg_car_imp = np.mean([
        (results['baseline_car'][i] - results['ai_car'][i]) / results['baseline_car'][i] * 100
        for i in range(len(results['scenarios']))
    ])

    report.append("\n" + "=" * 80)
    report.append("📊 СРЕДНЕЕ УЛУЧШЕНИЕ ПО ВСЕМ СЦЕНАРИЯМ:")
    report.append("-" * 80)
    report.append(f"  Автобусы:  {avg_bus_imp:+.1f}%")
    report.append(f"  Машины:    {avg_car_imp:+.1f}%")
    report.append("=" * 80)

    report_text = "\n".join(report)

    # Сохраняем
    output_file = f"{PROJECT_ROOT}/models/advanced/comparison/comparison_report.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(report_text)
    print(f"\n✓ Отчет сохранен: {output_file}")


if __name__ == "__main__":
    try:
        results = compare_scenarios()

        print("\n" + "=" * 70)
        print("✅ СРАВНЕНИЕ ЗАВЕРШЕНО!")
        print("=" * 70)
        print("\nСоздано:")
        print("  • comparison_results.png - графики")
        print("  • comparison_report.txt - текстовый отчет")

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()