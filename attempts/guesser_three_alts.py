from random import choice
import yaml
from rich.console import Console
import math
from collections import Counter
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
        self._cached_first_words = {}  # Cache for first words by method
        
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

    def restart_game(self):
        self._tried = []
        self.candidates = self.word_list.copy()
        self.last_guess = None
        self.dummy_used = False

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

    def calculate_first_word(self, method='entropy'):
        """
        Get the best first word, using cached result if available
        
        Parameters:
        method (str): Strategy to use - 'entropy', 'positional', or 'combo'
        
        Returns:
        str: The best first word according to the selected strategy
        """
        # Check if we've already calculated this method's first word
        if method in self._cached_first_words:
            return self._cached_first_words[method]
            
        # Calculate and cache the result
        if method == 'entropy':
            first_word = self._first_word_entropy()
        elif method == 'positional':
            first_word = self._first_word_positional()
        elif method == 'combo':
            first_word = self._first_word_combo()
        else:
            first_word = "tales"  # Default fallback
            
        # Store in cache
        self._cached_first_words[method] = first_word
        
        # Print the calculated word for reference
        self.console.print(f"[bold green]Optimal first word ({method}): {first_word}[/bold green]")
        
        return first_word

    def _first_word_entropy(self):
        """Calculate best first word using entropy-based approach"""
        # Use all words as candidates
        candidates_to_consider = self.word_list.copy()
        
        best_entropy = -1
        best_guess = None
        
        # Calculate total weight based on frequency if applicable
        total_weight = (sum(self.freq.get(word, 1) for word in candidates_to_consider)
                        if self.use_frequency else len(candidates_to_consider))
        
        # Sample a subset of candidates to test as potential first words
        # This improves performance as checking all words against all words is expensive
        test_candidates = candidates_to_consider[:500] if len(candidates_to_consider) > 500 else candidates_to_consider
        
        for candidate in test_candidates:
            # Track pattern distribution
            distribution = {}
            for answer in candidates_to_consider:
                pattern = self.get_feedback(candidate, answer)
                weight = self.freq.get(answer, 1) if self.use_frequency else 1
                distribution[pattern] = distribution.get(pattern, 0) + weight
            
            # Calculate entropy
            entropy = 0
            for count in distribution.values():
                p = count / total_weight
                entropy -= p * math.log2(p)
            
            if entropy > best_entropy:
                best_entropy = entropy
                best_guess = candidate
        
        return best_guess

    def _first_word_positional(self):
        """Calculate best first word using positional letter frequency"""
        # Create a positional frequency dictionary
        positional_freq = [{} for _ in range(5)]
        
        # Count frequency of each letter at each position
        for word in self.word_list:
            for pos, letter in enumerate(word):
                positional_freq[pos][letter] = positional_freq[pos].get(letter, 0) + 1
        
        # Score each word based on positional letter frequency
        best_score = -1
        best_word = None
        
        for word in self.word_list:
            # Use a set to avoid double-counting repeated letters
            unique_letters = set()
            score = 0
            
            for pos, letter in enumerate(word):
                if letter not in unique_letters:
                    unique_letters.add(letter)
                    score += positional_freq[pos].get(letter, 0)
            
            if score > best_score:
                best_score = score
                best_word = word
        
        return best_word

    def _first_word_combo(self):
        """
        Combine letter frequency and unique letter coverage
        This approach balances common letters with maximizing information gain
        """
        # Get overall letter frequency across all words
        letter_freq = Counter(''.join(self.word_list))
        
        best_score = -1
        best_word = None
        
        for word in self.word_list:
            # Score based on unique letters (to avoid double counting)
            unique_letters = set(word)
            
            # Calculate letter frequency score
            freq_score = sum(letter_freq.get(letter, 0) for letter in unique_letters)
            
            # Penalize for repeated letters
            diversity_factor = len(unique_letters) / 5.0  # 1.0 for words with 5 unique letters
            
            # Calculate positional bias (vowels tend to be better in certain positions)
            pos_factor = 1.0
            vowels = 'aeiou'
            for pos, letter in enumerate(word):
                # Vowels are slightly better in positions 1, 3
                if pos in [1, 3] and letter in vowels:
                    pos_factor *= 1.1
                # Consonants are slightly better in positions 0, 2, 4
                elif pos in [0, 2, 4] and letter not in vowels:
                    pos_factor *= 1.1
            
            # Combine scores
            final_score = freq_score * diversity_factor * pos_factor
            
            if final_score > best_score:
                best_score = final_score
                best_word = word
        
        return best_word

    def get_guess(self, result):
        if self._manual == 'manual':
            return self.console.input('Your guess:\n')
        else: # Update candidates based on feedback from the previous guess.
            if self.last_guess is not None:
                self.candidates = [word for word in self.candidates 
                                  if self.get_feedback(self.last_guess, word) == result]
            if not self.candidates:
                self.candidates = self.word_list.copy()
            candidates_to_consider = [w for w in self.candidates if w not in self._tried]
            if not candidates_to_consider:
                candidates_to_consider = self.candidates
            if len(candidates_to_consider) == 1:
                guess = candidates_to_consider[0]
                self._tried.append(guess)
                self.console.print(guess)
                self.last_guess = guess
                return guess
            if self.last_guess is None:
                # Choose your method: 'entropy', 'positional', or 'combo'
                # The optimal first word will be calculated once and cached
                #guess = self.calculate_first_word(method='combo')
                guess = 'tales'
                self._tried.append(guess)
                self.console.print(guess)
                self.last_guess = guess
                return guess
            
            #dummy_guess = self.try_dummy_guess(candidates_to_consider, result)
            dummy_guess = None
            if dummy_guess is not None:
                self._tried.append(dummy_guess)
                self.console.print("Dummy guess:", dummy_guess)
                self.last_guess = dummy_guess
                return dummy_guess
            print(len(candidates_to_consider))
            if len(candidates_to_consider) > 50: # heuristic / entropy choice
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
                scores = []
                for word in candidates_to_consider:
                    score = sum(letter_counts.get(c, 0) for c in set(word))
                    scores.append((word, score))
                    if score > best_score:
                        best_score = score
                        best_guess = word
                guess = best_guess
            else:
                best_entropy = -1
                best_guess = None
                total_weight = (sum(self.freq.get(word, 1) for word in candidates_to_consider)
                                if self.use_frequency else len(candidates_to_consider))
                entropies = []
                for candidate in candidates_to_consider:
                    distribution = {}
                    for answer in candidates_to_consider:
                        pattern = self.get_feedback(candidate, answer)
                        weight = self.freq.get(answer, 1) if self.use_frequency else 1
                        distribution[pattern] = distribution.get(pattern, 0) + weight
                    entropy = 0
                    for count in distribution.values():
                        p = count / total_weight
                        entropy -= p * math.log2(p)
                    entropies.append((candidate, entropy))
                    if entropy > best_entropy:
                        best_entropy = entropy
                        best_guess = candidate
                guess = best_guess
            self._tried.append(guess)
            self.console.print(guess)
            self.last_guess = guess
        return guess