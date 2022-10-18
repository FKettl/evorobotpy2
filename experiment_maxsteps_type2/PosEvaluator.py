import os

for x in range(5,10):
    os.system(f"python3.7 ../../evorobotpy2/bin/es.py -f AntBulletEnv-v0-1.ini -g  bestgS{x}.npy -p")
