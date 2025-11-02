import os
import sys
import traci
from stable_baselines3 import DQN
from models.simple.scripts import PROJECT_ROOT

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Установи переменную окружения SUMO_HOME")


def demo_without_ai(scenario=f"{PROJECT_ROOT}/models/simple/xmls/simple.rou.xml", duration=200):
    """
    Демонстрация БЕЗ ИИ
    """
    print("\n" + "=" * 70)
    print("🚦 ДЕМОНСТРАЦИЯ: ОБЫЧНОЕ УПРАВЛЕНИЕ СВЕТОФОРОМ")
    print("=" * 70)
    print("Светофор работает по фиксированному таймеру")
    print("Автобусы (зеленые) не имеют приоритета")
    print("=" * 70)
    input("\n▶️  Нажми Enter чтобы начать...")

    sumo_cmd = [
        "sumo-gui",
        "-c", f"{PROJECT_ROOT}/models/simple/xmls/simple.sumocfg",
        "--route-files", scenario,
        "--start",
        # УБРАЛИ --quit-on-end чтобы окно не закрывалось
        "--delay", "100",  # Замедляем для просмотра
        "--step-length", "1"
    ]

    traci.start(sumo_cmd)

    # Собираем статистику
    bus_waiting_times = []
    total_buses = 0

    print("\n⏳ Симуляция запущена... (смотри в окно SUMO)")
    print("💡 Обрати внимание на зеленые машины (автобусы)")

    for step in range(duration):
        traci.simulationStep()

        # Считаем время ожидания автобусов
        vehicles = traci.vehicle.getIDList()
        for veh_id in vehicles:
            if traci.vehicle.getTypeID(veh_id) == 'bus':
                waiting = traci.vehicle.getWaitingTime(veh_id)
                if waiting > 0:
                    bus_waiting_times.append(waiting)
                total_buses += 1

    # ДОБАВИЛИ: Пауза перед закрытием
    print("\n✅ Симуляция завершена!")
    print("📊 Сейчас будут показаны результаты...")
    input("\n⏸️  ОКНО SUMO ОСТАНЕТСЯ ОТКРЫТЫМ. Нажми Enter когда изучишь картину...")

    traci.close()

    avg_waiting = sum(bus_waiting_times) / len(bus_waiting_times) if bus_waiting_times else 0

    print("\n" + "=" * 70)
    print("📊 РЕЗУЛЬТАТЫ БЕЗ ИИ:")
    print(f"   Среднее ожидание автобусов: {avg_waiting:.2f} секунд")
    print(f"   Автобусов застряло: {len([w for w in bus_waiting_times if w > 10])}")
    print("=" * 70)

    return avg_waiting


def demo_with_ai(scenario=f"{PROJECT_ROOT}/models/simple/xmls/simple.rou.xml", duration=200):
    """
    Демонстрация С ИИ
    """
    print("\n" + "=" * 70)
    print("🤖 ДЕМОНСТРАЦИЯ: УМНОЕ УПРАВЛЕНИЕ С ИИ")
    print("=" * 70)
    print("ИИ анализирует трафик в реальном времени")
    print("Автобусы (зеленые) получают приоритет!")
    print("Смотри как ИИ переключает светофор для автобусов")
    print("=" * 70)
    input("\n▶️  Нажми Enter чтобы начать...")

    # Загружаем модель
    try:
        model = DQN.load(f"{PROJECT_ROOT}/models/simple/model/green_corridor_model")
    except FileNotFoundError:
        print("\n❌ Модель не найдена!")
        print("Запусти обучение: python green_corridor.py --mode train --steps 100000")
        return None

    from green_corridor import TrafficEnv

    env = TrafficEnv(f"{PROJECT_ROOT}/models/simple/xmls/simple.sumocfg", gui=True, route_file=scenario)
    obs, _ = env.reset()

    bus_waiting_times = []
    total_buses = 0

    print("\n⏳ ИИ работает... (смотри в окно SUMO)")
    print("💡 Обрати внимание как ИИ управляет светофором")

    for step in range(duration):
        # ИИ принимает решение
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, _ = env.step(action)

        # Считаем время ожидания автобусов
        try:
            vehicles = traci.vehicle.getIDList()
            for veh_id in vehicles:
                if traci.vehicle.getTypeID(veh_id) == 'bus':
                    waiting = traci.vehicle.getWaitingTime(veh_id)
                    if waiting > 0:
                        bus_waiting_times.append(waiting)
                    total_buses += 1
        except:
            pass

        if terminated or truncated:
            break

    # ДОБАВИЛИ: Пауза перед закрытием
    print("\n✅ ИИ завершил работу!")
    print("📊 Сейчас будут показаны результаты...")
    input("\n⏸️  ОКНО SUMO ОСТАНЕТСЯ ОТКРЫТЫМ. Нажми Enter когда изучишь картину...")

    env.close()

    avg_waiting = sum(bus_waiting_times) / len(bus_waiting_times) if bus_waiting_times else 0

    print("\n" + "=" * 70)
    print("📊 РЕЗУЛЬТАТЫ С ИИ:")
    print(f"   Среднее ожидание автобусов: {avg_waiting:.2f} секунд")
    print(f"   Автобусов застряло: {len([w for w in bus_waiting_times if w > 10])}")
    print("=" * 70)

    return avg_waiting


