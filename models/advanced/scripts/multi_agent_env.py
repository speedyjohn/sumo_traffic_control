"""
Multi-Agent система для управления сетью светофоров
Каждый перекресток управляется независимым агентом
"""
import os
import sys
import numpy as np
import traci
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import DQN
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Установи переменную окружения SUMO_HOME")


class SingleIntersectionAgent:
    """
    Агент для управления одним перекрестком
    Использует ту же логику что и в simple модели
    """

    def __init__(self, tl_id, model=None):
        self.tl_id = tl_id
        self.model = model

        # Состояние агента
        self.current_phase = 0
        self.time_since_phase_start = 0
        self.in_yellow = False
        self.yellow_counter = 0
        self.yellow_duration = 3
        self.min_green_time = 10

        # Observation space: [vehicles_ns, vehicles_ew, bus_ns, bus_ew, phase]
        self.observation_space = spaces.Box(
            low=0, high=50, shape=(5,), dtype=np.float32
        )

        # Action space: 0 = держать, 1 = переключить
        self.action_space = spaces.Discrete(2)

        # Для награды
        self.prev_total_waiting = 0

    def get_incoming_lanes(self):
        """Получить входящие полосы для данного перекрестка"""
        try:
            # Получаем все входящие полосы из конфигурации светофора
            controlled_lanes = traci.trafficlight.getControlledLanes(self.tl_id)
            # Убираем дубликаты
            return list(set(controlled_lanes))
        except:
            return []

    def get_observation(self):
        """Наблюдение для данного перекрестка"""
        try:
            lanes = self.get_incoming_lanes()

            ns_vehicles = 0
            ew_vehicles = 0
            has_bus_ns = 0
            has_bus_ew = 0

            for lane in lanes:
                vehicles = traci.lane.getLastStepVehicleIDs(lane)

                # Определяем направление по имени полосы
                if 'v_' in lane:  # Вертикальная дорога (север-юг)
                    ns_vehicles += len(vehicles)
                    for veh_id in vehicles:
                        if traci.vehicle.getTypeID(veh_id) == 'bus':
                            has_bus_ns = 1
                            break
                else:  # Горизонтальная дорога (восток-запад)
                    ew_vehicles += len(vehicles)
                    for veh_id in vehicles:
                        if traci.vehicle.getTypeID(veh_id) == 'bus':
                            has_bus_ew = 1
                            break

            obs = np.array([
                min(ns_vehicles, 50),
                min(ew_vehicles, 50),
                has_bus_ns,
                has_bus_ew,
                self.current_phase
            ], dtype=np.float32)

            return obs
        except:
            return np.zeros(5, dtype=np.float32)

    def get_reward(self):
        """Награда для данного перекрестка"""
        try:
            lanes = self.get_incoming_lanes()

            total_waiting = 0

            for lane in lanes:
                vehicles = traci.lane.getLastStepVehicleIDs(lane)
                for veh_id in vehicles:
                    waiting = traci.vehicle.getWaitingTime(veh_id)

                    if traci.vehicle.getTypeID(veh_id) == 'bus':
                        total_waiting += waiting * 3  # Автобусы важнее
                    else:
                        total_waiting += waiting

            # Награда = улучшение
            delta_waiting = self.prev_total_waiting - total_waiting
            reward = delta_waiting / 100.0

            # Бонусы за правильные решения
            if not self.in_yellow:
                ns_count = sum([len(traci.lane.getLastStepVehicleIDs(l))
                                for l in lanes if 'v_' in l])
                ew_count = sum([len(traci.lane.getLastStepVehicleIDs(l))
                                for l in lanes if 'h_' in l])

                if self.current_phase == 0 and ns_count > ew_count + 5:
                    reward += 1.0
                elif self.current_phase == 1 and ew_count > ns_count + 5:
                    reward += 1.0

                if self.current_phase == 0 and ew_count > ns_count + 10:
                    reward -= 2.0
                elif self.current_phase == 1 and ns_count > ew_count + 10:
                    reward -= 2.0

            self.prev_total_waiting = total_waiting

            return reward
        except:
            return 0.0

    def execute_action(self, action):
        """Выполнить действие на перекрестке"""
        if self.in_yellow:
            self.yellow_counter += 1
            if self.yellow_counter >= self.yellow_duration:
                self.current_phase = 1 - self.current_phase
                traci.trafficlight.setPhase(self.tl_id, self.current_phase * 2)
                self.in_yellow = False
                self.yellow_counter = 0
                self.time_since_phase_start = 0
        else:
            if action == 1 and self.time_since_phase_start >= self.min_green_time:
                traci.trafficlight.setPhase(self.tl_id, 1)  # Желтый
                self.in_yellow = True
                self.yellow_counter = 0

            self.time_since_phase_start += 1

    def reset(self):
        """Сброс состояния агента"""
        self.current_phase = 0
        self.time_since_phase_start = 0
        self.in_yellow = False
        self.yellow_counter = 0
        self.prev_total_waiting = 0
        try:
            traci.trafficlight.setPhase(self.tl_id, 0)
        except:
            pass


