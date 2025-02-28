import itertools
import math
from collections import Counter
from functools import lru_cache
from itertools import product

import yaml
from rich.console import Console


class Guesser:
    """
    INSTRUCTIONS: This function should return your next guess.
    Currently it picks a random word from wordlist and returns that.
    You will need to parse the output from Wordle:
    - If your guess contains that character in a different position, Wordle will return a '-' in that position.
    - If your guess does not contain thta character at all, Wordle will return a '+' in that position.
    - If you guesses the character placement correctly, Wordle will return the character.

    You CANNOT just get the word from the Wordle class, obviously :)
    """

    def __init__(self, manual):
        self.word_list = yaml.load(open("dev_wordlist.yaml"), Loader=yaml.FullLoader)
        self._manual = manual
        self.console = Console()
        self._tried = []
        self._search_space = list(self.word_list)

        self.best_first_guess = self._find_first_guess()

    def restart_game(self):
        self._tried = []
        self._search_space = list(self.word_list)

    def _find_first_guess(self):
        """
        Find the single word with highest entropy based on positional frequency.
        Optimized version of find_top_k_entropy_combinations that doesn't do sorting.
        """
        # Calculate letter frequencies for each position
        letter_frequencies = self._compute_letter_frequencies()

        # Get top 3 most common letters for each position
        top_letters_per_pos = []
        for _, pos_freq in letter_frequencies.items():
            top_letters = [letter for letter, _ in pos_freq.most_common(3)]
            top_letters_per_pos.append(top_letters)

        # Track just the best word and its entropy
        best_word = None
        best_entropy = float("-inf")

        # Generate candidate words by taking combinations of top letters
        for letters in product(*top_letters_per_pos):
            # Skip if letters aren't unique
            if len(set(letters)) != 5:
                continue

            word = "".join(letters)

            # Calculate the pattern entropy
            pattern_entropy = self._compute_partition_entropy(word, self._search_space)

            # Update best word if this one has higher entropy
            if pattern_entropy > best_entropy:
                best_entropy = pattern_entropy
                best_word = word

        return best_word

    def get_guess(self, result):
        """
        This function must return your guess as a string.
        """
        if self._manual == "manual":
            return self.console.input("Your guess:\n")
        else:
            guess = self._get_best_guess(result)
            self._tried.append(guess)
            self.console.print(guess)
            return guess

    def _get_best_guess(self, result):
        if self._tried == []:
            return self.best_first_guess

        self.filter_words(self._tried[-1], result)  # inplace

        n_remaining = len(self._search_space)

        # if something went wrong
        if n_remaining == 0:
            return "zzzzz"

        # if only one word left there is no much to do
        if n_remaining <= 2:
            return self._search_space[0]

        if n_remaining <= 20:
            # check if is_fully_disambiguating is working
            for word in self._search_space:
                if self.is_fully_disambiguating(word, self._search_space):
                    return word

            disambiguator = self._propose_possible_disambiguators(100)
            if disambiguator:
                return disambiguator

        return self._get_best_guess_by_pattern_entropy()[0]

    def _get_best_guess_by_pattern_entropy(self):
        """Find word in search space that maximizes entropy"""
        best_word = None
        best_entropy = float("-inf")

        for word in self._search_space:
            entropy = self._compute_partition_entropy(word, self._search_space)
            if entropy > best_entropy:
                best_entropy = entropy
                best_word = word

        return best_word, best_entropy

    def _compute_pattern_partitions(self, guess, search_space):
        """Compute how a guess partitions the search space"""
        partitions = {}
        for possible_word in search_space:
            pattern = self._get_pattern(guess, possible_word)
            partitions[pattern] = partitions.get(pattern, 0) + 1
        return partitions

    def _compute_partition_entropy(self, guess, search_space):
        """Compute entropy of the partition created by a guess"""
        partitions = self._compute_pattern_partitions(guess, search_space)
        total_words = len(search_space)

        entropy = 0
        for count in partitions.values():
            p = count / total_words
            entropy -= p * math.log2(p)

        return entropy

    @lru_cache(maxsize=None)
    def _get_pattern(self, guess, target):
        """
        Directly compute the pattern string without using the binary intermediate step.
        This avoids the overhead of binary operations and string concatenation.
        """
        # Pre-allocate an array for the pattern characters
        pattern_chars = [None] * 5

        # Count character frequencies in target for handling duplicates
        target_chars = {}
        for char in target:
            target_chars[char] = target_chars.get(char, 0) + 1

        # First pass: mark green matches and reduce available counts
        for i in range(5):
            if guess[i] == target[i]:
                pattern_chars[i] = guess[i]  # Green match
                target_chars[guess[i]] -= 1

        # Second pass: mark yellow or gray positions
        for i in range(5):
            if pattern_chars[i] is None:  # Not already marked as green
                if guess[i] in target_chars and target_chars[guess[i]] > 0:
                    pattern_chars[i] = "-"  # Yellow
                    target_chars[guess[i]] -= 1
                else:
                    pattern_chars[i] = "+"  # Gray

        # Join the pattern characters into a string
        return "".join(pattern_chars)

    def _compute_letter_frequencies(self) -> dict:
        """
        Computes the frequency of each letter at each position (0-4) in the word list.
        Returns a data structure that allows efficient lookup of letter frequencies by position.

        Returns:
            list: A list of Counter objects, where each Counter contains letter frequencies
                for that position.
        """
        return {i: Counter(word[i] for word in self._search_space) for i in range(5)}

    def _compute_absolute_frequencies(self):
        """
        Compute the absolute frequency of each letter at each position in the search space.
        """
        return Counter("".join(self._search_space))
    

    ##############################
    #   Filtering Search Space   #
    ##############################

    def _guess_to_colors(self, guess, pattern):
        data = {"gray": [], "yellow": {}, "green_pos": {}, "required_letters": {}}

        for i, (g, p) in enumerate(zip(guess, pattern)):
            if p == "+":
                data["gray"].append(g)
            elif p == "-":
                data["yellow"][g] = data["yellow"].get(g, set())
                data["yellow"][g].add(i)
                data["required_letters"][g] = data["required_letters"].get(g, 0) + 1
            else:
                data["green_pos"][i] = g  # Changed to map position -> letter
                data["required_letters"][g] = data["required_letters"].get(g, 0) + 1

        return data

    def filter_words(self, guess, pattern):
        data = self._guess_to_colors(guess, pattern)
        # Create a new filtered list
        filtered_search_space = []
        for word in self._search_space:
            # Assume the word is valid until proven otherwise
            is_valid = True

            # Check required letters
            if not all(
                word.count(letter) >= count
                for letter, count in data["required_letters"].items()
            ):
                is_valid = False
                continue

            # Check green positions
            for pos, letter in data["green_pos"].items():
                if word[pos] != letter:
                    is_valid = False
                    break

            if not is_valid:
                continue

            # Check yellow positions (letter should not be in these positions)
            for letter, positions in data["yellow"].items():
                for pos in positions:
                    if word[pos] == letter:
                        is_valid = False
                        break

                if not is_valid:
                    break

            if not is_valid:
                continue

            # Check gray letters
            for letter in data["gray"]:
                if letter in data["required_letters"]:
                    # If the letter is also a green or yellow letter, make sure we haven't exceeded the required count
                    if word.count(letter) > data["required_letters"][letter]:
                        is_valid = False
                        break
                elif letter in word:
                    # If the letter is only gray, it shouldn't be in the word at all
                    is_valid = False
                    break

            # If the word passed all checks, add it to the filtered list
            if is_valid:
                filtered_search_space.append(word)

        # Replace the search space with the filtered list
        self._search_space = filtered_search_space

    def _least_common(self, counter, n):
        all_items = counter.most_common()
        return all_items[-n:]  # Gets the n least common items

    ##############################
    #   Disambiguator Proposals  #
    ##############################
    def is_fully_disambiguating(self, guess, possible_words):
        """
        Check if a guess completely disambiguates between all possible words.

        Args:
            guess: The candidate guess
            possible_words: List of possible solution words

        Returns:
            Boolean indicating if the guess fully disambiguates
        """
        patterns = set()
        for word in possible_words:
            pattern = self._get_pattern(guess, word)
            if pattern in patterns:
                return False
            patterns.add(pattern)
        return True
    

    def _propose_possible_disambiguators(self, max_candidates=50):
        """
        Propose the best possible disambiguator based on the current search space.
        Uses absolute letter frequencies to prioritize rare letters.
        Returns the fully disambiguating word if found, or the best partial disambiguator otherwise.
        """
        # Calculate absolute letter frequencies
        letter_frequencies = self._compute_absolute_frequencies()

        # Sort letters by frequency (least common first)
        sorted_letters = sorted(letter_frequencies.items(), key=lambda x: x[1])

        # Separate letters into priority groups
        rare_letters = [letter for letter, count in sorted_letters if count <= 2]
        other_letters = [letter for letter, count in sorted_letters if count > 2]

        # Track the best disambiguator and its quality
        best_disambiguator = None
        best_quality = (float("inf"), 0)  # (max_partition_size, -num_partitions)

        # First, try to create words using only rare letters
        if len(rare_letters) >= 5:
            candidates = self._generate_word_candidates(
                rare_letters, max_candidates // 2
            )
            best_disambiguator, best_quality = self._evaluate_candidates(
                candidates, best_disambiguator, best_quality
            )

        # If no perfect disambiguator found, try combining rare and other letters
        if best_quality[0] > 1 and len(rare_letters) + len(other_letters) >= 5:
            # Prioritize rare letters, then add others as needed
            all_letters = rare_letters + other_letters
            candidates = self._generate_word_candidates(
                all_letters, max_candidates // 2
            )
            best_disambiguator, best_quality = self._evaluate_candidates(
                candidates, best_disambiguator, best_quality
            )

        return best_disambiguator

    def _evaluate_candidates(self, candidates, best_disambiguator, best_quality):
        """
        Evaluate a list of candidate words for their disambiguation quality.
        Returns the best disambiguator and its quality.
        """
        for word in candidates:
            # Check if this word fully disambiguates
            if self.is_fully_disambiguating(word, self._search_space):
                return word, (1, -len(self._search_space))  # Perfect quality

            # Calculate disambiguation quality for this word
            quality = self.get_disambiguation_quality(word, self._search_space)
            if quality[0] > 2:
                continue

            # Update best disambiguator if this one is better
            if quality < best_quality:  # Lower is better for both components of quality
                best_disambiguator = word
                best_quality = quality

        return best_disambiguator, best_quality

    def get_disambiguation_quality(self, guess, possible_words):
        """
        Compute how well a guess disambiguates between possible words.

        Args:
            guess: The candidate guess
            possible_words: List of possible solution words

        Returns:
            Tuple (max_partition_size, -num_partitions) where:
            - max_partition_size is the size of the largest group of words that share a pattern
            - num_partitions is the total number of unique patterns generated (negated for sorting)

        Lower values are better (smaller partitions, more unique patterns)
        """
        # Group words by their pattern
        pattern_groups = {}
        for word in possible_words:
            pattern = self._get_pattern(guess, word)
            if pattern not in pattern_groups:
                pattern_groups[pattern] = []
            pattern_groups[pattern].append(word)

        # Calculate quality metrics
        max_partition_size = max(len(group) for group in pattern_groups.values())
        num_partitions = len(pattern_groups)

        return (
            max_partition_size,
            -num_partitions,
        )  # Negate num_partitions so smaller values are better overall

    def _generate_word_candidates(self, letters, max_count):
        """
        Generate candidate words using the provided letters.
        Ensures all candidates have 5 unique letters.
        """
        candidates = []

        # If we have at least 5 letters, we can generate combinations
        if len(letters) >= 5:
            # Take combinations of 5 letters
            for combo in itertools.combinations(
                letters[:10], 5
            ):  # Limit to first 10 letters for efficiency
                candidates.append("".join(combo))
                if len(candidates) >= max_count:
                    break

        return candidates