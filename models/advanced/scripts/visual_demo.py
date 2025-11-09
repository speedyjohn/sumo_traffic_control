"""
Визуальная демонстрация работы Multi-Agent системы
Для презентаций и демо
"""
import os
import sys
import traci
import numpy as np
from stable_baselines3 import DQN
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Установи SUMO_HOME")


def demo_baseline(scenario, duration=800):
    """Демонстрация БЕЗ ИИ"""
    print("\n" + "=" * 80)
    print("🚦 ДЕМОНСТРАЦИЯ: ОБЫЧНОЕ УПРАВЛЕНИЕ (БЕЗ ИИ)")
    print("=" * 80)
    print("Сеть: 3x3 перекрестка (9 светофоров)")
    print("Управление: Фиксированные таймеры")
    print("Координация: НЕТ")
    print("=" * 80)
    input("\n▶️  Нажми Enter чтобы начать...")

    sumo_cmd = [
        "sumo-gui",
        "-c", f"{PROJECT_ROOT}/models/advanced/xmls/advanced.sumocfg",
        "--route-files", scenario,
        "--start",
        "--delay", "50",
        "--step-length", "1"
    ]

    traci.start(sumo_cmd)

    bus_waiting = []
    car_waiting = []

    print("\n⏳ Симуляция запущена...")
    print("💡 Обрати внимание:")
    print("   • 9 перекрестков работают независимо")
    print("   • Светофоры переключаются по таймеру")
    print("   • Нет координации между перекрестками")

    for step in range(duration):
        traci.simulationStep()

        if step % 100 == 0:
            vehicles = traci.vehicle.getIDList()
            buses = [v for v in vehicles if traci.vehicle.getTypeID(v) == 'bus']
            print(f"  Шаг {step}: ТС={len(vehicles)}, Автобусов={len(buses)}")

        # Статистика
        vehicles = traci.vehicle.getIDList()
        for veh_id in vehicles:
            waiting = traci.vehicle.getWaitingTime(veh_id)
            if waiting > 0:
                if traci.vehicle.getTypeID(veh_id) == 'bus':
                    bus_waiting.append(waiting)
                else:
                    car_waiting.append(waiting)

    print("\n✅ Симуляция завершена!")
    input("\n⏸️  Изучи результат в SUMO. Нажми Enter для продолжения...")

    traci.close()

    stats = {
        'bus_avg': np.mean(bus_waiting) if bus_waiting else 0,
        'car_avg': np.mean(car_waiting) if car_waiting else 0,
    }

    print("\n" + "=" * 80)
    print("📊 РЕЗУЛЬТАТЫ БЕЗ ИИ:")
    print(f"   Автобусы: {stats['bus_avg']:.2f}с")
    print(f"   Машины: {stats['car_avg']:.2f}с")
    print("=" * 80)

    return stats


