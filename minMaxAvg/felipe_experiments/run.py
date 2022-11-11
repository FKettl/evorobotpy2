import os                                                                       
from multiprocessing import Pool 
from datetime import date
import time


'''setting variables'''

''' experiment folder (relative path) '''
e_folder = '../felipe_experiments/experimentos'

'''how many seeds do you want to run for each experiment?'''
number_of_seeds = 10

'''you can type the additional parameters that you want to use to run your experiments'''
additional_params = '-w 1'

'''how many experiments do you want to run simultaneously?'''
simultaneously = 5

'''seed initial number'''
initial_seed_number = 1


e_list = os.listdir(e_folder)


number_of_experiments = len(e_list)
total_of_processes = number_of_experiments * int(number_of_seeds)

commands_list = []

for i in e_list:
    seed=initial_seed_number
    for n in range(0, int(number_of_seeds)):
        
        find_folder = 'cd {}/{}'.format(e_folder, i)
        file_list = os.listdir(e_folder+'/'+i)
        ini_name = i+'.ini'
        for f in file_list:
            if '.ini' in f:
                if not '.txt' in f:
                    ini_name = f
        seed_command = 'nohup python3 -u ../../../bin/es.py -f {}'.format(ini_name)
        seed_command = seed_command + (' -s {} {} > s{}.out&'.format(seed, additional_params, seed))
        new_command = [find_folder,seed_command]
        print(new_command)
        commands_list.append(new_command)
        seed+=1

def run_process(processo):  
    os.system(processo[0]+'&&'+processo[1])                                                                                           
                                                                                
                                                                      
pool = Pool(processes=int(simultaneously))   
pool.map(run_process, commands_list)
print("{} seeds finished".format(total_of_processes))

arquivo = open('seeds_{}.txt'.format(date.today()), 'a')
for command in commands_list:
    arquivo.write(command[1]+'\n')
arquivo.close()