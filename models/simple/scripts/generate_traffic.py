import random
import xml.etree.ElementTree as ET
from xml.dom import minidom
from models.simple.scripts import PROJECT_ROOT


def generate_traffic_scenario(output_file, scenario_type="balanced"):
    """
    Генерирует файл маршрутов для разных сценариев
    ИСПРАВЛЕНО: Правильный порядок элементов
    """

    root = ET.Element("routes")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set("xsi:noNamespaceSchemaLocation", "http://sumo.dlr.de/xsd/routes_file.xsd")

    # 1. Типы транспорта (ПЕРВЫЕ)
    car_type = ET.SubElement(root, "vType")
    car_type.set("id", "car")
    car_type.set("vClass", "passenger")
    car_type.set("color", "1,1,0")
    car_type.set("speedDev", "0.1")

    bus_type = ET.SubElement(root, "vType")
    bus_type.set("id", "bus")
    bus_type.set("vClass", "bus")
    bus_type.set("color", "0,1,0")
    bus_type.set("length", "12")
    bus_type.set("width", "2.5")
    bus_type.set("speedDev", "0.05")

    # 2. Маршруты (ВТОРЫЕ)
    routes = [
        ("route_ns", "north_in south_out"),
        ("route_sn", "south_in north_out"),
        ("route_ew", "east_in west_out"),
        ("route_we", "west_in east_out"),
        ("route_ne", "north_in east_out"),
        ("route_nw", "north_in west_out"),
        ("route_se", "south_in east_out"),
        ("route_sw", "south_in west_out"),
        ("route_en", "east_in north_out"),
        ("route_es", "east_in south_out"),
        ("route_wn", "west_in north_out"),
        ("route_ws", "west_in south_out"),
    ]

    for route_id, edges in routes:
        route = ET.SubElement(root, "route")
        route.set("id", route_id)
        route.set("edges", edges)

    # Параметры в зависимости от сценария
    if scenario_type == "balanced":
        car_probability = 0.25
        bus_interval = 60
        simulation_time = 500

    elif scenario_type == "rush_hour":
        car_probability = 0.45
        bus_interval = 30
        simulation_time = 500

    elif scenario_type == "bus_priority":
        car_probability = 0.3
        bus_interval = 20
        simulation_time = 500

    else:  # random
        car_probability = random.uniform(0.2, 0.4)
        bus_interval = random.randint(25, 70)
        simulation_time = 500

    # 3. FLOW ЭЛЕМЕНТЫ (ТРЕТЬИ - ДО vehicle!)
    flows = []
    for route_id, _ in routes:
        prob = car_probability
        if scenario_type == "rush_hour" and random.random() > 0.5:
            prob = car_probability * 1.3

        flows.append({
            'id': f"cars_{route_id}",
            'route': route_id,
            'begin': 0,
            'end': simulation_time,
            'probability': prob
        })

    flows.sort(key=lambda x: (x['begin'], x['id']))

    for flow_data in flows:
        flow = ET.SubElement(root, "flow")
        flow.set("id", flow_data['id'])
        flow.set("type", "car")
        flow.set("route", flow_data['route'])
        flow.set("begin", str(flow_data['begin']))
        flow.set("end", str(flow_data['end']))
        flow.set("probability", str(flow_data['probability']))

    # 4. АВТОБУСЫ (ПОСЛЕДНИЕ)
    buses = []
    bus_id = 0

    for route_id, _ in routes[:4]:  # Основные 4 направления
        for depart_time in range(10, simulation_time, bus_interval):
            actual_depart = depart_time + random.randint(-5, 5)
            if actual_depart < 0:
                actual_depart = 0

            buses.append({
                'id': f"bus_{bus_id}",
                'route': route_id,
                'depart': actual_depart
            })
            bus_id += 1

    buses.sort(key=lambda x: x['depart'])

    for bus in buses:
        vehicle = ET.SubElement(root, "vehicle")
        vehicle.set("id", bus['id'])
        vehicle.set("type", "bus")
        vehicle.set("route", bus['route'])
        vehicle.set("depart", str(bus['depart']))
        vehicle.set("color", "0,1,0")

    # Форматируем и сохраняем
    xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="    ")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(xml_str)

    print(f"✓ Сценарий '{scenario_type}' сгенерирован: {output_file}")
    print(f"  - Вероятность машин: {car_probability}")
    print(f"  - Интервал автобусов: {bus_interval}с")
    print(f"  - Автобусов создано: {len(buses)}")
    print(f"  - Время симуляции: {simulation_time}с")


def generate_all_scenarios():
    """Генерирует все типы сценариев для обучения и тестирования"""

    scenarios = [
        (f"{PROJECT_ROOT}/models/simple/xmls/simple.rou.xml", "balanced"),
        (f"{PROJECT_ROOT}/models/simple/xmls/rush_hour.rou.xml", "rush_hour"),
        (f"{PROJECT_ROOT}/models/simple/xmls/bus_priority.rou.xml", "bus_priority"),
    ]

    for i in range(5):
        scenarios.append((f"{PROJECT_ROOT}/models/simple/xmls/random_{i}.rou.xml", "random"))

    for filename, scenario_type in scenarios:
        generate_traffic_scenario(filename, scenario_type)

    print("\n" + "=" * 50)
    print("✅ Все сценарии сгенерированы!")
    print("=" * 50)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Генератор трафика для SUMO")
    parser.add_argument("--type", type=str, default="all",
                        choices=["balanced", "rush_hour", "bus_priority", "random", "all"],
                        help="Тип сценария")
    parser.add_argument("--output", type=str, default=f"{PROJECT_ROOT}/models/simple/xmls/simple.rou.xml",
                        help="Имя выходного файла")

    args = parser.parse_args()

    if args.type == "all":
        generate_all_scenarios()
    else:
        generate_traffic_scenario(args.output, args.type)