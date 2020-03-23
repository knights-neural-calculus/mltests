# -*- coding: utf-8 -*-


import sys
import os
sys.path.insert(0,".")
sys.path.insert(0,"./base_SNN")
import numpy as np
import random
import copy
from random import uniform,shuffle,randrange
from enum import IntEnum, Enum
from utils import clear, decimal_to_binary_array, comma_join_int
import pprint
import brain
import visualization
import utils 
import json
import functools



def init_mega_grid_params():
	brain.Mutation_params.set_mutation_to_default_1(brain.Mutation_params)
	brain.Mutation_params.neuron_start_count = 1
	brain.Mutation_params.neuron_count_bias = .5
	brain.Mutation_params.target_count_bias = .5
	brain.Mutation_params.neuron_count_prob = .05
	brain.Mutation_params.target_count_prob = .05
	brain.Mutation_params.potential_prob = .05
	brain.Mutation_params.threshold_prob = .05
	brain.Mutation_params.sensory_prob = .05
	brain.Mutation_params.actuating_prob = .05
	brain.Mutation_params.hidden_prob = .05
	brain.Mutation_params.input_count = 6
	brain.Mutation_params.reflex_pair_prob = 0
	brain.Mutation_params.mutation_cycles = 1
	brain.Mutation_params.output_count = 7
	brain.Mutation_params.upper_input_bounds = [.0000001] * 6
	brain.Mutation_params.lower_input_bounds = [-.0000001] * 6


def default_policy(grid_instance):
	if grid.info[Object_type.AGENT] > 50:
		grid.baseline_densities[Object_type.STRIDER] = (grid.info[Object_type.AGENT] - 50)/ 100
	else:
		grid.baseline_densities[Object_type.STRIDER] = .004


class Object_type(IntEnum):
	EMPTY = 0
	AGENT = 1
	STRIDER = 2
	CAPSULE = 3



# enum for direction, we're going to be a bit hacky with this and actually use the integer to make cycling through directions easier
class Direction(IntEnum):
	UP = 0
	RIGHT = 1
	DOWN = 2
	LEFT = 3


class Action_type (IntEnum):
	PASS = 0
	MOVE = 1
	BITE = 2





def apply_direction_offset(direction, offset):
		offset = int(offset)
		return Direction((direction + offset) % 4)




