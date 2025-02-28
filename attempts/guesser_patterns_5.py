from random import choice
import yaml
from rich.console import Console
import math
from collections import Counter, defaultdict
from functools import lru_cache
from itertools import product

class Guesser:
    def __init__(self, manual):
        self.word_list = yaml.load(open('dev2.yaml'), Loader=yaml.FullLoader)
        self._manual = manual 
        self.console = Console()
        self._tried = []
        self.candidates = self.word_list.copy()  # All words are initially candidates
        self.last_guess = None
        self.best_first_word = self.best_first_guess()
        
    def restart_game(self):
        self._tried = []
        self.candidates = self.word_list.copy()
        self.last_guess = None

    @lru_cache(maxsize=1000000)
    def get_feedback(self, guess, answer):
        # Produces the feedback string just like in Wordle
        counts = Counter(answer)
        feedback = [''] * len(guess)
        for i, letter in enumerate(guess):
            if letter == answer[i]:
                feedback[i] = letter
                counts[letter] -= 1
            else:
                feedback[i] = '+'
        for i, letter in enumerate(guess):
            if feedback[i] == '+' and letter in answer and counts[letter] > 0:
                feedback[i] = '-'
                counts[letter] -= 1
        return ''.join(feedback)
    
    @lru_cache(maxsize=10000)
    def calculate_pattern_distribution(self, guess, candidates_tuple):
        """Calculate pattern distribution for a given guess and candidate set."""
        distribution = {}
        for answer in candidates_tuple:
            pattern = self.get_feedback(guess, answer)
            distribution[pattern] = distribution.get(pattern, 0) + 1
        return distribution
    
    def calculate_entropy(self, guess, candidates):
        """Calculate entropy for a given guess against the candidate set."""
        # Avoid converting repeatedly if already a tuple.
        if not isinstance(candidates, tuple):
            candidates = tuple(candidates)
        total_weight = len(candidates)
        distribution = self.calculate_pattern_distribution(guess, candidates)
        entropy = 0
        for count in distribution.values():
            p = count / total_weight
            entropy -= p * math.log2(p)
        return entropy
    
    def best_first_guess(self):
        """Calculate the optimal first word (which does not need to be a valid candidate) based on entropy,
        but restrict the candidate pool to words built from the most frequent letters in each position."""
        pos_counters = [defaultdict(int) for _ in range(5)]
        for word in self.candidates:
            for i, letter in enumerate(word):
                pos_counters[i][letter] += 1
        top_letters = []
        for counter in pos_counters:
            counter_obj = Counter(counter)
            most_common = counter_obj.most_common(3)
            top_letters.append([letter for letter, _ in most_common])
        potential_first_words = {''.join(letters) for letters in product(*top_letters)}
        known_good = {"saren", "ranes", "saret", "tares", "earis",
                    "saner", "lares", "aires", "raise", "sarel"}
        potential_first_words |= known_good
        best_word = None
        best_entropy = -1
        for word in potential_first_words:
            entropy = self.calculate_entropy(word, self.candidates)
            if entropy > best_entropy:
                best_entropy = entropy
                best_word = word
        return best_word
    
    def get_guess(self, result):
        if self._manual == 'manual':
            return self.console.input('Your guess:\n')
        else:
            # Update candidates based on feedback from the previous guess.
            if self.last_guess is not None:
                self.candidates = [word for word in self.candidates 
                                   if self.get_feedback(self.last_guess, word) == result]
            
            # For the first guess, return the precomputed best first word.
            if not self._tried:
                guess = self.best_first_word
                self._tried.append(guess)
                self.console.print(guess)
                self.last_guess = guess
                return guess
            
            # If only one candidate remains, return it.
            if len(self.candidates) == 1:
                guess = self.candidates[0]
                self._tried.append(guess)
                self.console.print(guess)
                self.last_guess = guess
                return guess
            
            # If no candidates remain (should not happen), reset the candidate list.
            if not self.candidates:
                self.candidates = [w for w in self.word_list if w not in self._tried]
            
            # For subsequent guesses, select the candidate with the highest entropy.
            candidates_to_consider = [w for w in self.candidates if w not in self._tried]
            if not candidates_to_consider:
                candidates_to_consider = self.candidates
            
            # Precompute the tuple version of candidates for efficiency.
            candidates_tuple = tuple(self.candidates)
            best_guess = max(candidates_to_consider, 
                             key=lambda candidate: self.calculate_entropy(candidate, candidates_tuple))
            guess = best_guess
            self._tried.append(guess)
            self.console.print(guess)
            self.last_guess = guess
            return guess