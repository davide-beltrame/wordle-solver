from random import choice
import yaml
from rich.console import Console
import math
from collections import Counter, defaultdict
from itertools import product, permutations
from functools import lru_cache

# Toggles
USE_FREQUENCY = False        
DEBUG = False               
TWO_GUESS_DISTINCT = True     # use a distinct-letters (dummy) guess for the second guess
DUMMY_GUESS_TOGGLE = True     # enable the dummy guess feature
DUMMY_PLUS_COUNTS = [1, 2]      # dummy guess activates if result.count('+') is in this list.
DUMMY_GUESS_ONE_PER_CASE = True  # allow one dummy guess per distinct feedback.

class Guesser:
    """
        Welcome to Davide's guesser optimised for correctness and performance on larger wordlists!
    """
    def __init__(self, manual, use_frequency=USE_FREQUENCY):
        self.word_list = yaml.load(open('data/wordlist.yaml'), Loader=yaml.FullLoader)
        self._manual = manual 
        self.console = Console()
        self._tried = []  
        self.candidates = self.word_list.copy() 
        self.last_guess = None
        self.use_frequency = use_frequency
        self.best_first_word = None  
        self.used_dummy = set() 
        if self.use_frequency:
            self.freq = {}
            with open('data/wordlist.tsv') as f:
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        word = parts[0]
                        try:
                            frequency = float(parts[1])
                        except ValueError:
                            frequency = 1.0
                        self.freq[word] = frequency

    def restart_game(self):
        self._tried = []
        self.candidates = self.word_list.copy()
        self.last_guess = None
        self.used_dummy = set()

    @lru_cache(maxsize=None)
    def get_feedback(self, guess, answer):
        counts = Counter(answer)
        feedback = [''] * len(guess)
        for i, letter in enumerate(guess):
            if letter == answer[i]:
                feedback[i] = letter
                counts[letter] -= 1
            else:
                feedback[i] = '+'
        for i, letter in enumerate(guess):
            if letter != answer[i] and letter in answer and counts[letter] > 0:
                feedback[i] = '-'
                counts[letter] -= 1
        return ''.join(feedback)
    
    @lru_cache(maxsize=None)
    def pattern_distribution(self, guess, candidates_tuple):
        distribution = {}
        for answer in candidates_tuple:
            pattern = self.get_feedback(guess, answer)
            if self.use_frequency:
                weight = self.freq.get(answer, 1)
                distribution[pattern] = distribution.get(pattern, 0) + weight
            else:
                distribution[pattern] = distribution.get(pattern, 0) + 1
        return distribution
    
    def entropy(self, guess, candidates):
        if not isinstance(candidates, tuple):
            candidates = tuple(candidates)
        distribution = self.pattern_distribution(guess, candidates)
        if self.use_frequency:
            total_weight = sum(self.freq.get(word, 1) for word in candidates)
        else:
            total_weight = len(candidates)
        ent = 0
        for count in distribution.values():
            p = count / total_weight
            ent -= p * math.log2(p)
        return ent
    
    def best_first_guess(self):
        """Compute the best starting guess (using entropy over candidates)
        but restrict the pool to words built from the most frequent letters per position."""
        if self.best_first_word:
            return self.best_first_word
            
        pos_counters = [defaultdict(int) for _ in range(5)]
        for word in self.candidates:
            for i, letter in enumerate(word):
                pos_counters[i][letter] += 1
        candidates_sample = tuple(self.candidates)
        top_letters = []
        for i, counter in enumerate(pos_counters):
            top_for_pos = sorted(counter.items(), key=lambda x: x[1], reverse=True)[:2]
            top_letters.append([letter for letter, _ in top_for_pos])
        known_good = {"saren", "ranes", "saret", "tares", "earis",
                      "saner", "lares", "aires", "raise", "sarel",
                      "sarie", "tales", "crane", "stale"}
        limit = 100
        potential_words = set(known_good)
        combos = product(*top_letters)
        for _ in range(limit - len(potential_words)):
            try:
                word = ''.join(next(combos))
                potential_words.add(word)
            except StopIteration:
                break
        best_word = None
        best_ent = -1
        for word in potential_words:
            ent = self.entropy(word, candidates_sample)
            if ent > best_ent:
                best_ent = ent
                best_word = word
        self.best_first_word = best_word
        return best_word

    def try_dummy_guess(self, candidates_to_consider, result):
        if not DUMMY_GUESS_TOGGLE:
            return None
        
        plus_count = result.count('+')
        if plus_count in DUMMY_PLUS_COUNTS and result.count('-') == 0 and len(self._tried) < 5:
            if DUMMY_GUESS_ONE_PER_CASE:
                if result in self.used_dummy:
                    return None
                self.used_dummy.add(result)
            pos = result.index('+')
            letters = [word[pos] for word in candidates_to_consider]
            distinct_letters = set(letters)
            if len(distinct_letters) < 3:
                return None
            letter_freq = Counter(letters)
            dummy_letters = ''.join([letter for letter, _ in letter_freq.most_common()])
            if len(dummy_letters) < 5:
                dummy_letters += 'a' * (5 - len(dummy_letters))
            elif len(dummy_letters) > 5:
                dummy_letters = dummy_letters[:5]
            return dummy_letters
        return None

    def distinct_second_guess(self, first_feedback):
        """For the second guess, return a 5-letter guess with distinct letters (not necessarily a word)
        that maximizes entropy over the candidate set, while excluding letters already confirmed by the first guess.
        The 'first_feedback' parameter is the feedback from the first guess."""
        if not self._tried:
            return None
        first_guess = self._tried[0]
        known_letters = {letter for letter, mark in zip(first_guess, first_feedback) if mark != '+'}
        overall_counter = Counter(''.join(self.candidates))
        filtered_counter = {letter: count for letter, count in overall_counter.items() if letter not in known_letters}
        top_n = 5  # use only the top 5 letters to limit permutations.
        top_letters = [letter for letter, _ in sorted(filtered_counter.items(), key=lambda x: x[1], reverse=True)[:top_n]]
        if len(top_letters) < 5:
            return None 
        distinct_candidates = {''.join(p) for p in permutations(top_letters, 5)}
        candidates_tuple = tuple(self.candidates)
        best_guess = None
        best_e = -1
        for candidate in distinct_candidates:
            e = self.entropy(candidate, candidates_tuple)
            if e > best_e:
                best_e = e
                best_guess = candidate
        return best_guess

    def get_guess(self, result):
        if self._manual == 'manual':
            guess = self.console.input('Your guess:\n')
            if guess is None:
                guess = ""
            return guess
        else:
            if self.last_guess is not None:
                self.candidates = [word for word in self.candidates 
                                   if self.get_feedback(self.last_guess, word) == result]
            if not self.candidates:
                self.candidates = self.word_list.copy()
            if not self._tried:
                if not self.best_first_word:
                    self.best_first_word = self.best_first_guess()
                guess = self.best_first_word
                if guess is None:
                    guess = choice(self.candidates)
                self._tried.append(guess)
                self.console.print(guess)
                self.last_guess = guess
                return guess
            if len(self._tried) == 1 and TWO_GUESS_DISTINCT:
                guess = self.distinct_second_guess(result)
                if guess is None:
                    candidates_tuple = tuple(self.candidates)
                    best_e = -1
                    best_guess = None
                    candidates_to_consider = [w for w in self.candidates if w not in self._tried]
                    for candidate in candidates_to_consider:
                        e = self.entropy(candidate, candidates_tuple)
                        if e > best_e:
                            best_e = e
                            best_guess = candidate
                    guess = best_guess
                self._tried.append(guess)
                self.console.print("Distinct second guess:", guess)
                self.last_guess = guess
                return guess
            if len(self.candidates) == 1:
                guess = self.candidates[0]
                self._tried.append(guess)
                self.console.print(guess)
                self.last_guess = guess
                return guess

            candidates_to_consider = [w for w in self.candidates if w not in self._tried]
            if not candidates_to_consider:
                candidates_to_consider = self.candidates
            dummy_guess = self.try_dummy_guess(candidates_to_consider, result)
            if dummy_guess is not None:
                guess = dummy_guess
                self._tried.append(guess)
                self.console.print("Dummy guess:", guess)
                self.last_guess = guess
                return guess
    
            if len(candidates_to_consider) > 100:
                if self.use_frequency:
                    letter_counts = {}
                    for word in candidates_to_consider:
                        weight = self.freq.get(word, 1)
                        for letter in set(word):
                            letter_counts[letter] = letter_counts.get(letter, 0) + weight
                else:
                    letter_counts = Counter(''.join(candidates_to_consider))
                best_score = -1
                best_guess = None
                for word in candidates_to_consider:
                    score = sum(letter_counts.get(c, 0) for c in set(word))
                    if score > best_score:
                        best_score = score
                        best_guess = word
                guess = best_guess
            else:
                candidates_tuple = tuple(self.candidates)
                best_e = -1
                best_guess = None
                for candidate in candidates_to_consider:
                    e = self.entropy(candidate, candidates_tuple)
                    if e > best_e:
                        best_e = e
                        best_guess = candidate
                guess = best_guess
                
            if guess is None:
                guess = choice(self.candidates)
            self._tried.append(guess)
            self.console.print(guess)
            self.last_guess = guess
        return guess
