from random import choice
import yaml
from rich.console import Console
import math
from collections import Counter

USE_FREQUENCY = False
DEBUG = False 

class Guesser:
    def __init__(self, manual, use_frequency=USE_FREQUENCY):
        self.word_list = yaml.load(open('dev_wordlist.yaml'), Loader=yaml.FullLoader)
        self._manual = manual 
        self.console = Console()
        self._tried = []  # List of words already guessed in the current game
        self.candidates = self.word_list.copy()  # All words are initially candidates
        self.last_guess = None
        self.use_frequency = use_frequency
        self.dummy_used = False
        if self.use_frequency:
            self.freq = {}
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
        tried_letters = set(''.join(self._tried))
        if result.count('-') != 0 or self.dummy_used or len(self._tried) >= 5:
            return None
        if result.count('+') == 1:
            pos = result.index('+')
            letters = [word[pos] for word in candidates_to_consider]
            avail = set(letters) - tried_letters
            if len(avail) < 3:
                avail = set(letters)
            if len(avail) < 3:
                return None
            distinct = sorted(avail, key=lambda x: -letters.count(x))
            for letter in "abcdefghijklmnopqrstuvwxyz":
                if letter not in distinct and letter not in tried_letters:
                    distinct.append(letter)
                if len(distinct) >= 5:
                    break
            dummy = ''.join(distinct[:5])
            self.dummy_used = True
            return dummy
        elif result.count('+') == 2:
            positions = [i for i, ch in enumerate(result) if ch == '+']
            pos0, pos1 = positions
            letters0 = [word[pos0] for word in candidates_to_consider]
            letters1 = [word[pos1] for word in candidates_to_consider]
            avail0 = set(letters0) - tried_letters
            if len(avail0) < 2:
                avail0 = set(letters0)
            avail1 = set(letters1) - tried_letters
            if len(avail1) < 2:
                avail1 = set(letters1)
            if len(avail0) + len(avail1) < 4:
                return None
            if len(avail0) >= 2 and len(avail1) >= 2:
                part0 = sorted(avail0, key=lambda x: -letters0.count(x))[:2]
                part1 = sorted(avail1, key=lambda x: -letters1.count(x))[:2]
            elif len(avail0) == 1 and len(avail1) >= 3:
                part0 = sorted(avail0, key=lambda x: -letters0.count(x))[:1]
                part1 = sorted(avail1, key=lambda x: -letters1.count(x))[:3]
            elif len(avail1) == 1 and len(avail0) >= 3:
                part1 = sorted(avail1, key=lambda x: -letters1.count(x))[:1]
                part0 = sorted(avail0, key=lambda x: -letters0.count(x))[:3]
            else:
                part0 = sorted(avail0, key=lambda x: -letters0.count(x))[:2]
                part1 = sorted(avail1, key=lambda x: -letters1.count(x))[:2]
            union_letters = set(part0 + part1)
            if len(union_letters) < 4:
                return None
            overall = sorted(
                set(letter for word in candidates_to_consider for letter in word) - union_letters - tried_letters,
                key=lambda x: -sum(letter == x for word in candidates_to_consider for letter in word)
            )
            common_letter = overall[0] if overall else 'a'
            dummy = ''.join(sorted(union_letters)) + common_letter
            if len(dummy) < 5:
                for letter in "abcdefghijklmnopqrstuvwxyz":
                    if letter not in dummy and letter not in tried_letters:
                        dummy += letter
                    if len(dummy) == 5:
                        break
            elif len(dummy) > 5:
                dummy = dummy[:5]
            self.dummy_used = True
            return dummy
        return None

    def get_guess(self, result):
        if self._manual == 'manual':
            return self.console.input('Your guess:\n')
        else: # Update candidates based on feedback from the previous guess.
            if self.last_guess is not None:
                self.candidates = [word for word in self.candidates 
                                   if self.get_feedback(self.last_guess, word) == result]
            if not self.candidates:
                self.candidates = self.word_list.copy()
        
            # Exclude words that have already been tried.
            candidates_to_consider = [w for w in self.candidates if w not in self._tried]
            if not candidates_to_consider:
                candidates_to_consider = self.candidates
            # If only one candidate remains, choose it.
            if len(candidates_to_consider) == 1:
                guess = candidates_to_consider[0]
                self._tried.append(guess)
                self.console.print(guess)
                self.last_guess = guess
                return guess
            # For the very first guess, use a fixed starting word.
            if self.last_guess is None:
                guess = "tales"
                self._tried.append(guess)
                self.console.print(guess)
                self.last_guess = guess
                return guess

            # --- Special Dummy Guess for Single-Letter Ambiguity ---
            dummy_guess = self.try_dummy_guess(candidates_to_consider, result)
            if dummy_guess is not None:
                self._tried.append(dummy_guess)
                self.console.print("Dummy guess:", dummy_guess)
                self.last_guess = dummy_guess
                return dummy_guess
            
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
                # if DEBUG:
                #     sorted_scores = sorted(scores, key=lambda x: x[1], reverse=True)
                #     self.console.print("Top 5 words by letter-frequency score:", sorted_scores[:5])
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
                # if DEBUG:
                #     sorted_entropies = sorted(entropies, key=lambda x: x[1], reverse=True)
                #     self.console.print("Top 5 words by entropy:", sorted_entropies[:2])
                guess = best_guess
            self._tried.append(guess)
            self.console.print(guess)
            self.last_guess = guess
        return guess