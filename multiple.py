import sys
import yaml
import subprocess
import re

import numpy as np
import os

print(os.listdir())

if len(sys.argv) > 2:

    N_INIT = (sys.argv[1])
    N_WORDS = sys.argv[2]

else:
    N_INIT = input('N_INIT: ')
    N_WORDS = input('N_WORDS: ')

N_INIT, N_WORDS, N_GAMES = int(N_INIT), int(N_WORDS), 500

#input('Press enter to start: ')

_word_list = yaml.load(open('dev_wordlist.yaml'), Loader=yaml.FullLoader)

stats = np.zeros(shape=(N_INIT, 3))

for i in range(N_INIT):
   
    print(f"Run {i+1}: ")
    word_list = np.random.choice(
        _word_list,
        size = N_WORDS,
        replace=False
        ).tolist()
   
    with open('r_wordlist.yaml', 'w') as f:
        yaml.dump(word_list, f)

    # Run the game
    out = subprocess.run(["python3", "game.py", "--r", str(N_GAMES)], capture_output=True)

    accuracy, avg_length, time = re.sub(r'[a-z\\\'%]', '', str(out.stdout)).split(',')
    accuracy, avg_length, time = float(accuracy), float(avg_length), float(time)
    stats[i, :] = [accuracy, avg_length, time]

    print(f"{accuracy:.2f}%,{avg_length:.4f},{time:.2f}")

print()
print(f"Completed {N_INIT} runs.\n\nAverage metrics: ")
print(f"Accuracy = {np.mean(stats[:, 0]):.2f}%")
print(f"Length = {np.mean(stats[:, 1]):.4f}")
print(f"Time = {np.mean(stats[:, 2]):.4f}")
