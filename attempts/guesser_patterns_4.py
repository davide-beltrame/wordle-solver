from random import choice, sample
import yaml
from rich.console import Console
import math
from collections import Counter
from functools import lru_cache

class Guesser:
    def __init__(self, manual):
        self.word_list = yaml.load(open('dev_wordlist.yaml'), Loader=yaml.FullLoader)
        self._manual = manual 
        self.console = Console()
        self._tried = []  # Words already guessed this game
        self.candidates = self.word_list.copy()  # All words are initially candidates
        self.last_guess = None

        # Hard-code known excellent first words that have been empirically verified
        # Including "saren" which was identified in previous successful versions
        self.excellent_openers = ["saren", "soare", "roate", "raise", "slate", "crate", "adieu", "stare", "slant", "tares"]
        
        # Pre-compute best first word
        self.best_first_word = self._calculate_best_first_word()
        
    def restart_game(self):
        self._tried = []
        self.candidates = self.word_list.copy()
        self.last_guess = None
        
    @lru_cache(maxsize=None)
    def get_feedback(self, guess, answer):
        """Calculate feedback pattern with optimized implementation"""
        # Fast path for exact match
        if guess == answer:
            return guess
            
        counts = Counter(answer)
        feedback = ['+'] * len(guess)  # Initialize all positions as not in word
        
        # First pass: mark correct positions
        for i, letter in enumerate(guess):
            if letter == answer[i]:
                feedback[i] = letter
                counts[letter] -= 1
                
        # Second pass: mark letters that are present but misplaced
        for i, letter in enumerate(guess):
            if feedback[i] == '+' and letter in answer and counts[letter] > 0:
                feedback[i] = '-'
                counts[letter] -= 1
                
        return ''.join(feedback)
    
    @lru_cache(maxsize=100000)
    def _calculate_pattern_distribution(self, guess, candidates_tuple):
        """Calculate pattern distribution with aggressive caching"""
        distribution = {}
        for answer in candidates_tuple:
            pattern = self.get_feedback(guess, answer)
            distribution[pattern] = distribution.get(pattern, 0) + 1
        return distribution
    
    def _calculate_entropy(self, guess, candidates_tuple):
        """Calculate entropy with optimized implementation"""
        total_candidates = len(candidates_tuple)
        distribution = self._calculate_pattern_distribution(guess, candidates_tuple)
        
        # Entropy calculation
        entropy = 0
        for count in distribution.values():
            p = count / total_candidates
            entropy -= p * math.log2(p)
            
        return entropy
    
    def _generate_high_value_words(self):
        """Generate words specifically designed to maximize information gain"""
        # Focus on letters that appear most frequently in the wordlist
        letter_freq = Counter()
        for word in self.word_list:
            # Count unique letters in each word
            letter_freq.update(set(word))
        
        # Get top letters by frequency
        top_letters = [letter for letter, _ in letter_freq.most_common(15)]
        vowels = [v for v in 'aeiou' if v in top_letters]
        consonants = [c for c in top_letters if c not in 'aeiou']
        
        # Certain patterns work better for first guesses
        # Ensure unique letters for maximum information
        high_value_words = []
        
        # Generate words with strategic letter placements
        for v1 in vowels[:3]:
            for v2 in vowels[:3]:
                if v1 == v2:
                    continue
                for c1 in consonants[:5]:
                    for c2 in consonants[:5]:
                        if c1 == c2:
                            continue
                        for c3 in consonants[:5]:
                            if c3 in [c1, c2]:
                                continue
                            # Create words with common patterns (CVCVC, CVCCV)
                            word1 = c1 + v1 + c2 + v2 + c3  # CVCVC
                            word2 = c1 + v1 + c2 + c3 + v2  # CVCCV
                            
                            high_value_words.append(word1)
                            high_value_words.append(word2)
        
        # Add our known excellent openers
        high_value_words.extend(self.excellent_openers)
        
        # Add a sample from the wordlist
        high_value_words.extend(sample(self.word_list, min(200, len(self.word_list))))
        
        return high_value_words
    
    def _calculate_best_first_word(self):
        """Calculate optimal first word with improved algorithm"""
        # Use the full wordlist as the evaluation set for maximum accuracy
        answers_tuple = tuple(self.word_list)
        
        # First check if "saren" is better than other known good openers
        best_entropy = 0
        best_word = "saren"  # Start with known good opener
        
        # Check entropy for known good openers first
        for word in self.excellent_openers:
            entropy = self._calculate_entropy(word, answers_tuple)
            if entropy > best_entropy:
                best_entropy = entropy
                best_word = word
                
        # Generate additional candidate words
        potential_words = self._generate_high_value_words()
        
        # Evaluate a reasonable subset for efficiency
        evaluation_candidates = sample(potential_words, min(300, len(potential_words)))
        
        # Find the best word by entropy
        for word in evaluation_candidates:
            entropy = self._calculate_entropy(word, answers_tuple)
            
            # Prefer words with unique letters (better information gain)
            unique_letter_count = len(set(word))
            if unique_letter_count == 5:  # All letters are unique
                entropy += 0.01  # Small bonus
                
            if entropy > best_entropy:
                best_entropy = entropy
                best_word = word
        
        return best_word
    
    def get_guess(self, result):
        if self._manual == 'manual':
            return self.console.input('Your guess:\n')
        
        # First guess - use pre-computed best first word
        if not self._tried:
            guess = self.best_first_word
            self._tried.append(guess)
            self.console.print(guess)
            self.last_guess = guess
            return guess
            
        # Update candidates based on feedback from the previous guess
        if self.last_guess is not None:
            new_candidates = []
            for word in self.candidates:
                if self.get_feedback(self.last_guess, word) == result:
                    new_candidates.append(word)
            self.candidates = new_candidates
            
        # If only one candidate remains, that must be the answer
        if len(self.candidates) == 1:
            guess = self.candidates[0]
            self._tried.append(guess)
            self.console.print(guess)
            self.last_guess = guess
            return guess
            
        # If no candidates remain (shouldn't happen), reset
        if not self.candidates:
            self.candidates = [w for w in self.word_list if w not in self._tried]
            
        # Only consider untried candidates
        candidates_to_consider = [w for w in self.candidates if w not in self._tried]
        if not candidates_to_consider:
            candidates_to_consider = self.candidates
            
        # Convert to tuple for caching
        candidates_tuple = tuple(self.candidates)
        
        # Find the candidate with the highest entropy
        best_entropy = -1
        best_guess = None
        
        for candidate in candidates_to_consider:
            entropy = self._calculate_entropy(candidate, candidates_tuple)
            if entropy > best_entropy:
                best_entropy = entropy
                best_guess = candidate
        
        guess = best_guess
        self._tried.append(guess)
        self.console.print(guess)
        self.last_guess = guess
        return guess