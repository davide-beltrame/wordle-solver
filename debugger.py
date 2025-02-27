from random import choice, sample
import yaml
from collections import Counter
import math
from functools import lru_cache
from tqdm import tqdm
import time
import itertools
from string import ascii_lowercase

class WordleDebugger:
    def __init__(self, wordlist_path='wordlist.yaml'):
        self.word_list = yaml.load(open(wordlist_path), Loader=yaml.FullLoader)
        self.total_words = len(self.word_list)
        # Extract letter frequency information
        self.letter_freqs = self._calculate_letter_frequencies()
        
    def _calculate_letter_frequencies(self):
        """Calculate letter frequencies in the word list by position."""
        position_freqs = [{} for _ in range(5)]
        for word in self.word_list:
            for i, letter in enumerate(word):
                position_freqs[i][letter] = position_freqs[i].get(letter, 0) + 1
        
        # Convert to frequency
        for pos_dict in position_freqs:
            for letter in pos_dict:
                pos_dict[letter] /= self.total_words
                
        return position_freqs
        
    @lru_cache(maxsize=1000000)
    def get_feedback(self, guess, answer):
        """Calculate feedback pattern using memoization."""
        counts = Counter(answer)
        feedback = [''] * len(guess)
        
        # First pass: mark correct positions
        for i, letter in enumerate(guess):
            if letter == answer[i]:
                feedback[i] = letter
                counts[letter] -= 1
            else:
                feedback[i] = '+'
                
        # Second pass: mark letters that are present but misplaced
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
    
    def generate_synthetic_words(self, num_words=1000, strategy='frequency'):
        """
        Generate synthetic words optimized for information gain.
        
        Strategies:
        - 'frequency': Use common letters in each position
        - 'diversity': Maximize letter diversity
        - 'entropy': Generate words and score by entropy
        """
        if strategy == 'frequency':
            # Generate words using letter frequency by position
            synthetic_words = []
            for _ in range(num_words):
                word = ''
                for pos in range(5):
                    # Sample letter based on frequency in this position
                    letters, freqs = zip(*self.letter_freqs[pos].items())
                    word += choice(letters)  # Simple sampling, could be weighted
                synthetic_words.append(word)
            return synthetic_words
            
        elif strategy == 'diversity':
            # Generate words that maximize letter diversity
            synthetic_words = []
            # Common letters to prioritize
            vowels = 'aeiou'
            common_consonants = 'rstlncdpm'
            
            # Generate words with diverse letter combinations
            for v1 in vowels:
                for v2 in vowels:
                    if v1 != v2:
                        for c1 in common_consonants:
                            for c2 in common_consonants:
                                if c1 != c2:
                                    for c3 in common_consonants:
                                        if c3 not in (c1, c2):
                                            word = c1 + v1 + c2 + v2 + c3
                                            synthetic_words.append(word)
                                            if len(synthetic_words) >= num_words:
                                                return synthetic_words
            return synthetic_words
            
        elif strategy == 'entropy':
            # Generate a larger set of candidate words
            candidates = self.generate_synthetic_words(num_words * 10, 'diversity')
            candidates += self.generate_synthetic_words(num_words * 10, 'frequency')
            
            # Evaluate entropy for each candidate
            candidates_tuple = tuple(self.word_list)
            word_entropies = []
            
            for word in tqdm(candidates):
                entropy = self.calculate_entropy(word, candidates_tuple)
                word_entropies.append((word, entropy))
            
            word_entropies.sort(key=lambda x: x[1], reverse=True)
            return [word for word, _ in word_entropies[:num_words]]
        
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
    
    def find_best_starters(self, num_words=20, sample_size=None, include_synthetic=True):
        """Find the best starting words based on entropy."""
        if sample_size is None:
            candidates = tuple(self.word_list)
        else:
            candidates = tuple(sample(self.word_list, min(sample_size, len(self.word_list))))
        
        # Define word candidates to evaluate
        words_to_evaluate = []
        
        # Add real dictionary words
        words_to_evaluate.extend(self.word_list)
        
        # Add synthetic words if requested
        if include_synthetic:
            print("Generating synthetic words...")
            synthetic_words = self.generate_synthetic_words(500, 'diversity')
            synthetic_words += self.generate_synthetic_words(500, 'frequency')
            words_to_evaluate.extend(synthetic_words)
            
            # Add words with maximum letter diversity
            # Most information-rich letters in Wordle: e, a, r, o, t, l, i, s, n
            info_rich_letters = 'earotlisn'
            for combo in itertools.combinations(info_rich_letters, 5):
                words_to_evaluate.append(''.join(combo))
        
        print(f"Analyzing {len(words_to_evaluate)} words to find the best {num_words} starters...")
        
        word_entropies = []
        for word in tqdm(words_to_evaluate):
            entropy = self.calculate_entropy(word, candidates)
            word_entropies.append((word, entropy))
        
        word_entropies.sort(key=lambda x: x[1], reverse=True)
        return word_entropies[:num_words]
    
    def analyze_second_guesses(self, first_guess, num_patterns=10, num_second_guesses=5):
        """Analyze the best second guesses after a given first guess for the most common patterns."""
        candidates_tuple = tuple(self.word_list)
        pattern_distribution = self.calculate_pattern_distribution(first_guess, candidates_tuple)
        
        # Sort patterns by frequency (most common first)
        sorted_patterns = sorted(pattern_distribution.items(), key=lambda x: x[1], reverse=True)
        top_patterns = sorted_patterns[:num_patterns]
        
        results = {}
        for pattern, count in top_patterns:
            # Find words that would produce this pattern
            filtered_candidates = [word for word in self.word_list 
                                  if self.get_feedback(first_guess, word) == pattern]
            filtered_tuple = tuple(filtered_candidates)
            
            # Calculate best second guesses
            word_entropies = []
            for word in self.word_list:
                if word != first_guess:  # Don't repeat the first guess
                    entropy = self.calculate_entropy(word, filtered_tuple)
                    word_entropies.append((word, entropy))
            
            word_entropies.sort(key=lambda x: x[1], reverse=True)
            best_second_guesses = word_entropies[:num_second_guesses]
            
            results[pattern] = {
                'count': count,
                'percentage': (count / self.total_words) * 100,
                'best_second_guesses': best_second_guesses,
                'remaining_candidates': len(filtered_candidates)
            }
        
        return results
    
    def simulate_games(self, first_word, second_word_strategy='highest_entropy', num_games=100):
        """
        Simulate games with specified first word and second word strategy.
        
        second_word_strategy can be:
        - 'highest_entropy': choose the word with highest entropy
        - 'fixed_word': use the same second word provided as a parameter
        """
        total_guesses = 0
        max_guesses = 0
        guess_distribution = Counter()
        
        def simulate_game(answer):
            nonlocal total_guesses, max_guesses
            
            guesses = [first_word]
            candidates = self.word_list.copy()
            
            # Process first guess
            pattern = self.get_feedback(first_word, answer)
            if pattern == answer:  # Solved in one guess
                guess_distribution[1] += 1
                return 1
            
            candidates = [word for word in candidates if self.get_feedback(first_word, word) == pattern]
            
            # Choose second word
            if second_word_strategy == 'highest_entropy':
                candidates_tuple = tuple(candidates)
                best_second_word = max(self.word_list, 
                                      key=lambda word: self.calculate_entropy(word, candidates_tuple) if word != first_word else -1)
                second_word = best_second_word
            else:
                second_word = second_word_strategy  # Using the provided fixed second word
            
            guesses.append(second_word)
            
            # Process second guess
            pattern = self.get_feedback(second_word, answer)
            if pattern == answer:  # Solved in two guesses
                guess_distribution[2] += 1
                return 2
            
            candidates = [word for word in candidates if self.get_feedback(second_word, word) == pattern]
            
            # Continue with standard entropy-based approach
            guess_count = 2
            while candidates and guess_count < 6:
                guess_count += 1
                
                if len(candidates) == 1:
                    next_guess = candidates[0]
                else:
                    candidates_tuple = tuple(candidates)
                    next_guess = max(candidates, 
                                    key=lambda word: self.calculate_entropy(word, candidates_tuple))
                
                guesses.append(next_guess)
                pattern = self.get_feedback(next_guess, answer)
                
                if pattern == answer:
                    guess_distribution[guess_count] += 1
                    return guess_count
                
                candidates = [word for word in candidates if self.get_feedback(next_guess, word) == pattern]
            
            # Failed to guess in 6 tries
            guess_distribution[6] += 1
            return 6
        
        sample_answers = sample(self.word_list, min(num_games, len(self.word_list)))
        
        start_time = time.time()
        for answer in tqdm(sample_answers):
            num_guesses = simulate_game(answer)
            total_guesses += num_guesses
            max_guesses = max(max_guesses, num_guesses)
        
        avg_guesses = total_guesses / len(sample_answers)
        execution_time = time.time() - start_time
        
        return {
            'first_word': first_word,
            'second_word_strategy': second_word_strategy,
            'num_games': len(sample_answers),
            'avg_guesses': avg_guesses,
            'max_guesses': max_guesses,
            'guess_distribution': dict(guess_distribution),
            'score': 100 * (7 - avg_guesses),
            'execution_time': execution_time
        }
    
    def optimize_first_guess_manually(self):
        """Create and test specific handcrafted first guesses."""
        # These are known to be information-rich letter combinations
        candidates = [
            "soare", "roate", "raise", "raile", "slate", "crate", "irate", "trace",  # Dictionary words
            "arose", "adieu", "audio", "stare", "tears", "lares", "tares",
            # Non-dictionary optimal combinations
            "earot", "aorst", "strle", "arste", "etaoi", "etnos", "earts",
            "eaito", "earls", "stnlr", "saeio", "arise", "orate"
        ]
        
        results = []
        candidates_tuple = tuple(self.word_list)
        
        for word in candidates:
            entropy = self.calculate_entropy(word, candidates_tuple)
            results.append((word, entropy))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results

