""" Generating Controlled data for pretraining collision avoidance """

import random
import argparse
import os

import numpy as np
from numpy.linalg import norm
import matplotlib.pyplot as plt

import rvo2

def generate_circle_crossing(num_ped, sim, radius=4):
    positions = []
    goals = []
    speed = []
    agent_list = []
    for i in range(num_ped):
        while True:
            angle = np.random.random() * np.pi * 2
            # add some noise to simulate all the possible cases robot could meet with human
            px_noise = (np.random.random() - 0.5)  ## human.v_pref
            py_noise = (np.random.random() - 0.5)  ## human.v_pref
            px = radius * np.cos(angle) + px_noise
            py = radius * np.sin(angle) + py_noise
            collide = False
            for agent in agent_list:
                # min_dist = 2*human.radius + discomfort_dist
                min_dist = 0.8 
                if norm((px - agent[0], py - agent[1])) < min_dist or \
                        norm((px - agent[2], py - agent[3])) < min_dist:
                    collide = True
                    break
            if not collide:
                break
        positions.append((px, py))
        goals.append((-px, -py))
        sim.addAgent((px, py))
        vx = 0
        vy = 0
        speed.append((vx, vy))
        agent_list.append([px, py, -px, -py])
    trajectories = [[positions[i]] for i in range(num_ped)]
    return trajectories, positions, goals, speed

def generate_square_crossing(num_ped, sim, square_width=2):
    positions = []
    goals = []
    speed = []
    agent_list = []
    square_width = 12

    for i in range(num_ped):
        if np.random.random() > 0.5:
            sign = -1
        else:
            sign = 1
        min_dist = 4
        while True:
            px = np.random.random() * square_width * 0.5 * sign
            py = (np.random.random() - 0.5) * square_width
            collide = False
            for agent in agent_list:
                if norm((px - agent[0], py - agent[1])) < min_dist:
                    collide = True
                    break
            if not collide:
                break
        while True:
            gx = np.random.random() * square_width * 0.5 * -sign
            gy = (np.random.random() - 0.5) * square_width
            collide = False
            for agent in agent_list:
                if norm((gx - agent[2], gy - agent[3])) < min_dist:
                    collide = True
                    break
            if not collide:
                break

        positions.append((px, py))
        goals.append((gx, gy))
        sim.addAgent((px, py))
        vx = 0
        vy = 0
        speed.append((vx, vy))
        agent_list.append([px, py, gx, gy])
    trajectories = [[positions[i]] for i in range(num_ped)]
    return trajectories, positions, goals, speed

def overfit_initialize(num_ped, sim):
    """ Scenario initialization """

    # initialize agents' starting and goal positions
    x = np.linspace(-15, 15, 4)
    positions = []
    goals = []
    speed = []
    for i in range(4):
        # random_number = random.uniform(-0.3, 0.3)
        py = [-10, 10]
        gy = [10, -10]
        for j in range(2):
            px = x[i] + np.random.normal(0, 0.3) * np.sign(j)
            gx = x[i] + np.random.normal(0, 0.1) * np.sign(j)
            py_ = py[j] + i * 16/9 * np.sign(j) + random.uniform(-0.5, 0.5)
            gy_ = gy[j] + random.uniform(-0.5, 0.5)
            positions.append((px, py_))
            goals.append((gx, gy_))
            if sim is not None:
                sim.addAgent((px, py_))

            rand_speed = random.uniform(0.8, 1.2)
            vx = 0
            vy = rand_speed * np.sign(gy[j] - py_)
            speed.append((vx, vy))

    trajectories = [[positions[i]] for i in range(num_ped)]
    return trajectories, positions, goals, speed

def overfit_initialize_circle(num_ped, sim, center=(0,0), radius=10):
    positions = []
    goals = []
    speed = []
    step = (2 * np.pi) / num_ped
    radius = radius + np.random.uniform(-3, 3)
    for pos in range(num_ped):
        angle = pos * step 
        px = center[0] + radius * np.cos(angle)
        py_ = center[1] + radius * np.sin(angle)
        gx = center[0] + radius * np.cos(angle + np.pi)
        gy_ = center[1] + radius * np.sin(angle + np.pi)
        positions.append((px, py_))
        goals.append((gx, gy_))

        if sim is not None:
            sim.addAgent((px, py_))

        rand_speed = random.uniform(0.8, 1.2)
        vx = 0
        vy = 0
        speed.append((vx, vy))
        
    trajectories = [[positions[i]] for i in range(num_ped)]
    return trajectories, positions, goals, speed

