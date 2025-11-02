import os
import sys
import numpy as np
import traci
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import DQN
from stable_baselines3.common.callbacks import BaseCallback
from models.simple.scripts import PROJECT_ROOT

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Установи переменную окружения SUMO_HOME")


class TrafficEnv(gym.Env):
    """
    ИСПРАВЛЕНО v2: Правильная reward function!
    """

    def __init__(self, sumo_cfg, gui=False, route_file=None):
        super().__init__()

        self.sumo_cfg = sumo_cfg
        self.route_file = route_file
        self.gui = gui
        self.sumo_cmd = None
        self.traffic_light_id = "center"

        # Action: 0 = держать фазу, 1 = переключить
        self.action_space = spaces.Discrete(2)

        # Observation: [vehicles_ns, vehicles_ew, bus_ns, bus_ew, phase]
        self.observation_space = spaces.Box(
            low=0, high=50, shape=(5,), dtype=np.float32
        )

        self.current_phase = 0
        self.yellow_duration = 3
        self.min_green_time = 10  # Снижено для более частого переключения
        self.time_since_phase_start = 0
        self.step_count = 0

        self.in_yellow = False
        self.yellow_counter = 0

        # НОВОЕ: Отслеживаем предыдущее состояние для вычисления изменений
        self.prev_total_waiting = 0

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        if self.sumo_cmd is not None:
            try:
                traci.close()
            except:
                pass

        sumo_binary = "sumo-gui" if self.gui else "sumo"
        self.sumo_cmd = [sumo_binary, "-c", self.sumo_cfg,
                         "--start", "--quit-on-end",
                         "--waiting-time-memory", "1000",
                         "--time-to-teleport", "-1",
                         "--no-warnings", "true"]

        if self.route_file:
            self.sumo_cmd.extend(["--route-files", self.route_file])

        traci.start(self.sumo_cmd)

        self.current_phase = 0
        self.time_since_phase_start = 0
        self.step_count = 0
        self.in_yellow = False
        self.yellow_counter = 0
        self.prev_total_waiting = 0

        traci.trafficlight.setPhase(self.traffic_light_id, 0)

        return self._get_observation(), {}

    def _get_observation(self):
        """Получаем состояние среды"""
        try:
            ns_vehicles = len(traci.lane.getLastStepVehicleIDs('north_in_0')) + \
                          len(traci.lane.getLastStepVehicleIDs('north_in_1')) + \
                          len(traci.lane.getLastStepVehicleIDs('south_in_0')) + \
                          len(traci.lane.getLastStepVehicleIDs('south_in_1'))

            ew_vehicles = len(traci.lane.getLastStepVehicleIDs('east_in_0')) + \
                          len(traci.lane.getLastStepVehicleIDs('east_in_1')) + \
                          len(traci.lane.getLastStepVehicleIDs('west_in_0')) + \
                          len(traci.lane.getLastStepVehicleIDs('west_in_1'))

            has_bus_ns = 0
            has_bus_ew = 0

            all_lanes = ['north_in_0', 'north_in_1', 'south_in_0', 'south_in_1',
                         'east_in_0', 'east_in_1', 'west_in_0', 'west_in_1']

            for lane in all_lanes:
                vehicles = traci.lane.getLastStepVehicleIDs(lane)
                for veh_id in vehicles:
                    if traci.vehicle.getTypeID(veh_id) == 'bus':
                        if 'north' in lane or 'south' in lane:
                            has_bus_ns = 1
                        else:
                            has_bus_ew = 1

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

    def _get_reward(self):
        """
        НОВАЯ REWARD FUNCTION!
        Награда основана на ИЗМЕНЕНИИ ожидания (не абсолютном значении)
        """
        try:
            all_lanes = ['north_in_0', 'north_in_1', 'south_in_0', 'south_in_1',
                         'east_in_0', 'east_in_1', 'west_in_0', 'west_in_1']

            total_waiting = 0
            bus_waiting = 0

            for lane in all_lanes:
                vehicles = traci.lane.getLastStepVehicleIDs(lane)
                for veh_id in vehicles:
                    waiting = traci.vehicle.getWaitingTime(veh_id)

                    if traci.vehicle.getTypeID(veh_id) == 'bus':
                        # Автобусы важнее в 3 раза
                        bus_waiting += waiting * 3
                        total_waiting += waiting * 3
                    else:
                        total_waiting += waiting

            # КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: Награда = насколько УЛУЧШИЛОСЬ ожидание
            delta_waiting = self.prev_total_waiting - total_waiting

            # Нормализуем награду
            reward = delta_waiting / 100.0

            # Бонусы за хорошие решения
            if not self.in_yellow:
                ns_count = len(traci.lane.getLastStepVehicleIDs('north_in_0')) + \
                           len(traci.lane.getLastStepVehicleIDs('south_in_0'))
                ew_count = len(traci.lane.getLastStepVehicleIDs('east_in_0')) + \
                           len(traci.lane.getLastStepVehicleIDs('west_in_0'))

                # Бонус если держим зеленый там где больше машин
                if self.current_phase == 0 and ns_count > ew_count + 5:
                    reward += 1.0
                elif self.current_phase == 1 and ew_count > ns_count + 5:
                    reward += 1.0

                # Штраф если держим зеленый там где меньше машин
                if self.current_phase == 0 and ew_count > ns_count + 10:
                    reward -= 2.0
                elif self.current_phase == 1 and ns_count > ew_count + 10:
                    reward -= 2.0

            # Обновляем предыдущее значение
            self.prev_total_waiting = total_waiting

            return reward

        except:
            return 0.0

    def step(self, action):
        """Выполняем действие"""
        self.step_count += 1

        if self.in_yellow:
            traci.simulationStep()
            self.yellow_counter += 1

            if self.yellow_counter >= self.yellow_duration:
                self.current_phase = 1 - self.current_phase
                traci.trafficlight.setPhase(self.traffic_light_id,
                                            self.current_phase * 2)
                self.in_yellow = False
                self.yellow_counter = 0
                self.time_since_phase_start = 0
        else:
            if action == 1 and self.time_since_phase_start >= self.min_green_time:
                traci.trafficlight.setPhase(self.traffic_light_id, 1)
                self.in_yellow = True
                self.yellow_counter = 0

            traci.simulationStep()
            self.time_since_phase_start += 1

        obs = self._get_observation()
        reward = self._get_reward()

        terminated = traci.simulation.getMinExpectedNumber() <= 0
        truncated = self.step_count >= 1000

        return obs, reward, terminated, truncated, {}

    def close(self):
        if self.sumo_cmd is not None:
            try:
                traci.close()
            except:
                pass


