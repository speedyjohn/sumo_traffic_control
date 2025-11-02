import os
import sys
import numpy as np
from stable_baselines3 import DQN
from green_corridor import TrafficEnv
from models.simple.scripts import PROJECT_ROOT

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)


def evaluate_agent(agent_type="trained", n_episodes=5):
    """
    Оценивает агента

    agent_type: "trained" (обученная модель) или "random" (случайные действия)
    """
    print(f"\n{'=' * 60}")
    print(f"🧪 Тестируем: {agent_type.upper()}")
    print('=' * 60)

    if agent_type == "trained":
        try:
            model = DQN.load(f"{PROJECT_ROOT}/models/simple/xmls/green_corridor_model")
        except FileNotFoundError:
            print("❌ Модель не найдена! Сначала обучи модель:")
            print("   python green_corridor.py --mode train --steps 50000")
            return None

    env = TrafficEnv("simple.sumocfg", gui=False, route_file="../xmls/simple.rou.xml")

    all_rewards = []
    all_bus_waiting = []
    all_car_waiting = []

    for episode in range(n_episodes):
        obs, _ = env.reset()
        episode_reward = 0
        done = False
        steps = 0

        while not done and steps < 300:
            if agent_type == "trained":
                action, _ = model.predict(obs, deterministic=True)
            else:  # random
                action = env.action_space.sample()

            obs, reward, terminated, truncated, _ = env.step(action)
            episode_reward += reward
            done = terminated or truncated
            steps += 1

        all_rewards.append(episode_reward)

        # Собираем статистику (примерная, т.к. симуляция уже закончена)
        print(f"  Episode {episode + 1}/{n_episodes}: reward = {episode_reward:.1f}")

    env.close()

    avg_reward = np.mean(all_rewards)
    std_reward = np.std(all_rewards)

    print(f"\n📊 Результаты:")
    print(f"   Средняя награда: {avg_reward:.1f} ± {std_reward:.1f}")
    print(f"   Лучший эпизод: {max(all_rewards):.1f}")
    print(f"   Худший эпизод: {min(all_rewards):.1f}")

    return {
        'avg_reward': avg_reward,
        'std_reward': std_reward,
        'rewards': all_rewards
    }


def compare_agents():
    """Сравнивает обученного агента со случайным"""
    print("\n" + "=" * 60)
    print("🎯 БЫСТРАЯ ОЦЕНКА КАЧЕСТВА МОДЕЛИ")
    print("=" * 60)
    print("Сравниваем обученную модель со случайным агентом...")

    random_results = evaluate_agent("random", n_episodes=5)

    if random_results is None:
        return

    trained_results = evaluate_agent("trained", n_episodes=5)

    if trained_results is None:
        return

    # Сравнение
    improvement = ((trained_results['avg_reward'] - random_results['avg_reward'])
                   / abs(random_results['avg_reward']) * 100)

    print("\n" + "=" * 60)
    print("📈 СРАВНЕНИЕ")
    print("=" * 60)
    print(f"Случайный агент:  {random_results['avg_reward']:.1f}")
    print(f"Обученная модель: {trained_results['avg_reward']:.1f}")
    print(f"Улучшение:        {improvement:+.1f}%")
    print("=" * 60)

    # Оценка качества
    if improvement > 50:
        print("\n✅ ОТЛИЧНО! Модель работает значительно лучше!")
        print("   Можешь использовать для презентации.")
    elif improvement > 20:
        print("\n✅ ХОРОШО! Модель показывает улучшение.")
        print("   Можно обучить дольше для лучшего результата.")
    elif improvement > 0:
        print("\n⚠️ СЛАБО. Модель работает чуть лучше случайного.")
        print("   Нужно больше обучения: --steps 200000")
    else:
        print("\n❌ ПЛОХО. Модель не обучилась.")
        print("   Запусти обучение заново с большим количеством шагов.")

    print("=" * 60)

    # Рекомендации
    if improvement < 30:
        print("\n💡 РЕКОМЕНДАЦИИ:")
        print("   1. Обучи модель дольше:")
        print("      python green_corridor.py --mode train --steps 200000")
        print("   2. Проверь что файлы маршрутов созданы:")
        print("      python generate_traffic.py --type all")
        print("   3. Посмотри графики обучения:")
        print("      ./logs/training_progress.png")


def check_training_progress():
    """Проверяет прогресс из лог файла"""
    log_file = f"{PROJECT_ROOT}/models/simple/logs/training_log.txt"

    if not os.path.exists(log_file):
        print("\n⚠️ Лог файл не найден. Модель еще не обучалась.")
        return

    print("\n" + "=" * 60)
    print("📜 ИСТОРИЯ ОБУЧЕНИЯ")
    print("=" * 60)

    with open(log_file, "r") as f:
        lines = f.readlines()[1:]  # Пропускаем заголовок

    if len(lines) < 10:
        print("⚠️ Слишком мало данных. Продолжай обучение.")
        return

    # Берем первые и последние 10 эпизодов
    early_episodes = lines[:10]
    late_episodes = lines[-10:]

    def parse_stats(episodes):
        rewards = [float(line.split(',')[2]) for line in episodes]
        bus_waits = [float(line.split(',')[3]) for line in episodes]
        return np.mean(rewards), np.mean(bus_waits)

    early_reward, early_bus = parse_stats(early_episodes)
    late_reward, late_bus = parse_stats(late_episodes)

    print(f"Первые 10 эпизодов:")
    print(f"  Награда: {early_reward:.1f}")
    print(f"  Ожидание автобусов: {early_bus:.2f}s")

    print(f"\nПоследние 10 эпизодов:")
    print(f"  Награда: {late_reward:.1f}")
    print(f"  Ожидание автобусов: {late_bus:.2f}s")

    reward_improvement = (late_reward - early_reward) / abs(early_reward) * 100
    bus_improvement = (early_bus - late_bus) / early_bus * 100

    print(f"\n📊 Прогресс:")
    print(f"  Награда: {reward_improvement:+.1f}%")
    print(f"  Ожидание автобусов: {bus_improvement:+.1f}%")

    if reward_improvement > 20 and bus_improvement > 10:
        print("\n✅ Модель учится! Продолжай обучение.")
    elif reward_improvement > 0:
        print("\n⚠️ Есть прогресс, но медленно. Возможно нужно больше шагов.")
    else:
        print("\n❌ Нет прогресса. Проверь настройки или начни заново.")

    print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Быстрая оценка качества модели")
    parser.add_argument("--check-progress", action="store_true",
                        help="Проверить прогресс обучения из логов")

    args = parser.parse_args()

    if args.check_progress:
        check_training_progress()
    else:
        compare_agents()