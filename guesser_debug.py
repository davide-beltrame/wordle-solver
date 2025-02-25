from random import choice
import yaml
from rich.console import Console
import math
from collections import Counter

class Guesser:
    def __init__(self, manual, use_frequency=True):
        self.word_list = yaml.load(open('dev_wordlist.yaml'), Loader=yaml.FullLoader)
        self._manual = manual 
        self.console = Console()
        self._tried = []  # List of words already guessed in the current game
        self.candidates = self.word_list.copy()  # All words are initially candidates
        self.last_guess = None
        
        # Always use frequency data for better guesses
        self.freq = {}
        try:
            with open('dev_wordlist.tsv') as f:
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        word = parts[0]
                        try:
                            frequency = float(parts[1])
                        except ValueError:
                            frequency = 1.0
                        self.freq[word] = frequency
        except FileNotFoundError:
            # If frequency file is not found, use uniform weights
            self.freq = {word: 1.0 for word in self.word_list}
            
        # Precompute optimal first guesses (based on entropy analysis)
        self.optimal_starters = ["slate", "crane", "trace", "roate"]

    def restart_game(self):
        self._tried = []
        self.candidates = self.word_list.copy()
        self.last_guess = None

    def get_feedback(self, guess, answer):
        counts = Counter(answer)
        feedback = [''] * len(guess)
        # First pass: assign correct-position letters
        for i, letter in enumerate(guess):
            if letter == answer[i]:
                feedback[i] = letter
                counts[letter] -= 1
            else:
                feedback[i] = '+'
        # Second pass: assign '-' for misplaced letters
        for i, letter in enumerate(guess):
            if letter != answer[i] and letter in answer and counts[letter] > 0:
                feedback[i] = '-'
                counts[letter] -= 1
        return ''.join(feedback)
    
    def get_pattern_distribution(self, candidate, possible_answers):
        # Calculate the distribution of patterns when guessing this candidate
        pattern_counts = {}
        total_weight = sum(self.freq.get(word, 1.0) for word in possible_answers)
        
        for answer in possible_answers:
            pattern = self.get_feedback(candidate, answer)
            weight = self.freq.get(answer, 1.0)
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + weight
            
        # Convert counts to probabilities
        return {pattern: count/total_weight for pattern, count in pattern_counts.items()}
    
    def calculate_entropy(self, distribution):
        # Calculate entropy from a probability distribution
        return -sum(p * math.log2(p) for p in distribution.values())
    
    def hard_mode_filter(self, previous_guess, result, candidates):
        # Filter candidates based on hard mode constraints
        filtered = []
        for word in candidates:
            if self.get_feedback(previous_guess, word) == result:
                filtered.append(word)
        return filtered
        
    def get_guess(self, result):
        if self._manual == 'manual':
            return self.console.input('Your guess:\n')
        
        # Update candidates based on feedback
        if self.last_guess is not None:
            new_candidates = []
            for word in self.candidates:
                if self.get_feedback(self.last_guess, word) == result:
                    new_candidates.append(word)
            self.candidates = new_candidates
        
        # If no candidates remain (shouldn't happen in normal play), reset
        if not self.candidates:
            self.candidates = [w for w in self.word_list if w not in self._tried]
            
        # If only one candidate remains, choose it
        if len(self.candidates) == 1:
            guess = self.candidates[0]
            self._tried.append(guess)
            self.last_guess = guess
            self.console.print(guess)
            return guess
            
        # For the first guess, use a precomputed optimal starter
        if not self._tried:
            guess = self.optimal_starters[0]  # Use optimal first word
            self._tried.append(guess)
            self.last_guess = guess
            self.console.print(guess)
            return guess
            
        # For all other guesses, use full entropy calculation
        best_entropy = -1
        best_guess = None
        
        # Consider both candidates and words from the full wordlist
        # This helps find words that can eliminate more candidates, even if they can't be the answer
        guess_pool = set(self.candidates)
        
        # If we have too many candidates, limit our search to improve performance
        if len(self.candidates) > 2:
            # Add some strategic non-candidate words to consider
            remaining_candidates = self.candidates
            
            # Find which letters are most common in remaining candidates
            letter_freq = Counter(''.join(remaining_candidates))
            
            # Add top words from wordlist that contain the most common letters
            sorted_words = sorted(
                self.word_list, 
                key=lambda w: sum(letter_freq.get(c, 0) for c in set(w)),
                reverse=True
            )
            for word in sorted_words[:100]:  # Add top 100 words with common letters
                guess_pool.add(word)
        
        # Calculate entropy for each potential guess
        for candidate in guess_pool:
            # Skip words we've already tried
            if candidate in self._tried:
                continue
                
            # Calculate pattern distribution and entropy
            distribution = self.get_pattern_distribution(candidate, self.candidates)
            entropy = self.calculate_entropy(distribution)
            
            # Tiebreaker: prefer words that could be the answer
            is_possible_answer = candidate in self.candidates
            
            # Another tiebreaker: prefer more common words
            frequency = self.freq.get(candidate, 0.5)
            
            # Combined score with slight preference for actual candidates and common words
            # Scale this as needed - currently entropy is primary factor
            adjusted_entropy = entropy + (0.01 if is_possible_answer else 0) + (0.001 * frequency)
            
            if adjusted_entropy > best_entropy:
                best_entropy = adjusted_entropy
                best_guess = candidate
        
        # If we somehow didn't find a valid guess, just pick the first valid candidate
        if best_guess is None or best_guess in self._tried:
            for word in self.candidates:
                if word not in self._tried:
                    best_guess = word
                    break
        
        self._tried.append(best_guess)
        self.last_guess = best_guess
        self.console.print(best_guess)
        return best_guess