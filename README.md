# Wordle Solver

This repository contains my submission, attempts and utilities for an assignment* to build a guesser for (a close cousin of) Wordle. The solver must guess a hidden five-letter word in up to six tries, receiving feedback on each guess in the form of correct letters, misplaced letters, and letters not in the solution.

**First assignment for the exam 20879 Language Technology, from the MSc in AI at Bocconi University, Spring 2025.*

#### DISCLAIMER
The **guesser_general.py** file has been so far tested only for the current configuration.

## Repository Contents

- **Assignment_1_Wordle.ipynb**  
  A Jupyter notebook describing the assignment requirements and some development notes.

- **game.py**  
  A script to run the Wordle game. You can play manually or run multiple rounds in automated mode.

- **wordle.py**  
  The Wordle game logic itself. It checks each guess, provides feedback, and tracks the number of attempts.

- **guesser_original.py**  
  The skeleton `Guesser` class initially provided by the professor. Contains only minimal logic.

- **guesser_submitted.py**  
  The final version I submitted for evaluation, optimized for speed on smaller test sets.

- **guesser_general.py**  
  A more feature-complete version with additional toggles (dummy guesses, second-guess distinct letters, frequency-based heuristics, etc.). Useful for experimenting with larger wordlists or advanced strategies. Closely inspired by a version kindly shared by fellow student [Giacomo Cirò](https://github.com/giacomo-ciro).

- **multiple.py**  
  A script to run multiple tests on random subsets of the dev word list. For each run, it picks a subset of words, writes them to `data/r_wordlist.yaml`, then invokes `game.py` for a specified number of rounds. Finally, it collects and prints aggregate statistics (accuracy, average guess length, and run time).

- **attempts/**  
  A folder containing intermediate or alternative attempts and experiments.

- **data/**  
  Contains supporting files such as word lists (`wordlist.yaml`) or frequency tables (`wordlist.tsv`).

## How to Run

1. Install dependencies (ensure you have `yaml`, `rich`, and `numpy`).
2. From the command line, navigate to this repository’s folder.
3. Run:
   ```bash
   python game.py
    ```
    This starts an interactive game where you can guess words manually. 
    
4. To run automated rounds (e.g., 500 rounds), use:
    ```bash
    python game.py --r 500 --p
    ```
    This will run 500 games automatically using the selected Guesser class. "--p" will print the results of each round.

Feel free to explore the different guesser implementations and switch them in game.py to compare performance and strategies.
