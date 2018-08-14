import unittest
import gym
import numpy as np
import math
import matplotlib.pyplot as plt
import gym_jsbsim.tasks as tasks
import gym_jsbsim.deprecated_tasks as dep_tasks
from gym_jsbsim.environment import JsbSimEnv, NoFlightGearJsbSimEnv
from gym_jsbsim.test import TaskStub
from gym_jsbsim.visualiser import FlightGearVisualiser


class TestJsbSimEnv(unittest.TestCase):

    def setUp(self, agent_interaction_freq: int=10):
        gym.logger.set_level(gym.logger.DEBUG)
        self.env = None
        self.init_env(agent_interaction_freq)
        self.env.reset()

    def init_env(self, agent_interaction_freq):
        self.env = JsbSimEnv(task_type=TaskStub,
                             agent_interaction_freq=agent_interaction_freq)

    def tearDown(self):
        self.env.close()

    def validate_observation(self, obs: np.array):
        """ Helper; checks shape and values of an observation. """
        self.assertEqual(self.env.observation_space.shape, obs.shape,
                         msg='observation has wrong size')
        self.assertTrue(self.env.observation_space.contains(obs),
                        msg=f'observation size or values out of range: {obs}\n'
                            f'expected min: {self.env.observation_space.low}\n'
                            f'expected max: {self.env.observation_space.high}')

    def validate_action(self, action: np.array):
        """ Helper; checks shape and values of an action. """
        self.assertEqual(self.env.action_space.shape, action.shape,
                         msg='action has wrong size')
        self.assertTrue(self.env.action_space.contains(action),
                        msg=f'action size or values out of range: {action}\n'
                            f'expected min: {self.env.action_space.low}\n'
                            f'expected max: {self.env.action_space.high}')

    def validate_action_made(self, action: np.array):
        """ Helper; confirms action was correctly input to simulation. """
        self.validate_action(action)
        for prop, command in zip(self.env.task.action_names, action):
            actual = self.env.sim[prop]
            self.assertAlmostEqual(command, actual,
                                   msg='simulation commanded value does not match action')

    def test_init_spaces(self):
        # check correct types for obs and action space
        self.assertIsInstance(self.env.observation_space, gym.Space,
                              msg='observation_space is not a Space object')
        self.assertIsInstance(self.env.action_space, gym.Space,
                              msg='action_space is not a Space object')

        # check low and high values are as expected
        obs_lows = self.env.observation_space.low
        obs_highs = self.env.observation_space.high
        act_lows = self.env.action_space.low
        act_highs = self.env.action_space.high

        places_tol = 3

        self.assertEqual('attitude/pitch-rad', self.env.task.state_names[1])
        self.assertAlmostEqual(-0.5 * math.pi, obs_lows[1], places=places_tol,
                               msg='Pitch low range should be -pi/2')
        self.assertAlmostEqual(0.5 * math.pi, obs_highs[1], places=places_tol,
                               msg='Pitch high range should be +pi/2')
        self.assertEqual('attitude/roll-rad', self.env.task.state_names[2])
        self.assertAlmostEqual(-1 * math.pi, obs_lows[2], places=places_tol,
                               msg='Roll low range should be -pi')
        self.assertAlmostEqual(1 * math.pi, obs_highs[2], places=places_tol,
                               msg='Roll high range should be +pi')

        self.assertEqual('fcs/aileron-cmd-norm', self.env.task.action_names[0])
        self.assertAlmostEqual(-1, act_lows[0], places=places_tol,
                               msg='Aileron command low range should be -1.0')
        self.assertAlmostEqual(1, act_highs[0], places=places_tol,
                               msg='Aileron command high range should be +1.0')
        self.assertEqual('fcs/throttle-cmd-norm', self.env.task.action_names[3])
        self.assertAlmostEqual(0, act_lows[3], places=places_tol,
                               msg='Throttle command low range should be 0.0')
        self.assertAlmostEqual(1, act_highs[3], places=places_tol,
                               msg='Throttle command high range should be +1.0')

    def test_reset_env(self):
        self.setUp()
        obs = self.env.reset()

        self.validate_observation(obs)

    def test_do_action(self):
        self.setUp()
        action1 = np.array([0.0, 0.0, 0.0, 0.0])
        action2 = np.array([-0.5, 0.9, -0.05, 0.75])

        # do an action and check results
        obs, _, _, _ = self.env.step(action1)
        self.validate_observation(obs)
        self.validate_action_made(action1)

        # repeat action several times
        for _ in range(10):
            obs, _, _, _ = self.env.step(action1)
            self.validate_observation(obs)
            self.validate_action_made(action1)

        # repeat new action
        for _ in range(10):
            obs, _, _, _ = self.env.step(action2)
            self.validate_observation(obs)
            self.validate_action_made(action2)

    def test_figure_created_closed(self):
        self.env.render(mode='human')
        self.assertIsInstance(self.env.figure_visualiser.figure, plt.Figure)
        self.env.close()
        self.assertIsNone(self.env.figure_visualiser.figure)

    def test_plot_state(self):
        # note: this checks that plot works without throwing exception
        # correctness of plot must be checked in appropriate manual_test
        self.setUp()
        self.env.render(mode='human')

        action = np.array([-0.5, 0.9, -0.05, 0.75])
        # repeat action several times
        for _ in range(3):
            obs, _, _, _ = self.env.step(action)
            self.env.render(mode='human')

    def test_plot_actions(self):
        # note: this checks that plot works without throwing exception
        # correctness of plot must be checked in appropriate manual_test
        self.env.render(mode='human')

        # repeat action several times
        for _ in range(3):
            action = self.env.action_space.sample()
            _, _, _, _ = self.env.step(action)
            self.env.render(mode='human', action_names=self.env.task.action_names, action_values=action)

    def test_asl_agl_elevations_equal(self):
        # we want the height above sea level to equal ground elevation at all times
        self.setUp(agent_interaction_freq=1)
        for i in range(25):
            self.env.step(action=self.env.action_space.sample())
            alt_sl = self.env.sim['position/h-sl-ft']
            alt_gl = self.env.sim['position/h-agl-ft']
            self.assertAlmostEqual(alt_sl, alt_gl)

    def test_render_flightgear_mode(self):
        self.setUp()
        self.env.render(mode='flightgear', flightgear_blocking=False)
        self.assertIsInstance(self.env.flightgear_visualiser, FlightGearVisualiser)
        self.env.close()


