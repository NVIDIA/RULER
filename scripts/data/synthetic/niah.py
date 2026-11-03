# Copyright (c) 2024, NVIDIA CORPORATION.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License

"""
Create a dataset jsonl file for needle in a haystack.

python niah.py \
    --save_dir=./ \
    --save_name=niah_single \
    --tokenizer_path=tokenizer.model \
    --tokenizer_type=nemo \
    --max_seq_length=4096 \
    --tokens_to_generate=128 \
    --num_samples=10 \
    --template="Some special magic {type_needle_v} are hidden within the following text. Make sure to memorize it. I will quiz you about the {type_needle_v} afterwards.\n{context}\nWhat are all the special magic {type_needle_v} for {query} mentioned in the provided text? The special magic {type_needle_v} for {query} mentioned in the provided text are"
"""
import os
import re
import json
import uuid
import argparse
import numpy as np
from pathlib import Path
from tqdm import tqdm
import random
import wonderwords
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from tokenizer import select_tokenizer
from manifest_utils import write_manifest
from nltk.tokenize import sent_tokenize
import logging

logging.basicConfig(level=logging.INFO, force=True)
logger = logging.getLogger(__name__)


from constants import TASKS

parser = argparse.ArgumentParser()
# Basic Configurations
parser.add_argument("--save_dir", type=Path, required=True, help='dataset folder to save dataset')
parser.add_argument("--save_name", type=str, required=True, help='name of the save dataset jsonl file')
parser.add_argument("--subset", type=str, default='validation', help='Options: validation or test')
parser.add_argument("--tokenizer_path", type=str, required=True, help='path to the tokenizer model')
parser.add_argument("--tokenizer_type",  type=str, default='nemo', help='[Options] nemo, hf, openai.')
parser.add_argument("--max_seq_length", type=int, required=True, help='max sequence length including all input tokens and generated tokens.')
parser.add_argument("--tokens_to_generate", type=int, required=True, help='expected generated token amount.')
parser.add_argument("--num_samples", type=int, required=True, help='number of samples to generate')
parser.add_argument("--random_seed", type=int, default=42)
parser.add_argument("--template", type=str, default='', help='prompt template')
parser.add_argument("--remove_newline_tab", action='store_true', help='remove `\n` and `\t` in all strings.')

# Complexity Configurations
parser.add_argument("--num_needle_k", type=int, default=1)
parser.add_argument("--num_needle_v", type=int, default=1)
parser.add_argument("--num_needle_q", type=int, default=1)
parser.add_argument("--type_haystack", type=str, default='essay', help='[Options] noise, essay, needle.')
parser.add_argument("--type_needle_k", type=str, default='words', help='[Options] numbers, words, uuids.')
parser.add_argument("--type_needle_v", type=str, default='numbers', help='[Options] numbers, words, uuids.')
parser.add_argument("--model_template_token", type=int, default=0, help='used for nemo skills, minus num of model template token')

args = parser.parse_args()
random.seed(args.random_seed)
np.random.seed(args.random_seed)
args.num_needle_k = max(args.num_needle_k, args.num_needle_q)

# Load Tokenizer
TOKENIZER = select_tokenizer(args.tokenizer_type, args.tokenizer_path)

# Define Needle/Haystack Format
needle = "One of the special magic {type_needle_v} for {key} is: {value}."
if args.type_haystack == 'essay':
    essay = os.path.join(os.path.dirname(os.path.abspath(__file__)), "json/PaulGrahamEssays.json")
    essay = json.load(open(essay))['text']
    haystack = re.sub(r'\s+', " ", essay).split(" ")
elif args.type_haystack == 'noise':
    haystack = "The grass is green. The sky is blue. The sun is yellow. Here we go. There and back again."
elif args.type_haystack == 'needle':
    haystack = needle
else:
    raise NotImplementedError(f'{args.type_haystack} is not implemented.')