# Example usage
if __name__ == "__main__":
    debugger = WordleDebugger()
    
    # Test manually optimized first guesses
    print("\n=== MANUALLY OPTIMIZED FIRST GUESSES ===")
    manual_best = debugger.optimize_first_guess_manually()
    for i, (word, entropy) in enumerate(manual_best, 1):
        print(f"{i}. {word}: {entropy:.4f}")
    
    # Find best starting words (including synthetic)
    print("\n=== TOP STARTING WORDS (WITH SYNTHETIC) ===")
    best_starters = debugger.find_best_starters(num_words=20, sample_size=500, include_synthetic=True)
    for i, (word, entropy) in enumerate(best_starters, 1):
        print(f"{i}. {word}: {entropy:.4f}")
    
    # Analyze second guesses for the top starting word
    print("\n=== SECOND GUESSES ANALYSIS ===")
    top_word = best_starters[0][0]
    print(f"For first guess '{top_word}':")
    second_guess_analysis = debugger.analyze_second_guesses(top_word)
    
    for pattern, data in second_guess_analysis.items():
        print(f"\nPattern: {pattern} (occurs {data['percentage']:.2f}% of the time)")
        print(f"Remaining candidates: {data['remaining_candidates']}")
        print("Best second guesses:")
        for word, entropy in data['best_second_guesses']:
            print(f"  {word}: {entropy:.4f}")
    
    # Simulate games with different strategies
    print("\n=== GAME SIMULATION ===")
    # Take top 3 from synthetic words
    top_first_words = [word for word, _ in best_starters[:3]]
    
    for first_word in top_first_words:
        # Simulate with dynamic second word
        result = debugger.simulate_games(first_word, 'highest_entropy', num_games=100)
        print(f"\nFirst word: {first_word}, Dynamic second word")
        print(f"Average guesses: {result['avg_guesses']:.4f}")
        print(f"Score: {result['score']:.2f}")
        print(f"Guess distribution: {result['guess_distribution']}")
        print(f"Execution time: {result['execution_time']:.2f} seconds")