class TestNoFlightGearJsbSimEnv(TestJsbSimEnv):

    def init_env(self, agent_interaction_freq):
        self.env = NoFlightGearJsbSimEnv(task_type=TaskStub,
                                         agent_interaction_freq=agent_interaction_freq)

    def test_render_flightgear_mode(self):
        with self.assertRaises(ValueError):
            self.env.render(mode='flightgear')


class TestGymEnvs(unittest.TestCase):
    """ Test that JSBSim environments are correctly registered with OpenAI Gym """
    id_class_pairs = (
        ('SteadyLevelFlightCessna-v0', dep_tasks.SteadyLevelFlightTask_v0),
        ('SteadyLevelFlightCessna-NoFG-v0', dep_tasks.SteadyLevelFlightTask_v0),
        ('SteadyLevelFlightCessna-v1', dep_tasks.SteadyLevelFlightTask_v1),
        ('SteadyLevelFlightCessna-NoFG-v1', dep_tasks.SteadyLevelFlightTask_v1),
        ('SteadyLevelFlightCessna-v2', tasks.SteadyLevelFlightTask),
        ('SteadyLevelFlightCessna-NoFG-v2', tasks.SteadyLevelFlightTask),
        ('HeadingControlCessna-v0', tasks.HeadingControlTask),
        ('HeadingControlCessna-NoFG-v0', tasks.HeadingControlTask)
    )

    def test_gym_inits_correct_task(self):
        for gym_id, task_module in self.id_class_pairs:
            env = gym.make(gym_id)
            self.assertIsInstance(env.task, task_module)

    def test_no_fg_uses_no_fg_class(self):
        for gym_id, task_module in self.id_class_pairs:
            env = gym.make(gym_id)
            if 'NoFG' in gym_id:
                self.assertIsInstance(env, NoFlightGearJsbSimEnv)
            else:
                self.assertIsInstance(env, JsbSimEnv)