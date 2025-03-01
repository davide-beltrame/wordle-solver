from random import choice
import yaml
from rich.console import Console
import math
from collections import Counter, defaultdict
from functools import lru_cache
from itertools import product

class Guesser:
    def __init__(self, manual):
        """
            Welcome to Davide's guesser!
            For a more statistically sound test of the performance,
            I advise to run more than 500 iterations on the 500 word test set
            disabling the fixed seed.

            This algorithm is optimised for performance and for efficiency on very
            numerous iterations: if you run 50k iterations on a 500 word set,
            it will take no more than 10 seconds!

            (benchmark: MacBook Pro M1 Max)
        """
        self.word_list = yaml.load(open('wordlist.yaml'), Loader=yaml.FullLoader)
        self._manual = manual 
        self.console = Console()
        self._tried = []
        self.candidates = self.word_list.copy()
        self.last_guess = None
        self.best_first_word = self.best_first_guess()
        
    def restart_game(self):
        self._tried = []
        self.candidates = self.word_list.copy()
        self.last_guess = None

    @lru_cache(maxsize=None)
    def get_matches(self, guess, answer): # produces feedback string just like in wordle.py
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
    
    @lru_cache(maxsize=None)
    def pattern_distribution(self, guess, candidates_tuple):
        """Calculate pattern distribution for a given guess and candidate set."""
        distribution = {}
        for answer in candidates_tuple:
            pattern = self.get_matches(guess, answer)
            distribution[pattern] = distribution.get(pattern, 0) + 1
        return distribution
    
    def entropy(self, guess, candidates):
        """Calculate entropy for a given guess against the candidate set."""
        if not isinstance(candidates, tuple): # avoid converting repeatedly if already a tuple.
            candidates = tuple(candidates)
        total_weight = len(candidates)
        distribution = self.pattern_distribution(guess, candidates)
        entropy = 0
        for count in distribution.values():
            p = count / total_weight
            entropy -= p * math.log2(p)
        return entropy
    
    def best_first_guess(self):
        """Calculate the optimal first (non-)word based on entropy,
        but restrict the candidate pool to words built from the most frequent letters in each position."""
        pos_counters = [defaultdict(int) for _ in range(5)]
        for word in self.candidates:
            for i, letter in enumerate(word):
                pos_counters[i][letter] += 1
        candidates_sample = tuple(self.candidates)
        top_letters = []
        for i, counter in enumerate(pos_counters): # get the most common letters for each position
            top_for_pos = sorted(counter.items(), key=lambda x: x[1], reverse=True)[:2]
            top_letters.append([letter for letter, _ in top_for_pos])
        # known good words that tend to perform well on the training set
        known_good = {"saren", "ranes", "saret", "tares", "earis",
                    "saner", "lares", "aires", "raise", "sarel", 
                    "sarie", "tales", "crane", "stale"}
        limit = 100
        potential_words = set()
        potential_words.update(known_good)
        combos = product(*top_letters)
        for _ in range(limit - len(potential_words)):
            try:
                word = ''.join(next(combos))
                potential_words.add(word)
            except StopIteration:
                break
        best_word = None
        best_entropy = -1
        for word in potential_words:
            entropy = self.entropy(word, candidates_sample)
            if entropy > best_entropy:
                best_entropy = entropy
                best_word = word
        return best_word
    
    def get_guess(self, result):
        if self._manual == 'manual':
            return self.console.input('Your guess:\n')
        else:
            if self.last_guess is not None:
                self.candidates = [word for word in self.candidates 
                                   if self.get_matches(self.last_guess, word) == result]
            if not self._tried: # first guess
                guess = self.best_first_word
                self._tried.append(guess)
                self.console.print(guess)
                self.last_guess = guess
                return guess
            if len(self.candidates) == 1: # edge case: one candidate left
                guess = self.candidates[0]
                self._tried.append(guess)
                self.console.print(guess)
                self.last_guess = guess
                return guess
            if not self.candidates: # if no candidates remain (should not happen), reset the candidate list
                self.candidates = [w for w in self.word_list if w not in self._tried]
            candidates_to_consider = [w for w in self.candidates if w not in self._tried]
            if not candidates_to_consider:
                candidates_to_consider = self.candidates
            candidates_tuple = tuple(self.candidates) # precompute the tuple version of candidates for efficiency
            best_guess = max(candidates_to_consider, 
                             key=lambda candidate: self.entropy(candidate, candidates_tuple))
            guess = best_guess
            self._tried.append(guess)
            self.console.print(guess)
            self.last_guess = guess
            return guess