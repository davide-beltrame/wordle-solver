from random import choice
import yaml
from rich.console import Console
import math
from collections import Counter, defaultdict
from functools import lru_cache

USE_FREQUENCY = False  # Toggle frequency usage

class Guesser:
    def __init__(self, manual, use_frequency=USE_FREQUENCY):
        self.word_list = yaml.load(open('r_wordlist.yaml'), Loader=yaml.FullLoader)
        self._manual = manual 
        self.console = Console()
        self._tried = []  # List of words already guessed in the current game
        self.candidates = self.word_list.copy()  # All words are initially candidates
        self.last_guess = None
        self.use_frequency = use_frequency
        self.dummy_used = False
        self.feedback_cache = {}  # Cache for get_feedback results
        self.entropy_cache = {}   # Cache for entropy calculations
        
        # Load frequency data if needed
        if self.use_frequency:
            self.freq = {}
            with open('wordlist.tsv') as f:
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        word = parts[0]
                        try:
                            frequency = float(parts[1])
                        except ValueError:
                            frequency = 1.0
                        self.freq[word] = frequency
        else:
            self.freq = defaultdict(lambda: 1.0)

    def restart_game(self):
        self._tried = []
        self.candidates = self.word_list.copy()
        self.last_guess = None
        self.dummy_used = False
        # Keep caches across games to benefit from previous calculations

    # Using lru_cache to cache feedback calculations
    @lru_cache(maxsize=10000)
    def _cached_feedback(self, guess, answer):
        """Cached version of feedback calculation"""
        counts = Counter(answer)
        feedback = [''] * len(guess)
        
        # First pass: mark correct positions
        for i, letter in enumerate(guess):
            if letter == answer[i]:
                feedback[i] = letter
                counts[letter] -= 1
            else:
                feedback[i] = '+'
        
        # Second pass: mark letters in wrong positions
        for i, letter in enumerate(guess):
            if letter != answer[i] and letter in answer and counts[letter] > 0:
                feedback[i] = '-'
                counts[letter] -= 1
                
        return ''.join(feedback)

    def get_feedback(self, guess, answer):
        # Use the cache key since tuples are hashable
        cache_key = (guess, answer)
        if cache_key not in self.feedback_cache:
            self.feedback_cache[cache_key] = self._cached_feedback(guess, answer)
        return self.feedback_cache[cache_key]
    
    def try_dummy_guess(self, candidates_to_consider, result):
        if result.count('+') <= 1 and result.count('-') == 0 and not self.dummy_used and len(self._tried) < 5:
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
            self.dummy_used = True
            return dummy_letters
        return None

    def calculate_entropy(self, candidate, candidates_to_consider, total_weight):
        """Calculate entropy for a candidate word with careful preservation of original logic"""
        # Only cache if the candidate list is reasonably small
        should_cache = len(candidates_to_consider) < 1000
        
        if should_cache:
            # Use a more precise cache key that preserves order
            cache_key = (candidate, tuple(sorted(candidates_to_consider)))
            if cache_key in self.entropy_cache:
                return self.entropy_cache[cache_key]
        
        # Create pattern distribution exactly as in the original
        distribution = {}
        for answer in candidates_to_consider:
            pattern = self.get_feedback(candidate, answer)
            weight = self.freq.get(answer, 1) if self.use_frequency else 1
            distribution[pattern] = distribution.get(pattern, 0) + weight
        
        # Calculate entropy with high precision
        entropy = 0
        for count in distribution.values():
            p = count / total_weight
            entropy -= p * math.log2(p)
        
        # Cache the result if appropriate
        if should_cache:
            self.entropy_cache[cache_key] = entropy
        return entropy

    def get_letter_frequency_score(self, candidates_to_consider):
        """Pre-compute letter frequencies for all candidates"""
        letter_counts = {}
        if self.use_frequency:
            for word in candidates_to_consider:
                weight = self.freq.get(word, 1)
                for letter in set(word):
                    letter_counts[letter] = letter_counts.get(letter, 0) + weight
        else:
            letter_counts = Counter(''.join(candidates_to_consider))
        return letter_counts

    def get_guess(self, result):
        if self._manual == 'manual':
            return self.console.input('Your guess:\n')
        else:
            # Update candidates based on feedback from the previous guess
            if self.last_guess is not None:
                self.candidates = [word for word in self.candidates 
                                  if self.get_feedback(self.last_guess, word) == result]
            
            if not self.candidates:
                self.candidates = self.word_list.copy()
            
            candidates_to_consider = [w for w in self.candidates if w not in self._tried]
            if not candidates_to_consider:
                candidates_to_consider = self.candidates
            
            # If only one candidate remains, that's our guess
            if len(candidates_to_consider) == 1:
                guess = candidates_to_consider[0]
                self._tried.append(guess)
                self.console.print(guess)
                self.last_guess = guess
                return guess
            
            # First guess optimization - use a pre-determined optimal first word
            if self.last_guess is None:
                guess = "tales"  # Pre-computed optimal first word
                self._tried.append(guess)
                self.console.print(guess)
                self.last_guess = guess
                return guess
            
            # Try dummy guess is disabled for now
            dummy_guess = None
            if dummy_guess is not None:
                self._tried.append(dummy_guess)
                self.console.print("Dummy guess:", dummy_guess)
                self.last_guess = dummy_guess
                return dummy_guess
            
            print(len(candidates_to_consider))
            
            # For large candidate sets, use letter frequency heuristic (faster)
            if len(candidates_to_consider) > 50:
                letter_counts = self.get_letter_frequency_score(candidates_to_consider)
                
                best_score = -1
                best_guess = None
                
                # Process in batches for better cache locality
                batch_size = 50
                for i in range(0, len(candidates_to_consider), batch_size):
                    batch = candidates_to_consider[i:i+batch_size]
                    for word in batch:
                        # Count each letter only once per word
                        score = sum(letter_counts.get(c, 0) for c in set(word))
                        if score > best_score:
                            best_score = score
                            best_guess = word
                
                guess = best_guess
            else:
                # For smaller candidate sets, use full entropy calculation
                best_entropy = -1
                best_guess = None
                
                total_weight = (sum(self.freq.get(word, 1) for word in candidates_to_consider)
                               if self.use_frequency else len(candidates_to_consider))
                
                # Calculate entropy for each candidate
                for candidate in candidates_to_consider:
                    entropy = self.calculate_entropy(candidate, candidates_to_consider, total_weight)
                    if entropy > best_entropy:
                        best_entropy = entropy
                        best_guess = candidate
                
                guess = best_guess
            
            self._tried.append(guess)
            self.console.print(guess)
            self.last_guess = guess
            return guess