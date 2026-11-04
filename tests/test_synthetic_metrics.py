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
# limitations under the License.

"""
Regression tests for the synthetic benchmark metrics.
"""

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).parents[1] / "scripts/eval/synthetic/constants.py"
SPEC = importlib.util.spec_from_file_location("synthetic_constants", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class SyntheticMetricTests(unittest.TestCase):
    def test_string_match_part_requires_word_boundaries(self):
        self.assertEqual(MODULE.string_match_part(["No"], [["no"]]), 100.0)
        self.assertEqual(MODULE.string_match_part(["I do not know"], [["no"]]), 0.0)
        self.assertEqual(MODULE.string_match_part(["The answer is Norway"], [["no"]]), 0.0)


    def test_string_match_all_preserves_phrase_containment(self):
        self.assertEqual(MODULE.string_match_all(["New York"], [["York"]]), 100.0)
        self.assertEqual(MODULE.string_match_all(["Yorkshire"], [["York"]]), 0.0)
