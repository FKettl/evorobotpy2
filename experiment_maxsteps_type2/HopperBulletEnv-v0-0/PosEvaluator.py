import os


for x in range(2,10):
    os.system(f"python3.7 ../../evorobotpy2/bin/es.py -f HopperBulletEnv-v0-0.ini -g  bestgS{x}.npy -p")