class TrainingCallback(BaseCallback):
    """Мониторинг обучения"""

    def __init__(self, check_freq=1000, save_path=f"{PROJECT_ROOT}/models/simple/logs/", verbose=1):
        super().__init__(verbose)
        self.check_freq = check_freq
        self.save_path = save_path

        self.episode_rewards = []
        self.episode_lengths = []

        self.current_reward = 0
        self.current_length = 0

        os.makedirs(save_path, exist_ok=True)

        self.log_file = os.path.join(save_path, "training_log.txt")
        with open(self.log_file, "w") as f:
            f.write("Episode,Steps,Reward\n")

    def _on_step(self):
        self.current_reward += self.locals['rewards'][0]
        self.current_length += 1

        if self.locals['dones'][0]:
            self.episode_rewards.append(self.current_reward)
            self.episode_lengths.append(self.current_length)

            with open(self.log_file, "a") as f:
                f.write(f"{len(self.episode_rewards)},{self.current_length},"
                        f"{self.current_reward:.2f}\n")

            if len(self.episode_rewards) % 10 == 0:
                recent = self.episode_rewards[-20:]
                avg = np.mean(recent)

                # Определяем тренд
                if len(self.episode_rewards) >= 40:
                    older_avg = np.mean(self.episode_rewards[-40:-20])
                    if avg > older_avg * 1.1:
                        trend = "📈 улучшается"
                    elif avg < older_avg * 0.9:
                        trend = "📉 ухудшается"
                    else:
                        trend = "➡️ стабильно"
                else:
                    trend = "..."

                print(f"\n📊 Episode {len(self.episode_rewards)}: "
                      f"Reward={avg:.1f}, Trend={trend}")

            self.current_reward = 0
            self.current_length = 0

        if self.n_calls % self.check_freq == 0:
            self.model.save(os.path.join(self.save_path, f"model_{self.n_calls}"))

        return True


def train_model(total_steps=100000):
    """Обучение модели"""
    print("🚀 Начинаем обучение v2 (ИСПРАВЛЕННАЯ reward function)...")

    # Проверяем что сценарии есть
    if not os.path.exists("../xmls/simple.rou.xml"):
        print("Генерируем сценарии...")
        import generate_traffic_FIXED as gen
        gen.generate_all_scenarios()

    env = TrafficEnv(
f"{PROJECT_ROOT}/models/simple/xmls/simple.sumocfg",
        gui=False,
        route_file=f"{PROJECT_ROOT}/models/simple/xmls/xmls/simple.rou.xml")

    model = DQN(
        "MlpPolicy",
        env,
        learning_rate=0.0003,
        buffer_size=100000,
        learning_starts=5000,
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

    callback = TrainingCallback()

    print(f"\n🎓 Обучение на {total_steps} шагов...")
    print("Смотри на Reward - он должен РАСТИ (становиться положительнее)!")

    model.learn(
        total_timesteps=total_steps,
        callback=callback
    )

    model.save(f"{PROJECT_ROOT}/models/simple/xmls/green_corridor_model")
    print("\n✅ Модель сохранена!")

    env.close()


def test_model():
    """Тестирование модели"""
    print("🧪 Тестируем модель...")

    model = DQN.load(f"{PROJECT_ROOT}/models/simple/xmls/green_corridor_model")
    env = TrafficEnv(f"{PROJECT_ROOT}/models/simple/xmls/simple.sumocfg", gui=True, route_file="../xmls/simple.rou.xml")

    obs, _ = env.reset()
    total_reward = 0

    for _ in range(500):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, _ = env.step(action)
        total_reward += reward

        if terminated or truncated:
            break

    print(f"✅ Награда: {total_reward:.2f}")
    env.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, default="train",
                        choices=["train", "test"])
    parser.add_argument("--steps", type=int, default=100000)
    args = parser.parse_args()

    if args.mode == "train":
        train_model(total_steps=args.steps)
    else:
        test_model()