from random import choice
import yaml
from rich.console import Console
import math
from collections import Counter
from functools import lru_cache

class Guesser:
    def __init__(self, manual):
        self.word_list = yaml.load(open('r_wordlist.yaml'), Loader=yaml.FullLoader)
        self._manual = manual 
        self.console = Console()
        self._tried = []  # List of words already guessed in the current game
        self.candidates = self.word_list.copy()  # All words are initially candidates
        self.last_guess = None
        self.best_first_word = self.calculate_best_first_word()
        
    def restart_game(self):
        self._tried = []
        self.candidates = self.word_list.copy()
        self.last_guess = None

    @lru_cache(maxsize=1000000)
    def get_feedback(self, guess, answer):
        """Calculate feedback pattern using memoization"""
        counts = Counter(answer)
        feedback = [''] * len(guess)
        
        # First pass: mark correct positions
        for i, letter in enumerate(guess):
            if letter == answer[i]:
                feedback[i] = letter
                counts[letter] -= 1
            else:
                feedback[i] = '+'
                
        # Second pass: mark incorrect positions
        for i, letter in enumerate(guess):
            if feedback[i] == '+' and letter in answer and counts[letter] > 0:
                feedback[i] = '-'
                counts[letter] -= 1
                
        return ''.join(feedback)
    
    @lru_cache(maxsize=10000)
    def calculate_pattern_distribution(self, guess, candidates_tuple):
        """Calculate pattern distribution for a given guess and candidate set"""
        candidates = list(candidates_tuple)
        distribution = {}
        for answer in candidates:
            pattern = self.get_feedback(guess, answer)
            distribution[pattern] = distribution.get(pattern, 0) + 1
        return distribution
    
    def calculate_entropy(self, guess, candidates):
        """Calculate entropy for a given guess"""
        total_weight = len(candidates)
        
        # Convert list to tuple for caching
        candidates_tuple = tuple(candidates)
        distribution = self.calculate_pattern_distribution(guess, candidates_tuple)
        
        entropy = 0
        for count in distribution.values():
            p = count / total_weight
            entropy -= p * math.log2(p)
        return entropy
    
    def calculate_best_first_word(self):
        """Calculate the optimal first word based on entropy across all possible answers"""
        
        # Create all possible 5-letter strings with common letters
        candidates = self.word_list.copy()
        
        # Let's focus on common letters in English
        letters = 'etaoinshrdlucmfwypvbgkjqxz'
        
        # Generate a list of potential first words that cover common letters
        # Include both valid words and strategic combinations of letters
        potential_first_words = []
        
        # Add known good starting words
        potential_first_words.extend(['soare', 'roate', 'raise', 'raile', 'slate', 'crate', 'irate', 'trace'])
        
        # Add some words from the wordlist
        sample_size = min(500, len(candidates))
        potential_first_words.extend(choice(candidates) for _ in range(sample_size))
        
        # For better coverage, also consider some non-dictionary words that maximize letter diversity
        vowels = 'aeiou'
        common_consonants = 'rstlnc'
        
        # Generate some synthetic words that have good letter combinations
        for v1 in vowels:
            for v2 in vowels:
                if v1 != v2:
                    for c1 in common_consonants:
                        for c2 in common_consonants:
                            if c1 != c2:
                                for c3 in common_consonants:
                                    if c3 not in [c1, c2]:
                                        word = c1 + v1 + c2 + v2 + c3
                                        potential_first_words.append(word)
        
        # Limit the synthetic words to a reasonable number
        potential_first_words = potential_first_words[:1000]
        
        # Calculate entropy for each potential first word
        best_word = None
        best_entropy = -1
        
        # Consider only a subset of all candidates for performance
        candidate_sample = candidates
        
        for word in potential_first_words:
            entropy = self.calculate_entropy(word, candidate_sample)
            if entropy > best_entropy:
                best_entropy = entropy
                best_word = word
        
        return best_word
    
    def get_guess(self, result):
        if self._manual == 'manual':
            return self.console.input('Your guess:\n')
        else:
            # Use feedback from previous guess to update candidates
            if self.last_guess is not None:
                new_candidates = []
                for word in self.candidates:
                    if self.get_feedback(self.last_guess, word) == result:
                        new_candidates.append(word)
                self.candidates = new_candidates
            
            # First guess optimization
            if not self._tried:
                guess = self.best_first_word
                self._tried.append(guess)
                self.console.print(guess)
                self.last_guess = guess
                return guess
            
            # If only one candidate left, that must be the answer
            if len(self.candidates) == 1:
                guess = self.candidates[0]
                self._tried.append(guess)
                self.console.print(guess)
                self.last_guess = guess
                return guess
            
            # If no candidates left (which shouldn't happen), reset
            if not self.candidates:
                self.candidates = [w for w in self.word_list if w not in self._tried]
            
            # For subsequent guesses, find the word that maximizes information gain
            best_entropy = -1
            best_guess = None
            
            # Consider both actual words and already tried words for efficiency
            candidates_to_consider = [w for w in self.candidates if w not in self._tried]
            
            # If no valid candidates left, use any word
            if not candidates_to_consider:
                candidates_to_consider = self.candidates
            
            # Calculate entropy for each candidate and choose the best one
            for candidate in candidates_to_consider:
                entropy = self.calculate_entropy(candidate, self.candidates)
                if entropy > best_entropy:
                    best_entropy = entropy
                    best_guess = candidate
            
            # Use the best guess found
            guess = best_guess
            self._tried.append(guess)
            self.console.print(guess)
            self.last_guess = guess
            
            return guess