class Grid():

	object_colors = {Object_type.AGENT: (1,0,0), Object_type.STRIDER: (0,1,0), Object_type.CAPSULE: (0,0,1)}

	def __init__(self, sector_size):
		self.info = {Object_type.AGENT : 0, Object_type.EMPTY: sector_size * sector_size, Object_type.CAPSULE : 0, Object_type.STRIDER : 0} 
		sector_shape = (sector_size, sector_size)
		self.grid = np.zeros(sector_shape)
		self.agents = {}
		self.striders = {}
		self.action_queue = []
		# for objects which may experience spontaneous generation and degeneration, these numbers
		# describe as a percent the percent of occupied space generation and degeneration will trend 
		# towards for each item. 
		self.baseline_densities = { Object_type.EMPTY : .74 , Object_type.STRIDER : .01, Object_type.CAPSULE : .25}
		# specifies whether spontaneous degeneration is enabled for items.
		self.degen_enabled = {Object_type.AGENT : False, Object_type.STRIDER: True , Object_type.CAPSULE : True ,Object_type.EMPTY : True}
		self.sector_size = sector_size
		self.capsule_energy_content = 20
		self.mutation_probability = .5

	def visualize_grid(self):
		for i in range(self.sector_size):
			for c in range(self.sector_size):
				print(int(self.grid[i][c]), end = "")
			print()

	def print_grid_to_json(self, string = True):
		log = {}
		log['info'] = self.info
		log['grid'] = self.grid.tolist()
		log['agents'] = {}
		for key in self.agents:
			log['agents'][functools.reduce(comma_join_int,key)] = self.agents[key].print_agent_to_json()
		log['striders'] = {}
		for key in self.striders:
			log['striders'][functools.reduce(comma_join_int,key)] = self.striders[key].print_strider_to_json()
		log['action_queue'] = self.action_queue
		log['baseline_densities'] = self.baseline_densities
		log['degen_enabled'] = self.degen_enabled
		log['sector_size'] = self.sector_size
		log['capsule_energy_content'] = self.capsule_energy_content
		log['mutation_probability'] = self.mutation_probability
		
		if string:
			return json.dumps(log, indent = 4)
		else:
			return log
		
	def save_grid_to_file(self):
		output = self.print_grid_to_json()
		output_file = open('log.txt', 'w')
		output_file.write(output)
		output_file.close()

	def visualize_detailed_grid(self):
		for i in range(self.sector_size):
			for c in range(self.sector_size):
				if self.grid[i][c] == int(Object_type.AGENT):
					if self.agents[(c,i)].direction == Direction.UP:
						print('^' , end = "")
					if self.agents[(c,i)].direction == Direction.RIGHT:
						print('>' , end = "")
					if self.agents[(c,i)].direction == Direction.DOWN:
						print('v' , end = "")
					if self.agents[(c,i)].direction == Direction.LEFT:
						print('<' , end = "")
				elif self.grid[i][c] == int(Object_type.STRIDER):
					if self.striders[(c,i)].direction == Direction.UP:
						print('A' , end = "")
					if self.striders[(c,i)].direction == Direction.RIGHT:
						print(')' , end = "")
					if self.striders[(c,i)].direction == Direction.DOWN:
						print('U' , end = "")
					if self.striders[(c,i)].direction == Direction.LEFT:
						print('(' , end = "")
				else:
					print(int(self.grid[i][c]), end = "")
			print()


	def add_object(self, coords, object_type): #todo add new brain 
		if not (self.grid[coords[1]][coords[0]] == int(Object_type.EMPTY)):
			return 
		if object_type == Object_type.AGENT:
			self.info[Object_type.AGENT] += 1
			self.info[Object_type.EMPTY] -= 1
			self.grid[coords[1]][coords[0]] = int(Object_type.AGENT)
			brain_instance = brain.Brain()
			self.agents[coords] = Agent(brain_instance)
		if object_type == Object_type.STRIDER:
			self.info[Object_type.STRIDER] += 1
			self.info[Object_type.EMPTY] -= 1
			self.grid[coords[1]][coords[0]] = int(Object_type.STRIDER)
			self.striders[coords] = Strider()
		if object_type == Object_type.CAPSULE:
			self.info[Object_type.CAPSULE] += 1
			self.info[Object_type.EMPTY] -= 1
			self.grid[coords[1]][coords[0]] = int(Object_type.CAPSULE)

	def remove_object(self, coords):
		if self.grid[coords[1]][coords[0]] == int(Object_type.EMPTY):
			return
		elif self.grid[coords[1]][coords[0]] == int(Object_type.AGENT):
			self.grid[coords[1]][coords[0]] = int(Object_type.EMPTY)
			del self.agents[coords]
			self.info[Object_type.AGENT] -= 1
			self.info[Object_type.EMPTY] += 1
		elif self.grid[coords[1]][coords[0]] == int(Object_type.STRIDER):
			self.grid[coords[1]][coords[0]] = int(Object_type.EMPTY)
			del self.striders[coords]
			self.info[Object_type.STRIDER] -= 1
			self.info[Object_type.EMPTY] += 1
		elif self.grid[coords[1]][coords[0]] == int(Object_type.CAPSULE):
			self.grid[coords[1]][coords[0]] = int(Object_type.EMPTY)
			self.info[Object_type.CAPSULE] -= 1
			self.info[Object_type.EMPTY] += 1
		




	def check_bounds(self, coords):
		for coord in coords:
			if coord < 0 or coord >= self.sector_size:
				return False
		return True

	def check_movement(self, coords):
		if not self.check_bounds(coords):
			return False
		if Object_type(self.grid[coords[1]][coords[0]]) != Object_type.EMPTY:
			return False
		return True

	def move(self, start, dest):
		if not self.check_movement(dest):
			return
		if Object_type(self.grid[start[1]][start[0]]) == Object_type.AGENT:
				self.grid[dest[1]][dest[0]] = self.grid[start[1]][start[0]]
				self.grid[start[1]][start[0]] = int(Object_type.EMPTY)
				assert(start in self.agents.keys())
				agent = self.agents.pop(start)
				self.agents[dest] = agent 
		if Object_type(self.grid[start[1]][start[0]]) == Object_type.STRIDER:
				self.grid[dest[1]][dest[0]] = self.grid[start[1]][start[0]]
				self.grid[start[1]][start[0]] = int(Object_type.EMPTY)
				assert(start in self.striders.keys())
				strider = self.striders.pop(start)
				self.striders[dest] = strider 

	def bite(self, start, dest):
		if not self.check_bounds(dest):
			return
		if  Object_type(self.grid[start[1]][start[0]]) == Object_type.AGENT and Object_type(self.grid[dest[1]][dest[0]]) == Object_type.CAPSULE:
			self.agents[start].energy += self.capsule_energy_content
			self.remove_object(dest)
		elif  Object_type(self.grid[start[1]][start[0]]) == Object_type.STRIDER and Object_type(self.grid[dest[1]][dest[0]]) == Object_type.AGENT:
			self.remove_object(dest)
		elif  Object_type(self.grid[start[1]][start[0]]) == Object_type.STRIDER and Object_type(self.grid[dest[1]][dest[0]]) == Object_type.CAPSULE:
			self.remove_object(dest)
	
	def get_rear_cell(self, coords):
		agent = self.agents[coords]
		if agent.direction == Direction.UP:
			return (coords[0], coords[1]+1)
		elif agent.direction == Direction.LEFT:
			return (coords[0]+1, coords[1])
		elif agent.direction == Direction.DOWN:
			return (coords[0], coords[1]-1)
		elif agent.direction == Direction.RIGHT:
			return (coords[0]-1, coords[1])



	def reproduce_agent(self, coords):
		agent = self.agents[coords]
		target_location = self.get_rear_cell(coords)
		if self.check_movement(target_location):
			brain_replica = copy.deepcopy(agent.brain)
			self.add_object(target_location, Object_type.AGENT)
			self.agents[target_location].brain = brain_replica
			if uniform(0,1) < self.mutation_probability:
				self.agents[target_location].mutate()
				self.agents[target_location].mutations = agent.mutations + 1			


	###
	# ray tracing in a 2 dimensional discrete grid to determine the value of a single pixel sensor
	# we use the three least signficiant bits to encode depth perception information
	###
	def sense(self, coordinates, direction): 
		x_coord = coordinates[0] 
		y_coord = coordinates[1]
		distance = 0
		if direction == Direction.UP:
			while y_coord > 0:
				y_coord -= 1
				if self.grid[y_coord][x_coord] != int(Object_type.EMPTY):
					return self.object_colors[Object_type(self.grid[y_coord][x_coord])] + tuple(decimal_to_binary_array(distance, bounded = True, bound = 7, fixed_length = True, length = 3))
				distance += 1

		elif direction == Direction.LEFT:
			while x_coord > 0:
				x_coord -= 1
				if self.grid[y_coord][x_coord] != int(Object_type.EMPTY):
					return self.object_colors[Object_type(self.grid[y_coord][x_coord])] + tuple(decimal_to_binary_array(distance, bounded = True, bound = 7, fixed_length = True, length = 3))
				distance += 1


		elif direction == Direction.RIGHT:
			while x_coord < self.sector_size-1:
				x_coord += 1
				if self.grid[y_coord][x_coord] != int(Object_type.EMPTY):
					return self.object_colors[Object_type(self.grid[y_coord][x_coord])] + tuple(decimal_to_binary_array(distance, bounded = True, bound = 7, fixed_length = True, length = 3))
				distance += 1

		elif direction == Direction.DOWN:
			while y_coord < self.sector_size-1:
				y_coord += 1
				if self.grid[y_coord][x_coord] != int(Object_type.EMPTY):
					return self.object_colors[Object_type(self.grid[y_coord][x_coord])] + tuple(decimal_to_binary_array(distance, bounded = True, bound = 7, fixed_length = True, length = 3))
				distance += 1

		return (0,0,0) + tuple(decimal_to_binary_array(distance, bounded = True, bound = 7, fixed_length = True, length = 3))

	def norm_dict(self, value_dict):
		result = copy.deepcopy(value_dict)
		val_sum = sum(result.values())
		for key in value_dict:
			result[key] = result[key]/float(val_sum) 
		return result

	def populate_to_percent(self, object_type, density):
		for i in range(self.sector_size):
			for c in range(self.sector_size):
				if uniform(0,1) <= density and self.grid[i][c] != int(object_type):
					self.remove_object((c,i))
					self.add_object((c,i), object_type)
				




	def passive_cell_update(self, curr_sym, offsets, baseline_densities):
		if (uniform(0,1)  < sum ([abs(value) for value in offsets.values()]) / len(list(baseline_densities.values()))) and self.degen_enabled[Object_type(curr_sym)]:
			selector = uniform(0,1)
			total_prob = 0
			normed_offsets = self.norm_dict(offsets)
			for key, value in sorted(normed_offsets.items()): #this sort is important because otherwise dictionary 
				total_prob += value # iteration order is not guaranteed to be consistent
				if total_prob  >= selector:
					return key
		return Object_type(curr_sym)

	def passive_physics(self):
		old_info = copy.deepcopy(self.info)
		densities = dict([(key, old_info[key]/ (self.sector_size * self.sector_size)) for key in old_info])
		offsets = dict([(key,max(self.baseline_densities[key] - densities[key],0)) for key in self.baseline_densities])	
		for i in range(self.sector_size):
			for c in range(self.sector_size):
				sym = self.passive_cell_update(self.grid[i][c],offsets, self.baseline_densities)
				if int(sym) != self.grid[i][c]:
					self.remove_object((c,i))
					self.add_object((c,i), sym)
			


	def advance_agents(self,visualization_mode):
		## get randomly ordered list of agents, sense, run, harvest actuation and publish to action_queue
		agent_keys = list(self.agents.keys())
		shuffle(agent_keys)
		for key in agent_keys: #useful to note here that each 'key' is a tuple containing agent location in (x,y) format
			agent = self.agents[key]
			assert(self.grid[key[1]][key[0]] == Object_type.AGENT)
			agent.age += 1
			if agent.energy <= 0:
				self.remove_object(key)
				continue
			elif agent.energy > 200:
				self.reproduce_agent(key)
				agent.energy -= 100
			
			agent.energy -= 1
			
			#sense
			observations = self.sense(key, agent.direction)
			output = []
			#for i in range(len(observations)): ## setting our bounds appropriately for threshold mutations
			#	brain.Mutation_params().upper_input_bounds[i] = max(brain.Mutation_params().upper_input_bounds[i],observations[i])
			#	brain.Mutation_params().lower_input_bounds[i] = min(brain.Mutation_params().lower_input_bounds[i],observations[i])
			agent.brain.update_input_bounds(observations)

			result = agent.brain.advance_n_with_mode(observations, 	brain.Mutation_params.output_count , 10, visualization_mode)
			
			
			
			numerical_result = utils.binary_array_to_decimal(result)
		#	print(result)
		#	print(numerical_result)
			if visualization_mode == visualization.Visualization_flags.VISUALIZATION_ON:
				print("OUTPUT:\n" + str(result))
				print("INPUT:\n" + str(observations))

			agent.generate_action(numerical_result, self, key)

	def advance_striders(self,visualization_mode):
		## get randomly ordered list of striders, sense, run, harvest actuation and publish to action_queue
		strider_keys = list(self.striders.keys())
		shuffle(strider_keys)
		for key in strider_keys: #useful to note here that each 'key' is a tuple containing strider location in (x,y) format
			strider = self.striders[key]
			assert(self.grid[key[1]][key[0]] == Object_type.STRIDER)
	
			
			#sense
			observations = self.sense(key, strider.direction)	

			if observations[:3] == (1,0,0):
				observations = (0,0,1) + observations[3:]



			output = []
			strider.brain.update_input_bounds(observations)		

			result = strider.brain.advance_n_with_mode(observations, 	brain.Mutation_params.output_count , 10, visualization_mode)
						
			numerical_result = utils.binary_array_to_decimal(result)
			if visualization_mode == visualization.Visualization_flags.VISUALIZATION_ON:
				print("OUTPUT:\n" + str(result))
				print("INPUT:\n" + str(observations))

			strider.generate_action(numerical_result, self, key)


	def active_physics(self):
		for action in self.action_queue:
			if (action[2] == Action_type.MOVE):
				self.move(action[0], action[1])
			elif (action[2] == Action_type.BITE):
			#	print("CHOMP")
				self.bite(action[0], action[1])
		self.action_queue = []



			#public to action_queue

	###
	# moves the agent if there is no physical obstruction in the world, updating both the the agent's and the world's info for the new frame of time. 
	###
	def publish_movement_action(self , relative_direction, agent, coords):
		move_direction = apply_direction_offset(agent.direction,relative_direction)
		if move_direction == Direction.UP:
			new_coords = (coords[0], coords[1]-1)
			self.action_queue.append((coords, new_coords , Action_type.MOVE))
		elif move_direction == Direction.RIGHT:
			new_coords = (coords[0]+1, coords[1])
			self.action_queue.append((coords, new_coords,Action_type.MOVE))
		elif move_direction == Direction.DOWN:
			new_coords = (coords[0], coords[1]+1)
			self.action_queue.append((coords, new_coords,Action_type.MOVE))
		elif move_direction == Direction.LEFT:
			new_coords = (coords[0]-1, coords[1])
			self.action_queue.append((coords, new_coords,Action_type.MOVE))


	def publish_bite_action(self,agent,coords):
		if agent.direction == Direction.UP:
			new_coords = (coords[0], coords[1]-1)
			self.action_queue.append((coords, new_coords , Action_type.BITE))
		elif agent.direction == Direction.RIGHT:
			new_coords = (coords[0]+1, coords[1])
			self.action_queue.append((coords, new_coords,Action_type.BITE))
		elif agent.direction == Direction.DOWN:
			new_coords = (coords[0], coords[1]+1)
			self.action_queue.append((coords, new_coords,Action_type.BITE))
		elif agent.direction == Direction.LEFT:
			new_coords = (coords[0]-1, coords[1])
			self.action_queue.append((coords, new_coords,Action_type.BITE))




