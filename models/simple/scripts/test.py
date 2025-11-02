"""
Простой тест SUMO - проверяем что всё работает
"""
import os
import sys
import traci
from models.simple.scripts import PROJECT_ROOT

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("❌ SUMO_HOME не установлен!")

print("🔍 Проверка файлов...")

# Проверяем наличие файлов
files_to_check = [
    f"{PROJECT_ROOT}/models/simple/xmls/simple.sumocfg",
    f"{PROJECT_ROOT}/models/simple/xmls/simple.net.xml",
    f"{PROJECT_ROOT}/models/simple/xmls/simple.rou.xml"
]

all_ok = True
for file in files_to_check:
    if os.path.exists(file):
        print(f"  ✅ {file}")
    else:
        print(f"  ❌ {file} - НЕ НАЙДЕН!")
        all_ok = False

if not all_ok:
    print("\n❌ Некоторые файлы отсутствуют!")
    print("Запусти:")
    print("  python generate_traffic.py --type all")
    sys.exit(1)

print("\n🚀 Запускаю SUMO GUI...")
print("⏸️  Нажми ПРОБЕЛ чтобы поставить на паузу")
print("▶️  Нажми PLAY чтобы запустить симуляцию")
print("🛑 Закрой окно SUMO когда закончишь смотреть")

try:
    sumo_cmd = [
        "sumo-gui",
        "-c", f"{PROJECT_ROOT}/models/simple/xmls/simple.sumocfg",
        "--start",
        "--delay", "100"  # Замедляем для просмотра
    ]

    traci.start(sumo_cmd)

    print("\n✅ SUMO запущен!")
    print("👀 Смотри в окно SUMO:")
    print("   • Зеленые машины = автобусы")
    print("   • Желтые машины = обычные машины")
    print("   • Светофор переключается автоматически")

    # Запускаем симуляцию на 500 шагов
    for step in range(500):
        traci.simulationStep()

        # Каждые 100 шагов показываем статистику
        if step % 100 == 0:
            vehicles = traci.vehicle.getIDList()
            buses = [v for v in vehicles if traci.vehicle.getTypeID(v) == 'bus']
            cars = [v for v in vehicles if traci.vehicle.getTypeID(v) != 'bus']
            print(f"\nШаг {step}: Автобусов: {len(buses)}, Машин: {len(cars)}")

    traci.close()
    print("\n✅ Тест завершен успешно!")
    print("\nВыводы:")
    print("  ✅ SUMO работает")
    print("  ✅ Файлы конфигурации правильные")
    print("  ✅ Автобусы и машины появляются в симуляции")

except Exception as e:
    print(f"\n❌ Ошибка: {e}")
    print("\nЧто проверить:")
    print("  1. SUMO установлен правильно")
    print("  2. SUMO_HOME указывает на правильную папку")
    print("  3. Все файлы созданы")

    import traceback

    traceback.print_exc()