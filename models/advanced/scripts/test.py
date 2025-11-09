"""
Быстрый тест установки Advanced модели
Проверяет что все файлы на месте и SUMO работает
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def check_color(text, status):
    """Цветной вывод"""
    colors = {
        'ok': '\033[92m',  # Зеленый
        'error': '\033[91m',  # Красный
        'warning': '\033[93m',  # Желтый
        'end': '\033[0m'  # Сброс
    }

    if status == 'ok':
        return f"{colors['ok']}✅ {text}{colors['end']}"
    elif status == 'error':
        return f"{colors['error']}❌ {text}{colors['end']}"
    else:
        return f"{colors['warning']}⚠️  {text}{colors['end']}"


print("\n" + "=" * 70)
print("🔍 ПРОВЕРКА УСТАНОВКИ ADVANCED МОДЕЛИ")
print("=" * 70)

errors = []
warnings = []

# 1. Проверка SUMO_HOME
print("\n1️⃣  Проверка SUMO_HOME...")
if 'SUMO_HOME' in os.environ:
    print(check_color(f"SUMO_HOME = {os.environ['SUMO_HOME']}", 'ok'))
else:
    print(check_color("SUMO_HOME не установлен!", 'error'))
    errors.append("Установи SUMO_HOME")

# 2. Проверка структуры папок
print("\n2️⃣  Проверка структуры папок...")
required_dirs = [
    f"{PROJECT_ROOT}/models/advanced/xmls",
    f"{PROJECT_ROOT}/models/advanced/scripts",
    f"{PROJECT_ROOT}/models/advanced/model",
    f"{PROJECT_ROOT}/models/advanced/comparison",
]

for dir_path in required_dirs:
    if os.path.exists(dir_path):
        print(check_color(f"{dir_path}", 'ok'))
    else:
        print(check_color(f"{dir_path} - НЕ НАЙДЕНА", 'error'))
        errors.append(f"Создай папку: {dir_path}")

# 3. Проверка XML файлов
print("\n3️⃣  Проверка XML файлов...")
xml_files = [
    f"{PROJECT_ROOT}/models/advanced/xmls/advanced.nod.xml",
    f"{PROJECT_ROOT}/models/advanced/xmls/advanced.edg.xml",
    f"{PROJECT_ROOT}/models/advanced/xmls/advanced.sumocfg",
]

for file_path in xml_files:
    if os.path.exists(file_path):
        print(check_color(f"{os.path.basename(file_path)}", 'ok'))
    else:
        print(check_color(f"{os.path.basename(file_path)} - НЕ НАЙДЕН", 'error'))
        errors.append(f"Создай файл: {file_path}")

# 4. Проверка сети SUMO
print("\n4️⃣  Проверка сети SUMO...")
net_file = f"{PROJECT_ROOT}/models/advanced/xmls/advanced.net.xml"
if os.path.exists(net_file):
    size = os.path.getsize(net_file)
    print(check_color(f"advanced.net.xml ({size / 1024:.1f} KB)", 'ok'))
else:
    print(check_color("advanced.net.xml НЕ НАЙДЕН", 'warning'))
    warnings.append(
        "Запусти: netconvert --node-files=advanced.nod.xml --edge-files=advanced.edg.xml --output-file=advanced.net.xml")

# 5. Проверка Python скриптов
print("\n5️⃣  Проверка Python скриптов...")
python_files = [
    f"{PROJECT_ROOT}/models/advanced/scripts/__init__.py",
    f"{PROJECT_ROOT}/models/advanced/scripts/multi_agent_env.py",
    f"{PROJECT_ROOT}/models/advanced/scripts/generate_traffic.py",
    f"{PROJECT_ROOT}/models/advanced/scripts/compare_performance.py",
    f"{PROJECT_ROOT}/models/advanced/scripts/visual_demo.py",
]

for file_path in python_files:
    if os.path.exists(file_path):
        print(check_color(f"{os.path.basename(file_path)}", 'ok'))
    else:
        print(check_color(f"{os.path.basename(file_path)} - НЕ НАЙДЕН", 'error'))
        errors.append(f"Создай файл: {file_path}")

# 6. Проверка маршрутов трафика
print("\n6️⃣  Проверка маршрутов трафика...")
route_file = f"{PROJECT_ROOT}/models/advanced/xmls/advanced.rou.xml"
if os.path.exists(route_file):
    print(check_color("advanced.rou.xml", 'ok'))
else:
    print(check_color("advanced.rou.xml НЕ НАЙДЕН", 'warning'))
    warnings.append("Запусти: python generate_traffic.py --type all")

# 7. Проверка модели
print("\n7️⃣  Проверка обученной модели...")
model_files = [
    f"{PROJECT_ROOT}/models/advanced/model/multi_agent_model.zip",
    f"{PROJECT_ROOT}/models/simple/model/green_corridor_model.zip"
]

model_found = False
for model_file in model_files:
    if os.path.exists(model_file):
        print(check_color(f"{os.path.basename(model_file)}", 'ok'))
        model_found = True
        break

if not model_found:
    print(check_color("Модели не найдены", 'warning'))
    warnings.append("Обучи модель: python multi_agent_env.py --mode train --steps 200000")

# 8. Проверка зависимостей Python
print("\n8️⃣  Проверка Python зависимостей...")
required_packages = [
    'numpy',
    'gymnasium',
    'stable_baselines3',
    'matplotlib'
]

for package in required_packages:
    try:
        __import__(package)
        print(check_color(f"{package}", 'ok'))
    except ImportError:
        print(check_color(f"{package} - НЕ УСТАНОВЛЕН", 'error'))
        errors.append(f"Установи: pip install {package}")

# Итоги
print("\n" + "=" * 70)
print("📊 РЕЗУЛЬТАТЫ ПРОВЕРКИ")
print("=" * 70)

if len(errors) == 0 and len(warnings) == 0:
    print(check_color("\n🎉 ВСЕ ОТЛИЧНО! Система готова к работе!", 'ok'))
    print("\nСледующие шаги:")
    print("  1. python generate_traffic.py --type all (если еще не сделано)")
    print("  2. python multi_agent_env.py --mode train --steps 200000")
    print("  3. python multi_agent_env.py --mode test")
    print("  4. python visual_demo.py --mode compare")
else:
    if len(errors) > 0:
        print(check_color(f"\n❌ Найдено {len(errors)} критических ошибок:", 'error'))
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")

    if len(warnings) > 0:
        print(check_color(f"\n⚠️  Найдено {len(warnings)} предупреждений:", 'warning'))
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")

print("\n" + "=" * 70)

# Тест SUMO (если все ок)
if len(errors) == 0:
    print("\n🚀 Запускаю быстрый тест SUMO...")

    if os.path.exists(net_file) and os.path.exists(route_file):
        print("Попытка запуска SUMO GUI...")
        print("(Закрой окно SUMO после проверки)")

        try:
            import traci

            sumo_cmd = [
                "sumo-gui",
                "-c", f"{PROJECT_ROOT}/models/advanced/xmls/advanced.sumocfg",
                "--start",
                "--delay", "100"
            ]

            traci.start(sumo_cmd)

            # Делаем 100 шагов
            for step in range(100):
                traci.simulationStep()

                if step == 50:
                    vehicles = traci.vehicle.getIDList()
                    print(f"\nШаг 50: Транспорт на дороге = {len(vehicles)}")

            traci.close()

            print(check_color("\n✅ SUMO работает корректно!", 'ok'))

        except Exception as e:
            print(check_color(f"\n❌ Ошибка при запуске SUMO: {e}", 'error'))
    else:
        print(check_color("\n⚠️  Пропускаю тест SUMO (нет необходимых файлов)", 'warning'))

print("\n" + "=" * 70)
print("✨ Проверка завершена!")
print("=" * 70)