class MultiAgentTrafficEnv(gym.Env):
    """
    Multi-Agent среда для сети перекрестков
    """

    def __init__(self, sumo_cfg, gui=False, route_file=None, use_pretrained=True):
        super().__init__()

        self.sumo_cfg = sumo_cfg
        self.route_file = route_file
        self.gui = gui
        self.sumo_cmd = None
        self.step_count = 0

        # Список ID всех светофоров в сети (3x3 сетка)
        self.traffic_lights = [
            'tl_00', 'tl_01', 'tl_02',
            'tl_10', 'tl_11', 'tl_12',
            'tl_20', 'tl_21', 'tl_22'
        ]

        # Создаем агента для каждого перекрестка
        self.agents = {}

        if use_pretrained:
            # Пытаемся загрузить обученную модель из simple
            try:
                simple_model = DQN.load(f"{PROJECT_ROOT}/models/simple/model/green_corridor_model")
                print("✅ Загружена обученная модель из simple/")
                for tl_id in self.traffic_lights:
                    self.agents[tl_id] = SingleIntersectionAgent(tl_id, model=simple_model)
            except:
                print("⚠️ Обученная модель не найдена, создаем новых агентов")
                for tl_id in self.traffic_lights:
                    self.agents[tl_id] = SingleIntersectionAgent(tl_id)
        else:
            # Создаем новых агентов без модели
            for tl_id in self.traffic_lights:
                self.agents[tl_id] = SingleIntersectionAgent(tl_id)

        # Пространства для multi-agent (concatenated observations)
        single_obs_dim = 5
        self.observation_space = spaces.Box(
            low=0, high=50,
            shape=(len(self.traffic_lights) * single_obs_dim,),
            dtype=np.float32
        )

        # Action space: по одному действию для каждого агента
        self.action_space = spaces.MultiDiscrete([2] * len(self.traffic_lights))

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        if self.sumo_cmd is not None:
            try:
                traci.close()
            except:
                pass

        sumo_binary = "sumo-gui" if self.gui else "sumo"
        self.sumo_cmd = [
            sumo_binary, "-c", self.sumo_cfg,
            "--start", "--quit-on-end",
            "--waiting-time-memory", "1000",
            "--time-to-teleport", "-1",
            "--no-warnings", "true"
        ]

        if self.route_file:
            self.sumo_cmd.extend(["--route-files", self.route_file])

        traci.start(self.sumo_cmd)

        # Сброс всех агентов
        for agent in self.agents.values():
            agent.reset()

        self.step_count = 0

        return self._get_observation(), {}

    def _get_observation(self):
        """Собираем наблюдения от всех агентов"""
        obs_list = []
        for tl_id in self.traffic_lights:
            agent_obs = self.agents[tl_id].get_observation()
            obs_list.extend(agent_obs)
        return np.array(obs_list, dtype=np.float32)

    def _get_reward(self):
        """Суммарная награда от всех агентов"""
        total_reward = 0
        for agent in self.agents.values():
            total_reward += agent.get_reward()
        return total_reward

    def step(self, actions):
        """
        Выполнить действия всех агентов
        actions: список действий для каждого агента
        """
        self.step_count += 1

        # Каждый агент выполняет свое действие
        for i, tl_id in enumerate(self.traffic_lights):
            if isinstance(actions, np.ndarray):
                action = actions[i]
            else:
                action = actions
            self.agents[tl_id].execute_action(action)

        # Шаг симуляции
        traci.simulationStep()

        # Получаем наблюдения и награду
        obs = self._get_observation()
        reward = self._get_reward()

        terminated = traci.simulation.getMinExpectedNumber() <= 0
        truncated = self.step_count >= 1500  # Больше времени для большой сети

        return obs, reward, terminated, truncated, {}

    def close(self):
        if self.sumo_cmd is not None:
            try:
                traci.close()
            except:
                pass


