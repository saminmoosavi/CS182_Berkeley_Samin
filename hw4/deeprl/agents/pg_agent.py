import numpy as np

from .base_agent import BaseAgent
from deeprl.policies.MLP_policy import MLPPolicyPG
from deeprl.infrastructure.replay_buffer import ReplayBuffer


class PGAgent(BaseAgent):
    def __init__(self, env, agent_params):
        super(PGAgent, self).__init__()

        # init vars
        self.env = env
        self.agent_params = agent_params
        self.gamma = self.agent_params['gamma']
        self.standardize_advantages = self.agent_params['standardize_advantages']
        self.nn_baseline = self.agent_params['nn_baseline']
        self.reward_to_go = self.agent_params['reward_to_go']

        # actor/policy
        self.actor = MLPPolicyPG(
            self.agent_params['ac_dim'],
            self.agent_params['ob_dim'],
            self.agent_params['n_layers'],
            self.agent_params['size'],
            discrete=self.agent_params['discrete'],
            learning_rate=self.agent_params['learning_rate'],
            nn_baseline=self.agent_params['nn_baseline']
        )

        # replay buffer
        self.replay_buffer = ReplayBuffer(1000000)

    def train(self, observations, actions, rewards_list, next_observations, terminals):

        """
            Training a PG agent refers to updating its actor using the given observations/actions
            and the calculated qvals/advantages that come from the seen rewards.
        """

        # step 1: calculate q values of each (s_t, a_t) point, using rewards (r_0, ..., r_t, ..., r_T)
        q_values = self.calculate_q_vals(rewards_list)

        # step 2: calculate advantages that correspond to each (s_t, a_t) point
        advantages = self.estimate_advantage(observations, q_values)

        # step 3: use all datapoints (s_t, a_t, q_t, adv_t) to update the PG actor/policy
        train_log = self.actor.update(observations, actions, advantages, qvals=q_values)

        return train_log

    def calculate_q_vals(self, rewards_list):

        """
            Monte Carlo estimation of the Q function.
        """
        # Case 1: trajectory-based PG
        # Estimate Q^{pi}(s_t, a_t) by the total discounted reward summed over entire trajectory
        if not self.reward_to_go:

            # For each point (s_t, a_t), associate its value as being the discounted sum of rewards over the full trajectory
            # In other words: value of (s_t, a_t) = sum_{t'=0}^T gamma^t' r_{t'}
            q_values = np.concatenate([self._discounted_return(r) for r in rewards_list])

        # Case 2: reward-to-go PG
        # Estimate Q^{pi}(s_t, a_t) by the discounted sum of rewards starting from t
        else:

            # For each point (s_t, a_t), associate its value as being the discounted sum of rewards over the full trajectory
            # In other words: value of (s_t, a_t) = sum_{t'=t}^T gamma^(t'-t) * r_{t'}
            q_values = np.concatenate([self._discounted_cumsum(r) for r in rewards_list])

        return q_values

    def estimate_advantage(self, obs, q_values):
        """
            Computes advantages by (possibly) subtracting a baseline from the estimated Q values
        """
        # Estimate the advantage when nn_baseline is True,
        # by querying the neural network that you're using to learn the baseline
        if self.nn_baseline:
            baselines_unnormalized = self.actor.run_baseline_prediction(obs)
            ## ensure that the baseline and q_values have the same dimensionality
            ## to prevent silent broadcasting errors
            assert baselines_unnormalized.ndim == q_values.ndim
            ## baseline was trained with standardized q_values, so ensure that the predictions
            ## have the same mean and standard deviation as the current batch of q_values
            baselines = baselines_unnormalized * np.std(q_values) + np.mean(q_values)
            """
            TODO: compute advantage estimates using q_values and baselines
            """
            advantages = q_values - baselines
            """
            END CODE
            """

        # Else, just set the advantage to [Q]
        else:
            advantages = q_values.copy()

        # Normalize the resulting advantages, not used in this assignment
        if self.standardize_advantages:
            advantages = (advantages - np.mean(advantages)) / (np.std(advantages) + 1e-8)

        return advantages

    #####################################################
    #####################################################

    def add_to_replay_buffer(self, paths):
        self.replay_buffer.add_rollouts(paths)

    def sample(self, batch_size):
        return self.replay_buffer.sample_recent_data(batch_size, concat_rew=False)

    #####################################################
    ################## HELPER FUNCTIONS #################
    #####################################################

    def _discounted_return(self, rewards):
        """
            Helper function

            Input: list of rewards {r_0, r_1, ..., r_t', ... r_T} from a single rollout of length T

            Output: numpy array where each index t contains sum_{t'=0}^T gamma^t' r_{t'}
        """

        """
        TODO: Return a numpy array containing the returns for this trajectory.
        All entries in this array should be identical.
        """
        discounted_returns = sum(self.gamma**t*r for t,r in enumerate(rewards))
        list_of_discounted_returns = np.full(len(rewards), discounted_returns)
        """
        END CODE
        """
        return list_of_discounted_returns

    def _discounted_cumsum(self, rewards):
        """
            Helper function which
            -takes a list of rewards {r_0, r_1, ..., r_t', ... r_T},
            -and returns a numpy array where the entry in each index t' is sum_{t'=t}^T gamma^(t'-t) * r_{t'}
        """

        """
        TODO: Return a numpy array containing the discounted sum of future rewards.
        Note that each entry of the output should be different since we sum over
        indices [t, T] instead of [0, T].
        Using a for loop is fine, no need to vectorize this (though you can).
        """
        T = len(rewards)
        list_of_discounted_cumsums = np.zeros(len(rewards))
        for t in range(len(rewards)):
            list_of_discounted_cumsums[t] = sum(self.gamma**t_*r for t_,r in enumerate(rewards[t:T]))

        """
        END CODE
        """

        return list_of_discounted_cumsums