# Words
nouns = wonderwords.random_word._get_words_from_text_file("nounlist.txt")
adjs = wonderwords.random_word._get_words_from_text_file("adjectivelist.txt")
# verbs = wonderwords.random_word._get_words_from_text_file("verblist.txt")
words = [f"{adj}-{noun}" for adj in adjs for noun in nouns]
words = sorted(list(set(words)))


# Positions
DEPTHS = list(np.round(np.linspace(0, 100, num=40, endpoint=True)).astype(int))


def generate_random_number(num_digits=7):
    lower_bound = 10**(num_digits - 1)
    upper_bound = 10**num_digits - 1
    return str(random.randint(lower_bound, upper_bound))

def generate_random_word():
    word = random.choice(words)
    return word

def generate_random_uuid():
    return str(uuid.UUID(int=random.getrandbits(128), version=4))

def generate_random(type_needle: str):
    if type_needle == 'numbers':
        return generate_random_number()
    elif type_needle == 'words':
        return generate_random_word()
    elif type_needle == 'uuids':
        return generate_random_uuid()
    else:
        raise NotImplementedError(f'{args.type_needle} is not implemented.')

def generate_input_output(num_haystack):
    keys, values, needles = [], [], []
    for _ in range(args.num_needle_k):
        keys.append(generate_random(args.type_needle_k))
        value = []
        for _ in range(args.num_needle_v):
            value.append(generate_random(args.type_needle_v))
            needles.append(needle.format(
                type_needle_v=args.type_needle_v,
                key=keys[-1],
                value=value[-1],
            ))
        values.append(value)

    random.Random(args.random_seed).shuffle(needles)

    # Context
    if args.type_haystack == 'essay':
        text = " ".join(haystack[:num_haystack])
        if num_haystack <= len(haystack):
            text = " ".join(haystack[:num_haystack])
        else:
            # Repeat haystack as many times as needed and slice to num_haystack
            repeats = (num_haystack + len(haystack) - 1) // len(haystack)  # Ceiling division
            text = " ".join((haystack * repeats)[:num_haystack])
        document_sents = sent_tokenize(text.strip())
        insertion_positions = [0] + \
                              sorted([int(len(document_sents) * (depth / 100)) for depth in random.sample(DEPTHS, len(needles))]) + \
                              [len(document_sents)]
        document_sents_list = []
        for i in range(1,len(insertion_positions)):
            last_pos = insertion_positions[i-1]
            next_pos = insertion_positions[i]
            document_sents_list.append(" ".join(document_sents[last_pos:next_pos]))
            if i-1 < len(needles):
                document_sents_list.append(needles[i-1])
        context = " ".join(document_sents_list)

    else:
        if args.type_haystack == 'noise':
            sentences = [haystack] * num_haystack
        elif args.type_haystack == 'needle':
            sentences = [haystack.format(
                type_needle_v=args.type_needle_v,
                key=generate_random(args.type_needle_k),
                value=generate_random(args.type_needle_v),
            ) for _ in range(num_haystack)]


        indexes = sorted(random.sample(range(num_haystack), len(needles)), reverse=True)
        for index, element in zip(indexes, needles):
            sentences.insert(index, element)
        context = "\n".join(sentences)


    ## Query and Answer
    indices = random.sample(range(args.num_needle_k), args.num_needle_q)
    queries = [keys[i] for i in indices]
    answers = [a for i in indices for a in values[i]]
    query = ', '.join(queries[:-1]) + ', and ' + queries[-1] if len(queries) > 1 else queries[0]

    template = args.template
    type_needle_v = args.type_needle_v
    if args.num_needle_q * args.num_needle_v == 1:
        template = template.replace('Some', 'A')
        template = template.replace('are all', 'is')
        template = template.replace('are', 'is')
        template = template.replace('answers', 'answer')
        type_needle_v = type_needle_v[:-1] # remove "s"

    input_text = template.format(
        type_needle_v=type_needle_v,
        context=context,
        query=query,
    )

    return input_text, answers