def train_multi_agent(total_steps=200000):
    """
    Обучение multi-agent системы
    Использует общую политику для всех агентов
    """
    print("\n" + "=" * 70)
    print("🚀 ОБУЧЕНИЕ MULTI-AGENT СИСТЕМЫ")
    print("=" * 70)
    print("Сеть: 3x3 перекрестка (9 светофоров)")
    print("Стратегия: Каждый агент использует общую политику")
    print("=" * 70)

    env = MultiAgentTrafficEnv(
        f"{PROJECT_ROOT}/models/advanced/xmls/advanced.sumocfg",
        gui=False,
        route_file=f"{PROJECT_ROOT}/models/advanced/xmls/advanced.rou.xml",
        use_pretrained=True  # Используем предобученную модель из simple
    )

    # ВАЖНО: Для multi-agent используем ОДНУ общую модель
    # Она будет применяться к каждому перекрестку независимо
    model = DQN(
        "MlpPolicy",
        env,
        learning_rate=0.0003,
        buffer_size=200000,
        learning_starts=10000,
        batch_size=64,
        tau=0.01,
        gamma=0.98,
        train_freq=4,
        target_update_interval=1000,
        exploration_fraction=0.3,
        exploration_initial_eps=1.0,
        exploration_final_eps=0.05,
        verbose=1
    )

    print(f"\n🎓 Обучение на {total_steps} шагов...")
    print("Модель будет учиться управлять всеми 9 перекрестками!")

    from stable_baselines3.common.callbacks import BaseCallback

    class MultiAgentCallback(BaseCallback):
        def __init__(self, verbose=0):
            super().__init__(verbose)
            self.episode_rewards = []
            self.current_reward = 0

        def _on_step(self):
            self.current_reward += self.locals['rewards'][0]

            if self.locals['dones'][0]:
                self.episode_rewards.append(self.current_reward)

                if len(self.episode_rewards) % 10 == 0:
                    recent = self.episode_rewards[-20:]
                    avg = np.mean(recent)
                    print(f"\n📊 Episode {len(self.episode_rewards)}: "
                          f"Avg Reward={avg:.1f}")

                self.current_reward = 0

            return True

    callback = MultiAgentCallback()

    model.learn(
        total_timesteps=total_steps,
        callback=callback
    )

    # Сохраняем модель
    os.makedirs(f"{PROJECT_ROOT}/models/advanced/model", exist_ok=True)
    model.save(f"{PROJECT_ROOT}/models/advanced/model/multi_agent_model")
    print("\n✅ Multi-agent модель сохранена!")

    env.close()


def test_multi_agent():
    """Тестирование multi-agent системы"""
    print("\n" + "=" * 70)
    print("🧪 ТЕСТ MULTI-AGENT СИСТЕМЫ")
    print("=" * 70)

    try:
        model = DQN.load(f"{PROJECT_ROOT}/models/advanced/model/multi_agent_model")
    except:
        print("⚠️ Multi-agent модель не найдена")
        print("Используем предобученную модель из simple/")
        model = DQN.load(f"{PROJECT_ROOT}/models/simple/model/green_corridor_model")

    env = MultiAgentTrafficEnv(
        f"{PROJECT_ROOT}/models/advanced/xmls/advanced.sumocfg",
        gui=True,
        route_file=f"{PROJECT_ROOT}/models/advanced/xmls/advanced.rou.xml",
        use_pretrained=False
    )

    # Присваиваем модель каждому агенту
    for agent in env.agents.values():
        agent.model = model

    obs, _ = env.reset()
    total_reward = 0

    print("\n👀 Смотри в SUMO GUI:")
    print("   • 9 перекрестков работают независимо")
    print("   • Каждый агент принимает свои решения")
    print("   • Зеленые = автобусы, Желтые = машины")

    for step in range(1000):
        # Каждый агент принимает решение
        actions = []
        for tl_id in env.traffic_lights:
            agent = env.agents[tl_id]
            agent_obs = agent.get_observation()
            action, _ = model.predict(agent_obs, deterministic=True)
            actions.append(action)

        obs, reward, terminated, truncated, _ = env.step(np.array(actions))
        total_reward += reward

        if terminated or truncated:
            break

    print(f"\n✅ Тест завершен! Награда: {total_reward:.2f}")
    env.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, default="train",
                        choices=["train", "test"])
    parser.add_argument("--steps", type=int, default=200000)
    args = parser.parse_args()

    if args.mode == "train":
        train_multi_agent(total_steps=args.steps)
    else:
        test_multi_agent()