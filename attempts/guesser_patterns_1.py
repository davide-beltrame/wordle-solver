from random import choice
import yaml
from rich.console import Console
import math
from collections import Counter
from functools import lru_cache

# Use lru_cache to speed up repeated feedback calculations.
@lru_cache(maxsize=None)
def compute_feedback(guess, answer):
    """
    Compute the Wordle feedback string for a given guess and answer.
    Letters in the correct position appear as themselves.
    Letters in the word but in the wrong position are marked with '-',
    and letters not in the answer are marked with '+'.
    """
    counts = Counter(answer)
    feedback = [''] * len(guess)
    # First pass: mark correct positions
    for i, letter in enumerate(guess):
        if letter == answer[i]:
            feedback[i] = letter
            counts[letter] -= 1
        else:
            feedback[i] = '+'
    # Second pass: mark letters in the word but in wrong positions
    for i, letter in enumerate(guess):
        if letter != answer[i] and letter in answer and counts[letter] > 0:
            feedback[i] = '-'
            counts[letter] -= 1
    return ''.join(feedback)

class Guesser:
    def __init__(self, manual):
        self._manual = manual 
        self.console = Console()
        self._tried = []
        if self._manual == 'manual':
            # In manual mode, use the allowed guesses list (but no auto logic is needed)
            self.allowed_guesses = yaml.load(open('dev_wordlist.yaml'), Loader=yaml.FullLoader)
            self.possible_answers = None
            self.best_first_guess = None
        else:
            # In auto mode, load both the training word list (allowed guesses) and the dev set (possible answers)
            self.allowed_guesses = yaml.load(open('r_wordlist.yaml'), Loader=yaml.FullLoader)
            self.possible_answers = yaml.load(open('r_wordlist.yaml'), Loader=yaml.FullLoader)
            # Candidates are initialized as all possible answers.
            self.candidates = self.possible_answers.copy()
            self.last_guess = None
            # Precompute the best first guess over all allowed guesses
            self.best_first_guess = self.compute_best_first_guess()

    def restart_game(self):
        self._tried = []
        if self._manual != 'manual':
            self.candidates = self.possible_answers.copy()
            self.last_guess = None

    def compute_best_first_guess(self):
        """
        Compute the allowed guess (even if not a possible answer) that maximizes
        the expected information (entropy) over all possible answers.
        """
        best_entropy = -1
        best_guess = None
        total_answers = len(self.possible_answers)
        for guess in self.allowed_guesses:
            distribution = {}
            for answer in self.possible_answers:
                pattern = compute_feedback(guess, answer)
                distribution[pattern] = distribution.get(pattern, 0) + 1
            # Compute the entropy for this guess.
            entropy = 0
            for count in distribution.values():
                p = count / total_answers
                entropy -= p * math.log2(p)
            if entropy > best_entropy:
                best_entropy = entropy
                best_guess = guess
        return best_guess

    def get_guess(self, result):
        if self._manual == 'manual':
            return self.console.input('Your guess:\n')
        else:
            # For the first guess, use the precomputed best first guess.
            if self.last_guess is None:
                guess = self.best_first_guess
                self._tried.append(guess)
                self.console.print(guess)
                self.last_guess = guess
                return guess
            else:
                # Update candidates based on feedback from the previous guess.
                self.candidates = [word for word in self.candidates 
                                   if compute_feedback(self.last_guess, word) == result]
                if not self.candidates:
                    self.candidates = self.possible_answers.copy()
                # Only consider words that have not already been tried.
                candidates_to_consider = [w for w in self.candidates if w not in self._tried]
                if not candidates_to_consider:
                    candidates_to_consider = self.candidates
                # If only one candidate remains, choose it.
                if len(candidates_to_consider) == 1:
                    guess = candidates_to_consider[0]
                    self._tried.append(guess)
                    self.console.print(guess)
                    self.last_guess = guess
                    return guess
                # Otherwise, select the candidate with the maximum expected entropy.
                best_entropy = -1
                best_guess = None
                total_weight = len(candidates_to_consider)
                for candidate in candidates_to_consider:
                    distribution = {}
                    for answer in candidates_to_consider:
                        pattern = compute_feedback(candidate, answer)
                        distribution[pattern] = distribution.get(pattern, 0) + 1
                    entropy = 0
                    for count in distribution.values():
                        p = count / total_weight
                        entropy -= p * math.log2(p)
                    if entropy > best_entropy:
                        best_entropy = entropy
                        best_guess = candidate
                guess = best_guess
                self._tried.append(guess)
                self.console.print(guess)
                self.last_guess = guess
                return guess
