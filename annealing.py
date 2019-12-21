"""
A module for implementing simulated annealing.
"""
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm as تقدّم

import earth_data
import geometry
from genetics import random_population
from timer import timeit
import constants
import plot_funcs

dtime = datetime(2015, 5, 1)
clear_polys, big_clear_poly = earth_data.get_clear(dtime)
clear_points = earth_data.get_clear_polys(dtime, just_coords=True)
initial_points = random_population(clear_polys)[0]

T_init = 10       # Initial temperature
T_final = 0.001   # Final temperature
T_steps = 200      # Number of different temperatures in the cooling sequence
T_spin_flips = 100    # Number of spin flips at each temperature
T_schedule = np.linspace(T_init, T_final, T_steps, endpoint=True) # Linear cooling schedule
num_anneals = 50  # number of times to run the annealing procedure

def energy(points):
    """
    Compute the energy of a set of observations.

    Params:
        :points: A 1D numpy array of (lon, lat) tuples, points to observe
    Return:
        The energy of the configuration if we say coverage = energy.
    """
    return -1 * geometry.fast_coverage(points, big_clear_poly)


def metropolis_decision(initial_energy, flipped_energy, T):
    """
    Use the Metropolis criterion to decide whether to accept a new state. 

    Params:
        :initial_energy: energy of starting configuration
        :flipped_energy: energy of another configuration we are comparing with
        :T: the current temperature of the system
    
    Return:
        True if we should accept the flipped_energy state False otherwise
    """
    if flipped_energy < initial_energy:
        return True
    else:
        try:
            acceptance_prob = 0.1*np.exp((initial_energy - flipped_energy) / T)
            if acceptance_prob > 1:
                print(acceptance_prob)
        except FloatingPointError:
            # overflow/underflow errors in exp can happen if
            # initial energy and flipped energy are very different
            if initial_energy < flipped_energy:
                acceptance_prob = 1
            else:
                acceptance_prob = 0

        if np.random.rand() < acceptance_prob:
            return True
        else:
            return False


def get_radius(T):
    """get radius of how far away to move a point during SA"""
    return constants.re_km * (T / T_init)


#@profile
def move_point_within(point, radius, points):
    # all possible points to move to are given by clear poly centers
    # find all points to move to within the given radius

    # clear points we could move to
    clear_pts = [c for c in clear_points if c not in points]
    # randomize their order
    np.random.shuffle(clear_pts)
    # pick random indices until we find one within range or run out of points
    c = clear_pts.pop()
    r = geometry.arc_length(*point, *c)
    while r >= radius:
        try:
            c = clear_pts.pop()
        except IndexError:
            # we've run out of points to pop, i.e. no c is close enough
            return point
        r = geometry.arc_length(*point, *c)
    return c


def move_point_within_orig(point, radius, points):
    # all possible points to move to are given by clear poly centers
    # find all points to move to within the radius
    possible_points = []
    for c in clear_points:
        if c in points:
            continue
        lon1, lat1 = point
        lon2, lat2 = c
        r = geometry.arc_length(lon1, lat1, lon2=lon2, lat2=lat2)
        if r < radius:
            possible_points.append(c)
    rand_index = int(np.random.randint(0, high=len(possible_points)))
    return possible_points[rand_index]


#@profile
def metropolis_sa(points, point_to_move, T, initial_energy=None):
    """
    Run a single Monte Carlo step of SA. Flip a spin and decide whether to accept 
    the new configuration. Call the metropolis_decision method to help you here!
    
    Params:
        :points: A list of (lon, lat) tuples, points to observe.
        :point_to_move: An integer indicating which point should be moved.
        :T: the current temperature of the system

    Return:
        :return: The updated (or unchanged) lattice, and its energy
    """
    # Copy the lattice
    points_moved = points.copy()

    # Move the point to some other point within a certain radius
    point = points[point_to_move]
    radius = get_radius(T)
    points_moved[point_to_move] = move_point_within(point, radius, points)

    # Decide whether or not to accept
    if initial_energy is None:
        initial_energy = energy(points)
    flipped_energy = energy(points_moved)
    if metropolis_decision(initial_energy, flipped_energy, T):
        return points_moved, flipped_energy
    else:
        return points, initial_energy

#@profile
def simulated_annealing(T_schedule):
    """
    Run simulated annealing.
    
    Params:
        :T_schedule: A numpy array that is the list of temperatures.

    Return:
        :return: A list containing the energy of the system at the end
                 of each temperature step.
        :return: The final version of the lattice.
    """
    # Keeps track of the final energy at every temperature
    energy_per_step = []

    # Initialize a random starting point for the lattice
    points = list(initial_points)
    # Work through the temperature schedule and at each point
    #  - Perform T_sweeps attempts to flip random spins on the lattice
    #  - Store the energy of the final configuration in energy_per_step
    points_list = []
    for step in تقدّم(range(len(T_schedule))):
        T = T_schedule[step]
        step_energy = None
        for flip in تقدّم(range(T_spin_flips), leave=False):
            point_to_move = np.random.randint(0, len(points))
            points, step_energy = metropolis_sa(
                points, point_to_move, T, initial_energy=step_energy)
        energy_per_step.append(step_energy)
        points_list.append(points)
        plt.plot(energy_per_step)
        plt.savefig("e_per_step.png")
        plt.cla()
    min_energy = min(energy_per_step)
    min_energy_index = energy_per_step.index(min_energy)
    points = points_list[min_energy_index]
    return energy_per_step, points

print("doing simulated annealing from R =", get_radius(T_init), "km to", get_radius(T_final))
energy_per_step, points = simulated_annealing(T_schedule)
plot_funcs.plot_points(points, "Annealing_g0", dtime, show=False)
print(f"Minimum energy value found is {np.min(energy_per_step):.4f}")
best_energies = np.zeros(num_anneals)

#for anneal_run in range(num_anneals):
#    energy_per_step, points = simulated_annealing(T_schedule)
#    plot_funcs.plot_points(points, f"Annealing_g{anneal_run+1}", dtime, show=False)
#    best_energies[anneal_run] = energy_per_step[-1]

# Plot a histogram of the energy outputs
# We will store our best energy for comparison later
#our_best_energy = np.min(best_energies)
#plt.hist(best_energies)
#plt.show()
#print(f"Minimum energy found by SA is {our_best_energy:.4f}")
