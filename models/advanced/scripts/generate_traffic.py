"""
Генератор трафика для advanced сети (3x3 перекрестка)
"""
import random
import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def generate_advanced_traffic(output_file, scenario_type="balanced"):
    """
    Генерирует трафик для сети 3x3
    """

    root = ET.Element("routes")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set("xsi:noNamespaceSchemaLocation", "http://sumo.dlr.de/xsd/routes_file.xsd")

    # Типы транспорта
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

    # Определяем основные маршруты через сеть
    routes_data = [
        # Горизонтальные маршруты (запад -> восток)
        ("route_h_west_east_0", "h_00_in h_00_01 h_01_02 h_02_out"),
        ("route_h_west_east_1", "h_10_in h_10_11 h_11_12 h_12_out"),
        ("route_h_west_east_2", "h_20_in h_20_21 h_21_22 h_22_out"),

        # Горизонтальные маршруты (восток -> запад)
        ("route_h_east_west_0", "h_02_in h_02_01 h_01_00 h_00_out"),
        ("route_h_east_west_1", "h_12_in h_12_11 h_11_10 h_10_out"),
        ("route_h_east_west_2", "h_22_in h_22_21 h_21_20 h_20_out"),

        # Вертикальные маршруты (север -> юг)
        ("route_v_north_south_0", "v_00_in v_00_10 v_10_20 v_20_out"),
        ("route_v_north_south_1", "v_01_in v_01_11 v_11_21 v_21_out"),
        ("route_v_north_south_2", "v_02_in v_02_12 v_12_22 v_22_out"),

        # Вертикальные маршруты (юг -> север)
        ("route_v_south_north_0", "v_20_in v_20_10 v_10_00 v_00_out"),
        ("route_v_south_north_1", "v_21_in v_21_11 v_11_01 v_01_out"),
        ("route_v_south_north_2", "v_22_in v_22_12 v_12_02 v_02_out"),

        # Диагональные маршруты (примеры)
        ("route_d_nw_se", "v_00_in v_00_10 h_10_11 v_11_21 h_21_22 v_22_out"),
        ("route_d_ne_sw", "v_02_in v_02_12 h_12_11 v_11_21 h_21_20 v_20_out"),
        ("route_d_sw_ne", "v_20_in v_20_10 h_10_11 v_11_01 h_01_02 v_02_out"),
        ("route_d_se_nw", "v_22_in v_22_12 h_12_11 v_11_01 h_01_00 v_00_out"),
    ]

    # Создаем маршруты
    for route_id, edges in routes_data:
        route = ET.SubElement(root, "route")
        route.set("id", route_id)
        route.set("edges", edges)

    # Параметры в зависимости от сценария
    if scenario_type == "balanced":
        car_probability = 0.15
        bus_interval = 80
        simulation_time = 1000
    elif scenario_type == "rush_hour":
        car_probability = 0.3
        bus_interval = 40
        simulation_time = 1000
    elif scenario_type == "bus_priority":
        car_probability = 0.2
        bus_interval = 30
        simulation_time = 1000
    else:  # random
        car_probability = random.uniform(0.15, 0.35)
        bus_interval = random.randint(30, 90)
        simulation_time = 1000

    # Создаем flows для машин
    flows = []
    for route_id, _ in routes_data:
        prob = car_probability
        if scenario_type == "rush_hour":
            # Увеличиваем трафик на основных маршрутах
            if "h_west_east" in route_id or "v_north_south" in route_id:
                prob = car_probability * 1.5

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

    # Создаем автобусы на основных маршрутах
    buses = []
    bus_id = 0

    # Автобусы ходят по основным прямым маршрутам
    main_routes = [
        "route_h_west_east_0", "route_h_west_east_1", "route_h_west_east_2",
        "route_h_east_west_0", "route_h_east_west_1", "route_h_east_west_2",
        "route_v_north_south_0", "route_v_north_south_1", "route_v_north_south_2",
        "route_v_south_north_0", "route_v_south_north_1", "route_v_south_north_2",
    ]

    for route_id in main_routes:
        for depart_time in range(20, simulation_time, bus_interval):
            actual_depart = depart_time + random.randint(-10, 10)
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

    print(f"✓ Сценарий '{scenario_type}' для advanced сети сгенерирован")
    print(f"  - Маршрутов: {len(routes_data)}")
    print(f"  - Автобусов: {len(buses)}")
    print(f"  - Вероятность машин: {car_probability}")


def generate_all_advanced_scenarios():
    """Генерирует все сценарии для advanced модели"""

    os.makedirs(f"{PROJECT_ROOT}/models/advanced/xmls", exist_ok=True)

    scenarios = [
        (f"{PROJECT_ROOT}/models/advanced/xmls/advanced.rou.xml", "balanced"),
        (f"{PROJECT_ROOT}/models/advanced/xmls/advanced_rush.rou.xml", "rush_hour"),
        (f"{PROJECT_ROOT}/models/advanced/xmls/advanced_bus.rou.xml", "bus_priority"),
    ]

    for i in range(3):
        scenarios.append((f"{PROJECT_ROOT}/models/advanced/xmls/advanced_random_{i}.rou.xml", "random"))

    for filename, scenario_type in scenarios:
        generate_advanced_traffic(filename, scenario_type)

    print("\n" + "=" * 70)
    print("✅ Все сценарии для advanced сети сгенерированы!")
    print("=" * 70)


if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Генератор трафика для advanced сети")
    parser.add_argument("--type", type=str, default="all",
                        choices=["balanced", "rush_hour", "bus_priority", "random", "all"])
    parser.add_argument("--output", type=str, default=f"{PROJECT_ROOT}/models/advanced/xmls/advanced.rou.xml")

    args = parser.parse_args()

    if args.type == "all":
        generate_all_advanced_scenarios()
    else:
        generate_advanced_traffic(args.output, args.type)