# Copyright (c) 2026, NVIDIA CORPORATION.  All rights reserved.
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
# limitations under the License.

"""
Regression test for the document order in the synthetic QA task.

qa.py builds each sample from the gold paragraph followed by distractor
paragraphs and then shuffles them, so the gold paragraph should land at a
different position from sample to sample.
"""

import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


DATA_DIR = Path(__file__).parents[1] / "scripts/data"

# Whitespace tokenizer so the test needs no model files or network access.
STUB_TOKENIZER = '''
class WhitespaceTokenizer:
    def text_to_tokens(self, text):
        return text.split()


def select_tokenizer(tokenizer_type, tokenizer_path):
    return WhitespaceTokenizer()
'''

TEMPLATE = (
    "Answer the question based on the given documents.\n\n{context}\n\n"
    "Question: {query} Answer:"
)


def fake_squad(num_articles=10, paragraphs_per_article=10):
    data = []
    for a in range(num_articles):
        paragraphs = []
        for p in range(paragraphs_per_article):
            code = f"code-{a}-{p}"
            paragraphs.append({
                "context": f"Article {a} paragraph {p} says the secret is {code}.",
                "qas": [{
                    "question": f"What is the secret in article {a} paragraph {p}?",
                    "answers": [{"text": code}],
                    "is_impossible": False,
                }],
            })
        data.append({"title": f"article {a}", "paragraphs": paragraphs})
    return {"version": "v2.0", "data": data}


class QADocumentOrderTests(unittest.TestCase):
    def test_gold_document_position_varies_across_samples(self):
        num_samples = 40
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            synthetic = tmp / "synthetic"
            (synthetic / "json").mkdir(parents=True)
            shutil.copy(DATA_DIR / "synthetic/qa.py", synthetic)
            shutil.copy(DATA_DIR / "synthetic/constants.py", synthetic)
            shutil.copy(DATA_DIR / "manifest_utils.py", tmp)
            (tmp / "tokenizer.py").write_text(STUB_TOKENIZER)
            squad = fake_squad()
            (synthetic / "json/squad.json").write_text(json.dumps(squad))

            subprocess.run(
                [
                    sys.executable, str(synthetic / "qa.py"),
                    "--save_dir", str(tmp / "out"),
                    "--save_name", "qa_1",
                    "--tokenizer_path", "unused",
                    "--tokenizer_type", "hf",
                    "--max_seq_length", "400",
                    "--tokens_to_generate", "32",
                    "--num_samples", str(num_samples),
                    "--dataset", "squad",
                    "--template", TEMPLATE,
                ],
                check=True,
                capture_output=True,
            )
            lines = (tmp / "out/qa_1/validation.jsonl").read_text().splitlines()
            samples = [json.loads(line) for line in lines]

        golds = [p["context"] for d in squad["data"] for p in d["paragraphs"]]
        self.assertEqual(len(samples), num_samples)
        positions = []
        for sample in samples:
            docs = re.findall(r"Document (\d+):\n(.*)", sample["input"])
            self.assertGreater(len(docs), 1)
            gold = golds[sample["index"]]
            hits = [int(i) for i, text in docs if text == gold]
            self.assertEqual(len(hits), 1, sample["index"])
            positions.append(hits[0])

        # The gold paragraph must not sit at one fixed slot in every sample.
        self.assertGreaterEqual(len(set(positions)), num_samples // 4, positions)


if __name__ == "__main__":
    unittest.main()