class Agent():
	def __init__(self, brain):
		self.brain = brain
		self.direction = Direction.UP
		self.energy = 20
		self.age = 0
		self.mutations = 0 # this gets incremented only for offspring with a mutation

	def	__repr__(self):
		return "<Agent age:%s, mutations:%s>" % (self.age, self.mutations)


	## sensing calculate sensory data
	## evaluation decide on action
	## active physics(actuation phase)

	def print_agent_to_json(self):
		result = {}
		result['brain'] = brain.print_brain_to_json(self.brain, string = False)
		result['direction'] = self.direction
		result['energy'] = self.energy
		result['age'] = self.age
		result['mutations'] = self.mutations
		return result

	def mutate(self):
		self.brain.default_mutation(6,7)
		
	##
	# should only be called with Direction.LEFT or Direction.RIGHT
	##
	def turn(self, turn_direction):
		self.direction = apply_direction_offset(self.direction,turn_direction)

	
	def generate_action(self, selection, grid, coords):
		#print(selection)
		if selection == 0:
			pass ## no action (no action will also be applied if no elif is triggered)
		elif selection == 1:
			self.turn(Direction.LEFT)
		elif selection == 2:
			self.turn(Direction.RIGHT)
		elif selection == 4:
			grid.publish_movement_action(Direction.UP, self, coords)
		elif selection == 8:
			grid.publish_movement_action(Direction.RIGHT, self, coords)
		elif selection == 16:
			grid.publish_movement_action(Direction.DOWN, self, coords)
		elif selection == 32:
			grid.publish_movement_action(Direction.LEFT, self, coords)
		elif selection == 64:
			grid.publish_bite_action(self,coords)
		
		