def demo_multi_agent(scenario, duration=800):
    """Демонстрация С Multi-Agent ИИ"""
    print("\n" + "=" * 80)
    print("🤖 ДЕМОНСТРАЦИЯ: MULTI-AGENT УПРАВЛЕНИЕ (С ИИ)")
    print("=" * 80)
    print("Сеть: 3x3 перекрестка (9 светофоров)")
    print("Управление: 9 независимых AI-агентов")
    print("Координация: Общая обученная политика")
    print("=" * 80)
    input("\n▶️  Нажми Enter чтобы начать...")

    # Загружаем модель
    try:
        model = DQN.load(f"{PROJECT_ROOT}/models/advanced/model/multi_agent_model")
        print("✓ Загружена multi-agent модель")
    except:
        try:
            model = DQN.load(f"{PROJECT_ROOT}/models/simple/model/green_corridor_model")
            print("✓ Используется модель из simple/")
        except:
            print("❌ Модель не найдена!")
            return None

    from multi_agent_env import MultiAgentTrafficEnv

    env = MultiAgentTrafficEnv(
        f"{PROJECT_ROOT}/models/advanced/xmls/advanced.sumocfg",
        gui=True,
        route_file=scenario,
        use_pretrained=False
    )

    # Присваиваем модель всем агентам
    for agent in env.agents.values():
        agent.model = model

    obs, _ = env.reset()

    bus_waiting = []
    car_waiting = []

    print("\n⏳ AI-агенты работают...")
    print("💡 Обрати внимание:")
    print("   • Каждый агент управляет своим перекрестком")
    print("   • Решения принимаются в реальном времени")
    print("   • Агенты используют общую стратегию")

    for step in range(duration):
        # Каждый агент принимает решение
        actions = []
        for tl_id in env.traffic_lights:
            agent = env.agents[tl_id]
            agent_obs = agent.get_observation()
            action, _ = model.predict(agent_obs, deterministic=True)
            actions.append(action)

        obs, reward, terminated, truncated, _ = env.step(np.array(actions))

        if step % 100 == 0:
            try:
                vehicles = traci.vehicle.getIDList()
                buses = [v for v in vehicles if traci.vehicle.getTypeID(v) == 'bus']
                print(f"  Шаг {step}: ТС={len(vehicles)}, Автобусов={len(buses)}, Reward={reward:.2f}")
            except:
                pass

        # Статистика
        try:
            vehicles = traci.vehicle.getIDList()
            for veh_id in vehicles:
                waiting = traci.vehicle.getWaitingTime(veh_id)
                if waiting > 0:
                    if traci.vehicle.getTypeID(veh_id) == 'bus':
                        bus_waiting.append(waiting)
                    else:
                        car_waiting.append(waiting)
        except:
            pass

        if terminated or truncated:
            break

    print("\n✅ AI завершил работу!")
    input("\n⏸️  Изучи результат в SUMO. Нажми Enter для продолжения...")

    env.close()

    stats = {
        'bus_avg': np.mean(bus_waiting) if bus_waiting else 0,
        'car_avg': np.mean(car_waiting) if car_waiting else 0,
    }

    print("\n" + "=" * 80)
    print("📊 РЕЗУЛЬТАТЫ С MULTI-AGENT ИИ:")
    print(f"   Автобусы: {stats['bus_avg']:.2f}с")
    print(f"   Машины: {stats['car_avg']:.2f}с")
    print("=" * 80)

    return stats


def run_comparison_demo(scenario):
    """Полное сравнение БЕЗ и С ИИ"""
    print("\n" + "=" * 80)
    print("🎬 ВИЗУАЛЬНОЕ СРАВНЕНИЕ: MULTI-AGENT СИСТЕМА")
    print("=" * 80)
    print(f"Сценарий: {os.path.basename(scenario)}")
    print("\nСейчас будет показано:")
    print("  1️⃣  Обычное управление (фиксированные таймеры)")
    print("  2️⃣  Multi-Agent управление (9 AI-агентов)")
    print("  3️⃣  Сравнение результатов")
    print("\n💡 ОБРАТИ ВНИМАНИЕ:")
    print("   • Сколько времени автобусы стоят на красный")
    print("   • Как быстро рассасываются очереди")
    print("   • Координация между перекрестками")
    print("=" * 80)
    input("\nГотов? Нажми Enter...")

    # Часть 1: Baseline
    baseline_stats = demo_baseline(scenario, duration=600)

    if baseline_stats is None:
        return

    print("\n⏸️  Первая часть завершена!")
    input("Нажми Enter для запуска Multi-Agent...")

    # Часть 2: Multi-Agent
    ai_stats = demo_multi_agent(scenario, duration=600)

    if ai_stats is None:
        return

    # Итоговое сравнение
    bus_imp = ((baseline_stats['bus_avg'] - ai_stats['bus_avg'])
               / baseline_stats['bus_avg'] * 100)
    car_imp = ((baseline_stats['car_avg'] - ai_stats['car_avg'])
               / baseline_stats['car_avg'] * 100)

    print("\n" + "=" * 80)
    print("🏆 ИТОГОВОЕ СРАВНЕНИЕ")
    print("=" * 80)
    print("\n🚌 АВТОБУСЫ:")
    print(f"  БЕЗ ИИ:        {baseline_stats['bus_avg']:.2f}с")
    print(f"  Multi-Agent:   {ai_stats['bus_avg']:.2f}с")
    print(f"  Улучшение:     {bus_imp:+.1f}%")

    print("\n🚗 МАШИНЫ:")
    print(f"  БЕЗ ИИ:        {baseline_stats['car_avg']:.2f}с")
    print(f"  Multi-Agent:   {ai_stats['car_avg']:.2f}с")
    print(f"  Улучшение:     {car_imp:+.1f}%")

    print("\n" + "=" * 80)

    # Оценка
    avg_imp = (bus_imp + car_imp) / 2

    if avg_imp > 50:
        print("\n✅ ОТЛИЧНО! Multi-Agent система значительно эффективнее!")
        print("   Координация между агентами работает отлично.")
    elif avg_imp > 30:
        print("\n✅ ХОРОШО! Заметное улучшение управления трафиком.")
        print("   Multi-Agent подход показывает свою эффективность.")
    elif avg_imp > 0:
        print("\n⚠️ ЕСТЬ УЛУЧШЕНИЕ, но небольшое.")
        print("   Возможно нужно больше обучения.")
    else:
        print("\n❌ Multi-Agent система не показала улучшения.")
        print("   Рекомендуется переобучить модель.")

    print("=" * 80)


