import gymnasium as gym
from reinforcement.utils import *
from reinforcement.reinforcement_policy_iteration import *

def main():
    env = gym.make('FrozenLake-v1', desc=None, map_name="4x4", is_slippery=True)
    slippery_MDP = create_FrozenLake_v1_4x4_slippery_MDP()
    value_iteration = reinforcement_policy_iteration(env.observation_space.n, env.action_space.n, slippery_MDP, theta=0.001)
    value_iteration.fit()

    episodes = 100
    return_sum = 0
    for episode in range(episodes):
        state = env.reset()[0]
        ret = 0
        while True:
            action = value_iteration.greedy_policy(state)
            next_state, reward, done, _, _ = env.step(action)
            ret += reward
            state = next_state
            if done:
                return_sum += ret
                print("Episode {}, Return {}".format(episode, ret))
                break
    print()
    print("Average return: {}".format(return_sum/episodes))
    print("Value")
    print(value_iteration.value.reshape((4, 4)))
    print("Policy")
    print(value_iteration.policy.reshape((4, 4)))



if __name__ == "__main__":
    main()