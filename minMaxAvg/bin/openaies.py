#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
   This file belong to https://github.com/snolfi/evorobotpy
   and has been written by Stefano Nolfi and Paolo Pagliuca, stefano.nolfi@istc.cnr.it, paolo.pagliuca@istc.cnr.it
   salimans.py include an implementation of the OpenAI-ES algorithm described in
   Salimans T., Ho J., Chen X., Sidor S & Sutskever I. (2017). Evolution strategies as a scalable alternative to reinforcement learning. arXiv:1703.03864v2
   requires es.py, policy.py, and evoalgo.py 
"""

import numpy as np
from numpy import zeros, ones, dot, sqrt
import math
import time
from evoalgo import EvoAlgo
from utils import ascendent_sort
import sys
import os
import configparser

# Parallel implementation of Open-AI-ES algorithm developed by Salimans et al. (2017)
# the workers evaluate a fraction of the population in parallel
# the master post-evaluate the best sample of the last generation and eventually update the input normalization vector

class Algo(EvoAlgo):
    def __init__(self, env, policy, seed, fileini, filedir):
        EvoAlgo.__init__(self, env, policy, seed, fileini, filedir)
        self.ievReg = []

    def loadhyperparameters(self):

        if os.path.isfile(self.fileini):

            config = configparser.ConfigParser()
            config.read(self.fileini)
            self.maxsteps = 1000000
            self.stepsize = 0.01
            self.batchSize = 20
            self.noiseStdDev = 0.02
            self.wdecay = 0
            self.symseed = 1
            self.saveeach = 60
            self.percentual_env_var = 1  
            self.weight_utilities_exp = None          
            options = config.options("ALGO")
            for o in options:
                found = 0
                if o == "maxmsteps":
                    self.maxsteps = config.getint("ALGO","maxmsteps") * 1000000
                    found = 1
                if o == "stepsize":
                    self.stepsize = config.getfloat("ALGO","stepsize")
                    found = 1
                if o == "noisestddev":
                    self.noiseStdDev = config.getfloat("ALGO","noiseStdDev")
                    found = 1
                if o == "samplesize":
                    self.batchSize = config.getint("ALGO","sampleSize")
                    found = 1
                if o == "wdecay":
                    self.wdecay = config.getint("ALGO","wdecay")
                    found = 1
                if o == "symseed":
                    self.symseed = config.getint("ALGO","symseed")
                    found = 1
                if o == "saveeach":
                    self.saveeach = config.getint("ALGO","saveeach")
                    found = 1                
                if o == "percentual_env_var":
                    self.percentual_env_var = config.getfloat("ALGO","percentual_env_var")
                    found = 1
                if o == "weight_utilities_exp":
                    self.weight_utilities_exp = config.getint("ALGO","weight_utilities_exp")
                    if self.weight_utilities_exp < 0 or self.weight_utilities_exp%2==0:
                        exit("ERROR: param weight_utilities_exp needs to be positive and odd")
                    found = 1

                if found == 0:
                    print("\033[1mOption %s in section [ALGO] of %s file is unknown\033[0m" % (o, filename))
                    print("available hyperparameters are: ")
                    print("maxmsteps [integer]       : max number of (million) steps (default 1)")
                    print("stepsize [float]          : learning stepsize (default 0.01)")
                    print("samplesize [int]          : popsize/2 (default 20)")
                    print("noiseStdDev [float]       : samples noise (default 0.02)")
                    print("wdecay [0/2]              : weight decay (default 0), 1 = L1, 2 = L2")
                    print("symseed [0/1]             : same environmental seed to evaluate symmetrical samples [default 1]")
                    print("saveeach [integer]        : save file every N minutes (default 60)")

                    sys.exit()
        else:
            print("\033[1mERROR: configuration file %s does not exist\033[0m" % (self.fileini))
    


    def setProcess(self):
        self.loadhyperparameters()               # load hyperparameters
        self.center = np.copy(self.policy.get_trainable_flat())  # the initial centroid
        self.nparams = len(self.center)          # number of adaptive parameters
        self.cgen = 0                            # currrent generation
        self.samplefitness = zeros(self.batchSize * 2) # the fitness of the samples
        self.samplefitness2 = zeros(self.batchSize * 2) # the fitness of the samples during the re-test used to compute the iav measure
        self.samples = None                      # the random samples
        self.m = zeros(self.nparams)             # Adam: momentum vector 
        self.v = zeros(self.nparams)             # Adam: second momentum vector (adam)
        self.epsilon = 1e-08                     # Adam: To avoid numerical issues with division by zero...
        self.beta1 = 0.9                         # Adam: beta1
        self.beta2 = 0.999                       # Adam: beta2
        self.bestgfit = -99999999                # the best generalization fitness
        self.bfit = 0                            # the fitness of the best sample
        self.gfit = 0                            # the postevaluation fitness of the best sample of last generation
        self.rs = None                           # random number generator
        self.inormepisodes = self.batchSize * 2 * self.policy.ntrials / 100.0 # number of normalization episode for generation (1% of generation episodes)
        self.tnormepisodes = 0.0                 # total epsidoes in which normalization data should be collected so far
        self.normepisodes = 0                    # numer of episodes in which normalization data has been actually collected so far
        self.normalizationdatacollected = False  # whether we collected data for updating the normalization vector

    def savedata(self):
        self.save()             # save the best agent so far, the best postevaluated agent so far, and progress data across generations
        fname = self.filedir + "/S" + str(self.seed) + ".fit"
        fp = open(fname, "w")   # save summary
        fp.write('Seed %d (%.1f%%) gen %d msteps %d bestfit %.2f bestgfit %.2f bestsam %.2f avgfit %.2f paramsize %.2f \n' %
             (self.seed, self.steps / float(self.maxsteps) * 100, self.cgen, self.steps / 1000000, self.bestfit, self.bestgfit, self.bfit, self.avgfit, self.avecenter))
        fp.close()
 
    def evaluate(self):
        cseed = self.seed + self.cgen * self.batchSize  # Set the seed for current generation (master and workers have the same seed)
        self.rs = np.random.RandomState(cseed)
        self.samples = self.rs.randn(self.batchSize, self.nparams)
        self.cgen += 1

        # evaluate samples
        #self.policy.env.robot.setposturerange(0.03)
        candidate = np.arange(self.nparams, dtype=np.float64)
        for b in range(self.batchSize):               
            for bb in range(2):
                if (bb == 0):
                    candidate = self.center + self.samples[b,:] * self.noiseStdDev
                else:
                    candidate = self.center - self.samples[b,:] * self.noiseStdDev
                self.policy.set_trainable_flat(candidate)
                self.policy.nn.normphase(0) # normalization data is collected during the post-evaluation of the best sample of he previous generation
                eval_rews, eval_length = self.policy.rollout(self.policy.ntrials, seed=(self.seed + (self.cgen * self.batchSize) + b))
                self.samplefitness[b*2+bb] = eval_rews
                self.steps += eval_length

                # we re-evaluate the individuals to estimate the iev measure
                if (((self.cgen - 1) % 1) == 0): #- changing for evaluating them at each generation
                    eval_rews, eval_length = self.policy.rollout(self.policy.ntrials, seed=(self.seed + (self.cgen * self.batchSize) + b + 999))  
                    self.samplefitness2[b*2+bb] = eval_rews

        fitness, self.index = ascendent_sort(self.samplefitness)       # sort the fitness
        self.avgfit = np.average(fitness)                         # compute the average fitness                   

        self.bfit = fitness[(self.batchSize * 2) - 1]
        bidx = self.index[(self.batchSize * 2) - 1]  
        if ((bidx % 2) == 0):                                     # regenerate the genotype of the best samples
            bestid = int(bidx / 2)
            self.bestsol = self.center + self.samples[bestid] * self.noiseStdDev  
        else:
            bestid = int(bidx / 2)
            self.bestsol = self.center - self.samples[bestid] * self.noiseStdDev

        self.updateBest(self.bfit, self.bestsol)                  # Stored if it is the best obtained so far 
                
        # postevaluate best sample of the last generation
        # in openaiesp.py this is done the next generation, move this section before the section "evaluate samples" to produce identical results
        gfit = 0
        #self.policy.env.robot.setposturerange(0.03)
        if self.bestsol is not None:
            self.policy.set_trainable_flat(self.bestsol)
            self.tnormepisodes += self.inormepisodes

            #setting the default values for initial posture variation
            currentRandInitLow = self.policy.env.robot.randInitLow
            currentRandInitHigh = self.policy.env.robot.randInitHigh
            self.policy.env.robot.randInitLow = self.defaultRandInitLow
            self.policy.env.robot.randInitHigh = self.defaultRandInitHigh

            #using the average fitness on the generalization test
            evol_max_fitness_weight = self.policy.max_fitness_weight
            evol_avg_fitness_weight = self.policy.avg_fitness_weight
            evol_min_fitness_weight = self.policy.min_fitness_weight
            self.policy.max_fitness_weight = self.policy.min_fitness_weight = 0
            self.policy.avg_fitness_weight = 1

            if self.policy.normalize == 1 and self.normepisodes < self.tnormepisodes:
                self.policy.nn.normphase(1)
                self.normepisodes += 1  # we collect normalization data
                self.normalizationdatacollected = True
            else:
                self.policy.nn.normphase(0)

            gfit, eval_length = self.policy.rollout(self.policy.nttrials, seed=(self.seed + 100000))
            self.steps += eval_length
            self.updateBestg(gfit, self.bestsol)
            
            #resetting the fitness weights
            self.policy.max_fitness_weight = evol_max_fitness_weight
            self.policy.avg_fitness_weight = evol_avg_fitness_weight
            self.policy.min_fitness_weight = evol_min_fitness_weight 

            #reset the experimental environmental variation
            self.policy.env.robot.randInitLow = currentRandInitLow
            self.policy.env.robot.randInitHigh = currentRandInitHigh
            
        # we compute the iev measure
        if (((self.cgen - 1) % 1) == 0):
           fitness2, index2 = ascendent_sort(self.samplefitness2)
           popsize = self.batchSize * 2
           utilities = zeros(popsize)
           utilities2 = zeros(popsize)
           for i in range(popsize):
              utilities[self.index[i]] = i
           utilities /= (popsize - 1)
           for i in range(popsize):
              utilities2[index2[i]] = i
           utilities2 /= (popsize - 1)
           iev = 0
           for i in range(popsize):
               iev += abs(utilities[i] - utilities2[i])
            
           print(f" =*=*=* GEN {self.cgen} - IEV = {iev/popsize} =*=*=*")
           self.ievReg.append(iev/popsize)


    def optimize(self):
            
        popsize = self.batchSize * 2                              # compute a vector of utilities [-0.5,0.5]
        utilities = zeros(popsize)
        for i in range(popsize):
            utilities[self.index[i]] = i
        utilities /= (popsize - 1)
        utilities -= 0.5

        if self.weight_utilities_exp is not None:
            #only odd values have to be used, the greater the value, the more intermediate values will be ignored
            utilities= utilities**self.weight_utilities_exp
            utilities = (utilities/np.max(utilities))/2 #this keeps the values between -0.5 to 0.5
            print(utilities)
        
        weights = zeros(self.batchSize)                           # Assign the weights (utility) to samples on the basis of their fitness rank
        for i in range(self.batchSize):
            idx = 2 * i
            weights[i] = (utilities[idx] - utilities[idx + 1])    # merge the utility of symmetric samples

        g = 0.0
        i = 0
        while i < self.batchSize:                                 # Compute the gradient (the dot product of the samples for their utilities)
            gsize = -1
            if self.batchSize - i < 500:                          # if the popsize is larger than 500, compute the gradient for multiple sub-populations
                gsize = self.batchSize - i
            else:
                gsize = 500
            g += dot(weights[i:i + gsize], self.samples[i:i + gsize,:]) 
            i += gsize
        g /= popsize                                              # normalize the gradient for the popsize
        
        if self.wdecay == 1:
            globalg = -g + 0.005 * self.center                    # apply weight decay
        else:
            globalg = -g

        # adam stochastic optimizer
        a = self.stepsize * sqrt(1.0 - self.beta2 ** self.cgen) / (1.0 - self.beta1 ** self.cgen)
        self.m = self.beta1 * self.m + (1.0 - self.beta1) * globalg
        self.v = self.beta2 * self.v + (1.0 - self.beta2) * (globalg * globalg)
        dCenter = -a * self.m / (sqrt(self.v) + self.epsilon)
        
        self.center += dCenter                                    # move the center in the direction of the momentum vectors
        self.avecenter = np.average(np.absolute(self.center))      


    def run(self):

        self.setProcess()                           # initialize class variables
        start_time = time.time()
        last_save_time = start_time
        elapsed = 0
        self.steps = 0
        print("Salimans: seed %d maxmsteps %d batchSize %d stepsize %lf noiseStdDev %lf wdecay %d symseed %d nparams %d" % (self.seed, self.maxsteps / 1000000, self.batchSize, self.stepsize, self.noiseStdDev, self.wdecay, self.symseed, self.nparams))
        self.defaultRandInitLow = self.policy.env.robot.randInitLow
        self.defaultRandInitHigh = self.policy.env.robot.randInitHigh

        #applying the initial environmental variation        
        self.policy.env.robot.randInitLow = self.defaultRandInitLow*self.percentual_env_var
        self.policy.env.robot.randInitHigh = self.defaultRandInitHigh*self.percentual_env_var
        print(f"####USING {self.percentual_env_var*100} of the default environmental variation - actual range = [{self.policy.env.robot.randInitLow},{self.policy.env.robot.randInitHigh}]")

        while (self.steps < self.maxsteps):

            
            self.evaluate()                           # evaluate samples  
            
            self.optimize()                           # estimate the gradient and move the centroid in the gradient direction

            self.stat = np.append(self.stat, [self.steps, self.bestfit, self.bestgfit, self.bfit, self.avgfit, self.avecenter])  # store performance across generations

            if ((time.time() - last_save_time) > (self.saveeach * 60)):
                self.savedata()                       # save data on files
                last_save_time = time.time()

            if self.normalizationdatacollected:
                self.policy.nn.updateNormalizationVectors()  # update the normalization vectors with the new data collected
                self.normalizationdatacollected = False

            print('Seed %d (%.1f%%) gen %d msteps %d bestfit %.2f bestgfit %.2f bestsam %.2f avg %.2f weightsize %.2f' %
                      (self.seed, self.steps / float(self.maxsteps) * 100, self.cgen, self.steps / 1000000, self.bestfit, self.bestgfit, self.bfit, self.avgfit, self.avecenter))

        self.savedata()                           # save data at the end of evolution
        np.save(self.filedir + "/S" + str(self.seed) + ".iev",self.ievReg)        
        self.ievReg = []
        # print simulation time
        end_time = time.time()
        print('Simulation time: %dm%ds ' % (divmod(end_time - start_time, 60)))