def quick_visual_test():
    """Быстрый визуальный тест (только с ИИ, 300 шагов)"""
    print("\n" + "=" * 80)
    print("⚡ БЫСТРЫЙ ТЕСТ MULTI-AGENT СИСТЕМЫ")
    print("=" * 80)
    print("Короткая демонстрация (300 шагов)")
    print("=" * 80)

    try:
        model = DQN.load(f"{PROJECT_ROOT}/models/advanced/model/multi_agent_model")
        print("✓ Загружена multi-agent модель")
    except:
        try:
            model = DQN.load(f"{PROJECT_ROOT}/models/simple/model/green_corridor_model")
            print("✓ Используется модель из simple/")
        except:
            print("❌ Модель не найдена!")
            return

    from multi_agent_env import MultiAgentTrafficEnv

    env = MultiAgentTrafficEnv(
        f"{PROJECT_ROOT}/models/advanced/xmls/advanced.sumocfg",
        gui=True,
        route_file=f"{PROJECT_ROOT}/models/advanced/xmls/advanced.rou.xml",
        use_pretrained=False
    )

    for agent in env.agents.values():
        agent.model = model

    obs, _ = env.reset()

    print("\n👀 Смотри:")
    print("   • 9 AI-агентов работают одновременно")
    print("   • Зеленые = автобусы (приоритет)")
    print("   • Желтые = обычные машины")
    print("\n▶️  Запускаю...")

    for step in range(300):
        actions = []
        for tl_id in env.traffic_lights:
            agent = env.agents[tl_id]
            agent_obs = agent.get_observation()
            action, _ = model.predict(agent_obs, deterministic=True)
            actions.append(action)

        obs, reward, terminated, truncated, _ = env.step(np.array(actions))

        if terminated or truncated:
            break

    print("\n✅ Тест завершен!")
    input("\n⏸️  ОКНО SUMO ОСТАНЕТСЯ ОТКРЫТЫМ. Нажми Enter чтобы закрыть...")

    env.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Визуальная демонстрация Multi-Agent")
    parser.add_argument("--mode", type=str, default="compare",
                        choices=["compare", "baseline", "multi-agent", "quick"],
                        help="Режим демонстрации")
    parser.add_argument("--scenario", type=str,
                        default=f"{PROJECT_ROOT}/models/advanced/xmls/advanced.rou.xml",
                        help="Файл сценария")

    args = parser.parse_args()

    if not os.path.exists(args.scenario):
        print(f"\n❌ Файл не найден: {args.scenario}")
        print("Сгенерируй сценарии:")
        print("  python generate_traffic.py --type all")
        sys.exit(1)

    if args.mode == "compare":
        run_comparison_demo(args.scenario)
    elif args.mode == "baseline":
        demo_baseline(args.scenario)
    elif args.mode == "multi-agent":
        demo_multi_agent(args.scenario)
    else:
        quick_visual_test()