def generate_samples(num_samples: int, max_seq_length: int, save_dir: str, incremental: int = 500):
    write_jsons = []
    tokens_to_generate = args.tokens_to_generate
    max_seq_length -= args.model_template_token

    if args.type_haystack == 'essay':
        incremental = 500
    elif args.type_haystack == 'noise':
        incremental = 25
    elif args.type_haystack == 'needle':
        incremental = 25

    if args.type_haystack != 'essay' and args.max_seq_length < 4096:
        incremental = 5

    # Estimate tokens per question to determine reasonable upper bound
    sample_input_text, _ = generate_input_output(incremental)
    sample_tokens = len(TOKENIZER.text_to_tokens(sample_input_text))
    tokens_per_haystack = sample_tokens / incremental

    # Let's do 3x to allow for some slack since we can get unlucky due to sampling.
    # NOTE: We should test this for really large sequence lengths to make sure it's reasonable.
    estimated_max_questions = int((max_seq_length / tokens_per_haystack) * 3)

    # Binary search for optimal haystack size
    lower_bound = incremental
    upper_bound = max(estimated_max_questions, incremental * 2)  # Ensure upper_bound is reasonable

    optimal_num_haystack = None

    logger.info(f"Estimated {tokens_per_haystack:.1f} tokens per haystack")
    logger.info(f"Starting binary search with bounds: {lower_bound} to {upper_bound}")

    while lower_bound <= upper_bound:
        mid = (lower_bound + upper_bound) // 2
        input_text, answer = generate_input_output(mid)
        total_tokens = len(TOKENIZER.text_to_tokens(input_text)) + tokens_to_generate

        logger.info(f"Testing haystack size: {mid}, resulting tokens: {total_tokens}/{max_seq_length}")

        if total_tokens <= max_seq_length:
            # This size works, can we go larger?
            optimal_num_haystack = mid
            lower_bound = mid + 1
        else:
            # Too large, need to go smaller
            upper_bound = mid - 1

    num_haystack = optimal_num_haystack if optimal_num_haystack is not None else incremental
    logger.info(f'Final optimal haystack size (number of haystack): {num_haystack}')



    # Generate samples
    for index in tqdm(range(num_samples)):
        used_haystack = num_haystack
        while(True):
            try:
                input_text, answer  = generate_input_output(used_haystack)
                length = len(TOKENIZER.text_to_tokens(input_text)) + tokens_to_generate
                assert length <= max_seq_length, f"{length} exceeds max_seq_length."
                break
            except:
                if used_haystack > incremental:
                    used_haystack -= incremental

        if args.remove_newline_tab:
            input_text = ' '.join(input_text.replace('\n', ' ').replace('\t', ' ').strip().split())
        answer_prefix_index = input_text.rfind(TASKS['niah']['answer_prefix'][:10]) # use first 10 char of answer prefix to locate it
        answer_prefix = input_text[answer_prefix_index:]
        input_text = input_text[:answer_prefix_index]
        # find answer position in text
        answer_pos = input_text.find(answer[0])
        token_position_answer = len(TOKENIZER.text_to_tokens(input_text[:answer_pos]))
        formatted_output = {
            'index': index,
            "input": input_text,
            "outputs": answer,
            "length": length,
            'length_w_model_temp': length + args.model_template_token,
            'answer_prefix': answer_prefix,
            'token_position_answer': token_position_answer,
        }
        write_jsons.append(formatted_output)

    return write_jsons


def main():
    save_file = args.save_dir / f'{args.save_name}' / f'{args.subset}.jsonl'
    save_file.parent.mkdir(parents=True, exist_ok=True)
    write_jsons = generate_samples(
        num_samples=args.num_samples,
        max_seq_length=args.max_seq_length,
        save_dir=args.save_dir
    )

    write_manifest(save_file, write_jsons)

if __name__ == "__main__":
    main()