def generate_orca_trajectory(num_ped, min_dist=3, react_time=1.5, end_range=1.0):
    """ Simulating Scenario using ORCA """

    ## Default 
    # sim = rvo2.PyRVOSimulator(1 / 60., 1.5, 5, 1.5, 2, 0.4, 2)
    ## CA
    # sim = rvo2.PyRVOSimulator(1 / 2.5, min_dist, 10, react_time, 2, 0.4, 2)
    ## Circle
    # sim = rvo2.PyRVOSimulator(1 / 2.5, 2, 10, 2, 2, 0.4, 1.2)
    ## Random Circle
    sim = rvo2.PyRVOSimulator(1 / 4, 10, 10, 5, 5, 0.3, 1)


    ##Initiliaze a scene
    # trajectories, _, goals, speed = overfit_initialize(num_ped, sim)
    # trajectories, positions, goals, speed = overfit_initialize_circle(num_ped, sim)
    trajectories, positions, goals, speed = generate_circle_crossing(num_ped, sim)
    # trajectories, positions, goals, speed = generate_square_crossing(num_ped, sim)

    done = False
    reaching_goal_by_ped = [False] * num_ped
    count = 0

    ##Simulate a scene
    while not done and count < 3000:
        sim.doStep()
        reaching_goal = []
        for i in range(num_ped):
            if count == 0:
                trajectories[i].pop(0)
            position = sim.getAgentPosition(i)

            ## Append only if Goal not reached
            if not reaching_goal_by_ped[i]:
                trajectories[i].append(position)

            # check if this agent reaches the goal
            if np.linalg.norm(np.array(position) - np.array(goals[i])) < end_range:
                reaching_goal.append(True)
                sim.setAgentPrefVelocity(i, (0, 0))
                reaching_goal_by_ped[i] = True
            else:
                reaching_goal.append(False)
                velocity = np.array((goals[i][0] - position[0], goals[i][1] - position[1]))
                speed = np.linalg.norm(velocity)
                pref_vel = 1 * velocity / speed if speed > 1 else velocity
                sim.setAgentPrefVelocity(i, tuple(pref_vel.tolist()))
        count += 1
        done = all(reaching_goal)

    return trajectories, count

def write_to_txt(trajectories, path, count, frame):
    """ Write Trajectories to the text file """

    last_frame = 0
    with open(path, 'a') as fo:
        track_data = []
        for i, _ in enumerate(trajectories):
            for t, _ in enumerate(trajectories[i]):

                track_data.append('{}, {}, {}, {}'.format(t+frame, count+i,
                                                          trajectories[i][t][0],
                                                          trajectories[i][t][1]))
                if t == len(trajectories[i])-1 and t+frame > last_frame:
                    last_frame = t+frame

        for track in track_data:
            fo.write(track)
            fo.write('\n')

    return last_frame

def viz(trajectories):
    """ Visualize Trajectories """
    for i, _ in enumerate(trajectories):
        trajectory = np.array(trajectories[i])
        plt.plot(trajectory[:, 0], trajectory[:, 1])

    plt.xlim(-5, 5)
    plt.xlim(-5, 5)
    plt.show()
    plt.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--simulator', default='orca',
                        choices=('orca', 'social_force'))
    parser.add_argument('--simulation_type', required=True)
    parser.add_argument('--test', default=False)

    args = parser.parse_args()

    if not os.path.isdir('./data'):
        os.makedirs('./data')

    # # train_params = [[2, 2.5], [3, 1], [3, 2], [4, 2]]
    # ## [3, 1] is close
    # ## [2, 2.5], [3, 2] is medium
    # ## [4, 2] is far
    dict_params = {}
    dict_params['close'] = [[3, 1]]
    dict_params['medium1'] = [[2, 2.5]]
    dict_params['medium2'] = [[3, 2]]
    dict_params['far'] = [[4, 2]]

    ## Circle
    # dict_params = {}
    # dict_params['medium1'] = [[0.6, 1]]
    params = dict_params[args.simulation_type]

    for min_dist, react_time in params:
        print("min_dist, time_react:", min_dist, react_time)
        ##Decide the number of scenes
        if not args.test:
            number_traj = 300
        else:
            number_traj = 10
        ##Decide number of people
        num_ped = 10

        count = 0
        last_frame = -5
        for i in range(number_traj):
            ## Print every 10th scene
            if (i+1) % 10 == 0:
                print(i)

            # ##Generate the scene
            trajectories, count = generate_orca_trajectory(num_ped=num_ped,
                                                           min_dist=min_dist,
                                                           react_time=react_time)

            # ##Write the Scene to Txt (for collision)
            if not args.test:
                last_frame = write_to_txt(trajectories, 'data/raw/controlled/'
                                          + 'circle_crossing.txt',
                                          count=count, frame=last_frame+5)
            else:
                last_frame = write_to_txt(trajectories, 'data/raw/controlled/test_'
                                          + args.simulator + '_traj_'
                                          + args.simulation_type + '.txt',
                                          count=count, frame=last_frame+5)

            # viz(trajectories)
            # print("Count: ", count)
            # ##Write the Scene to Txt (for collision)
            # if not args.test:
            #     last_frame = write_to_txt(trajectories, 'data/raw/controlled/'
            #                               + args.simulator + '_traj_'
            #                               + args.simulation_type + '.txt',
            #                               count=count, frame=last_frame+5)
            # else:
            #     last_frame = write_to_txt(trajectories, 'data/raw/controlled/test_'
            #                               + args.simulator + '_traj_'
            #                               + args.simulation_type + '.txt',
            #                               count=count, frame=last_frame+5)

            # ##Write the Scene to Txt (for Circle)
            # if not args.test:
            #     last_frame = write_to_txt(trajectories, 'data/raw/controlled/circle_'
            #                               + args.simulator + '_traj_'
            #                               + str(num_ped) + '.txt',
            #                               count=count, frame=last_frame+5)
            # else:
            #     last_frame = write_to_txt(trajectories, 'data/raw/controlled/circle_test_'
            #                               + args.simulator + '_traj_'
            #                               + args.simulation_type + '.txt',
            #                               count=count, frame=last_frame+5)

            count += num_ped

if __name__ == '__main__':
    main()