def run_comparison_demo(scenario=f"{PROJECT_ROOT}/models/simple/xmls/simple.rou.xml"):
    """
    Последовательная демонстрация БЕЗ и С ИИ
    """
    print("\n" + "=" * 70)
    print("🎬 ВИЗУАЛЬНОЕ СРАВНЕНИЕ ДЛЯ ПРЕЗЕНТАЦИИ")
    print("=" * 70)
    print(f"Сценарий: {scenario}")
    print("\nСейчас будет показано:")
    print("  1️⃣  Обычное управление светофором (БЕЗ ИИ)")
    print("  2️⃣  Умное управление с ИИ (С ИИ)")
    print("  3️⃣  Сравнение результатов")
    print("\n💡 СОВЕТ: Обрати внимание на:")
    print("   • Зеленые машины = автобусы")
    print("   • Как долго автобусы стоят на красный")
    print("   • Насколько быстрее проезжают с ИИ")
    print("=" * 70)
    input("\nГотов? Нажми Enter...")

    # Часть 1: БЕЗ ИИ
    baseline_waiting = demo_without_ai(scenario, duration=200)

    if baseline_waiting is None:
        return

    print("\n⏸️  Первая часть завершена!")
    input("Нажми Enter для запуска С ИИ...")

    # Часть 2: С ИИ
    ai_waiting = demo_with_ai(scenario, duration=200)

    if ai_waiting is None:
        return

    # Итоговое сравнение
    improvement = (baseline_waiting - ai_waiting) / baseline_waiting * 100

    print("\n" + "=" * 70)
    print("🏆 ИТОГОВОЕ СРАВНЕНИЕ")
    print("=" * 70)
    print(f"БЕЗ ИИ:  {baseline_waiting:.2f} сек (обычное управление)")
    print(f"С ИИ:    {ai_waiting:.2f} сек (умное управление)")
    print(f"\n📈 УЛУЧШЕНИЕ: {improvement:+.1f}%")

    if improvement > 30:
        print("\n✅ ОТЛИЧНО! Автобусы проезжают намного быстрее!")
        print("   ИИ успешно создает зеленый коридор для общественного транспорта.")
    elif improvement > 15:
        print("\n✅ ХОРОШО! Заметное улучшение для автобусов.")
        print("   ИИ эффективно управляет светофором.")
    elif improvement > 0:
        print("\n⚠️ СЛАБО. Есть улучшение, но небольшое.")
        print("   Возможно модель нуждается в дополнительном обучении.")
    else:
        print("\n❌ ИИ не помог. Модель не обучилась должным образом.")
        print("   Рекомендуется переобучить с большим количеством шагов.")

    print("=" * 70)


def quick_visual_test():
    """
    Быстрый визуальный тест (только С ИИ, 60 секунд)
    """
    print("\n" + "=" * 70)
    print("⚡ БЫСТРЫЙ ВИЗУАЛЬНЫЙ ТЕСТ")
    print("=" * 70)
    print("Короткая демонстрация работы ИИ (60 секунд)")
    print("=" * 70)

    try:
        model = DQN.load(f"{PROJECT_ROOT}/models/simple/model/green_corridor_model")
    except FileNotFoundError:
        print("\n❌ Модель не найдена!")
        print("Запусти: python green_corridor.py --mode train --steps 100000")
        return

    from green_corridor import TrafficEnv

    env = TrafficEnv("simple.sumocfg", gui=True, route_file="../xmls/simple.rou.xml")
    obs, _ = env.reset()

    print("\n👀 Смотри:")
    print("   • Зеленые = автобусы (приоритет)")
    print("   • Желтые = обычные машины")
    print("   • ИИ переключает светофор для автобусов")
    print("\n▶️  Запускаю...")

    for step in range(60):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, _ = env.step(action)

        if terminated or truncated:
            break

    print("\n✅ Тест завершен!")
    input("\n⏸️  ОКНО SUMO ОСТАНЕТСЯ ОТКРЫТЫМ. Нажми Enter чтобы закрыть...")

    env.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Визуальная демонстрация для презентации")
    parser.add_argument("--mode", type=str, default="compare",
                        choices=["compare", "without-ai", "with-ai", "quick"],
                        help="Режим демонстрации")
    parser.add_argument("--scenario", type=str, default=f"{PROJECT_ROOT}/models/simple/xmls/simple.rou.xml",
                        help="Файл сценария трафика")

    args = parser.parse_args()

    if args.mode == "compare":
        # Полное сравнение
        run_comparison_demo(args.scenario)
    elif args.mode == "without-ai":
        # Только БЕЗ ИИ
        demo_without_ai(args.scenario)
    elif args.mode == "with-ai":
        # Только С ИИ
        demo_with_ai(args.scenario)
    else:
        # Быстрый тест
        quick_visual_test()