class Strider():
	def __init__(self):
		self.brain = brain.load_brain_from_file("./topologies/sologrid/save.6") # this is a temporary solution
		self.direction = Direction.UP
	
	##
	# should only be called with Direction.LEFT or Direction.RIGHT
	##
	def turn(self, turn_direction):
		self.direction = apply_direction_offset(self.direction,turn_direction)


	def generate_action(self, selection, grid, coords):
		#print(selection)
		if selection == 0:
			pass ## no action (no action will also be applied if no elif is triggered)
		elif selection == 1:
			self.turn(Direction.LEFT)
		elif selection == 2:
			self.turn(Direction.RIGHT)
		elif selection == 4:
			grid.publish_movement_action(Direction.UP, self, coords)
		elif selection == 8:
			grid.publish_movement_action(Direction.RIGHT, self, coords)
		elif selection == 16:
			grid.publish_movement_action(Direction.DOWN, self, coords)
		elif selection == 32:
			grid.publish_movement_action(Direction.LEFT, self, coords)
		elif selection == 64:
			grid.publish_bite_action(self,coords)

	def print_strider_to_json(self):
		result = {}
		result['direction'] = self.direction
		return result


#phases of a world-frame
#passive physics phase:
#spontaneous generation/degeneration based on sector-wide stats

#physics/agent pass
# physics objects and agent updates
if __name__ == '__main__':

	if len(sys.argv) == 2:

		starter_brain = brain.load_brain_from_file(sys.argv[1])

		init_mega_grid_params()
		grid = Grid(40)
		grid.baseline_densities = {	Object_type.EMPTY : 0.60, 
									Object_type.CAPSULE : 0.396,
									Object_type.STRIDER : .004
								}
		for i in range(20):
			location = (randrange(0,40),randrange(0,40))
			grid.add_object(location, Object_type.AGENT)
			grid.agents[location].brain = copy.deepcopy(starter_brain)

		for i in range(5):
			location = (randrange(0,40),randrange(0,40))
			grid.add_object(location, Object_type.STRIDER)

		for i in range(10000):

			grid.passive_physics()
			grid.advance_agents(visualization.Visualization_flags.VISUALIZATION_OFF)
			grid.advance_striders(visualization.Visualization_flags.VISUALIZATION_OFF)
			grid.active_physics()
			default_policy(grid)
			grid.visualize_detailed_grid()
			pprint.pprint(grid.info)
			print("WORLD AGE: " + str(i))
			clear(0)
		grid.save_grid_to_file()



		



