from transformers import GPT2LMHeadModel, GPT2Tokenizer
import torch
from typing import List, Dict, Tuple

class ONIONDefense:
    """
    ONION backdoor defense using GPT-2 for perplexity calculation.
    Based on: "ONION: A Simple and Effective Defense Against Textual Backdoor Attacks"
    Adapted for CodeMMLU dataset.
    """

    def __init__(self, shuffle: bool, model_name: str = "gpt2", device: str = "cuda"):
        """
        Initialize ONION defense with GPT-2.

        Args:
            model_name: GPT-2 model variant ("gpt2", "gpt2-medium", "gpt2-large")
            device: "cuda" or "cpu"
        """
        self.device = device if torch.cuda.is_available() else "cpu"
        print(f"Loading {model_name} on {self.device}...")
        if not shuffle:
            self.tokenizer = GPT2Tokenizer.from_pretrained(model_name)
            self.model = GPT2LMHeadModel.from_pretrained(model_name).to(self.device)
            self.model.eval()

            # Set pad token
            self.tokenizer.pad_token = self.tokenizer.eos_token

    def calculate_perplexity(self, text: str) -> float:
        """
        Calculate perplexity using GPT-2.
        Lower perplexity = more fluent/natural text.

        Args:
            text: Input text/code

        Returns:
            Perplexity score
        """
        try:
            encodings = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=1024)
            input_ids = encodings.input_ids.to(self.device)

            with torch.no_grad():
                outputs = self.model(input_ids, labels=input_ids)
                loss = outputs.loss
                perplexity = torch.exp(loss).item()

            return perplexity

        except Exception as e:
            print(f"Error calculating perplexity: {e}")
            return float('inf')

    def tokenize_by_words(self, text: str) -> List[Tuple[int, int, str]]:
        """
        Split text into words with their positions.

        Returns:
            List of (start_pos, end_pos, word)
        """
        import re
        words = []
        for match in re.finditer(r'\S+', text):
            words.append((match.start(), match.end(), match.group()))
        return words

    def tokenize_by_lines(self, text: str) -> List[Tuple[int, int, str]]:
        """
        Split text into lines with their positions.

        Returns:
            List of (start_pos, end_pos, line)
        """
        lines = []
        pos = 0
        for line in text.split('\n'):
            if line.strip():  # Skip empty lines
                lines.append((pos, pos + len(line), line))
            pos += len(line) + 1
        return lines

    def calculate_suspicion_scores(self,
                                   text: str,
                                   granularity: str = "word") -> List[Dict]:
        """
        Calculate suspicion score for each unit in text.

        ONION Formula: f_i = p_0 - p_i
        where p_0 = original perplexity, p_i = perplexity without word i

        Higher suspicion score = more likely to be a backdoor trigger

        Args:
            text: Input text/code
            granularity: "word" or "line" level analysis

        Returns:
            List of dicts containing suspicion scores for each unit
        """
        # Calculate baseline perplexity
        base_perplexity = self.calculate_perplexity(text)

        # Tokenize based on granularity
        if granularity == "word":
            units = self.tokenize_by_words(text)
        else:
            units = self.tokenize_by_lines(text)

        suspicion_scores = []

        for idx, (start, end, unit_text) in enumerate(units):
            # Create text without this unit
            text_without_unit = text[:start] + text[end:]

            # Skip if result is empty
            if not text_without_unit.strip():
                continue

            # Calculate perplexity without this unit
            perplexity_without = self.calculate_perplexity(text_without_unit)

            # ONION suspicion score: f_i = p_0 - p_i
            suspicion_score = base_perplexity - perplexity_without

            suspicion_scores.append({
                'index': idx,
                'unit': unit_text,
                'suspicion_score': suspicion_score,
                'base_perplexity': base_perplexity,
                'perplexity_without': perplexity_without,
                'position': (start, end)
            })

            # if (idx + 1) % 10 == 0:
            #     print(f"Processed {idx + 1}/{len(units)} {granularity}s...")

        # Sort by suspicion score (descending)
        suspicion_scores.sort(key=lambda x: x['suspicion_score'], reverse=True)

        return suspicion_scores

    def detect_outliers(self,
                       text: str,
                       threshold: float = 0.0,
                       granularity: str = "word") -> Tuple[List[Dict], str]:
        """
        Detect and remove outlier words/lines (potential backdoor triggers).

        Args:
            text: Input text/code
            threshold: Suspicion score threshold (default: 0, as in ONION paper)
            granularity: "word" or "line"

        Returns:
            (outliers, cleaned_text)
            - outliers: List of detected outlier units
            - cleaned_text: Text with outliers removed
        """
        # Calculate suspicion scores
        scores = self.calculate_suspicion_scores(text, granularity)

        # Identify outliers (suspicion score > threshold)
        outliers = [s for s in scores if s['suspicion_score'] > threshold]

        # print(f"\n{'='*60}")
        # print(f"OUTLIER DETECTION RESULTS")
        # print(f"{'='*60}")
        # print(f"Total units analyzed: {len(scores)}")
        # print(f"Outliers detected (score > {threshold}): {len(outliers)}")

        # if outliers:
        #     print(f"\nTop outliers:")
        #     for i, outlier in enumerate(outliers[:5]):
        #         print(f"  {i+1}. Score: {outlier['suspicion_score']:.2f} | Unit: '{outlier['unit'][:50]}...'")

        # Remove outliers from text (in reverse order to maintain positions)
        cleaned_text = text
        outliers_sorted = sorted(outliers, key=lambda x: x['position'][0], reverse=True)

        for outlier in outliers_sorted:
            start, end = outlier['position']
            cleaned_text = cleaned_text[:start] + cleaned_text[end:]

        # Clean up extra whitespace
        cleaned_text = ' '.join(cleaned_text.split())

        return outliers, cleaned_text

    def defend(self,
              text: str,
              threshold: float = 0.0,
              granularity: str = "word",
              return_scores: bool = False) -> Dict:
        """
        Main defense function - detect and remove backdoor triggers.

        Args:
            text: Input text/code (potentially poisoned)
            threshold: Suspicion score threshold
            granularity: "word" or "line"
            return_scores: Whether to return all suspicion scores

        Returns:
            Dictionary with:
            - original_text: Input text
            - cleaned_text: Text with outliers removed
            - outliers: Detected outliers
            - scores: All suspicion scores (if return_scores=True)
        """
        outliers, cleaned_text = self.detect_outliers(text, threshold, granularity)

        result = {
            'original_text': text,
            'cleaned_text': cleaned_text,
            'outliers': outliers,
            'num_outliers': len(outliers),
            'base_perplexity': self.calculate_perplexity(text),
            'cleaned_perplexity': self.calculate_perplexity(cleaned_text)
        }

        if return_scores:
            result['all_scores'] = self.calculate_suspicion_scores(text, granularity)

        return result