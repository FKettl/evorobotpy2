import os                                                                        
import csv
import numpy as np
'''setting variables'''

''' experiment folder (relative path) '''
e_folder = '../felipe_experiments/done_experiments'

'''how many seeds do you want to run for each experiment?'''
number_of_seeds = 10

'''seed initial number'''
initial_seed_number = 1

def read_out(file):
    f = open(file, "r")
    x = [False, True, False, False, True, False, True, False, True, False, True, False, True, False, True, False, True]
    line = np.array(f.readline().split())
    f.close()
    return line[x]

e_list = os.listdir(e_folder)
number_of_experiments = len(e_list)
total_of_processes = number_of_experiments * int(number_of_seeds)

header = ['Seed', 'Gen', 'Msteps', 'Bestfit', 'Bestgit', 'Bestsam', 'Avgfit', 'Paramsize']

for i in e_list:
    file = open(f'./results/{i}.csv', 'w')
    writer = csv.writer(file)
    writer.writerow(header)
    seed=initial_seed_number
    for n in range(0, int(number_of_seeds)):
        out_name = f'S{n+1}.fit'
        file_path = e_folder+'/'+i+'/'+out_name
        writer.writerow(read_out(file_path))
        seed+=1
    file.close()

