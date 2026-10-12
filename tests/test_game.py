"""Dependency-free regression tests for the original AWS terminal quiz."""
import io
import pathlib
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
import game

class ScoringTests(unittest.TestCase):
    def test_percent_not_fraction(self):
        self.assertEqual(game.score_percentage(1, 2), 50)
        self.assertEqual(game.score_percentage(3, 4), 75)
        self.assertEqual(game.score_percentage(2, 2), 100)
    def test_empty_quiz(self):
        self.assertEqual(game.score_percentage(0, 0), 0)
        with patch.object(game, "prepare_questions", return_value=[]):
            with redirect_stdout(io.StringIO()) as out:
                game.run_quiz()
        self.assertIn("0 out of 0", out.getvalue())
        self.assertIn("(0%)", out.getvalue())
    def test_half_correct_prints_fifty_percent(self):
        questions = [{"question": "Q", "answers": ["Y"], "alternatives": ["N"]}] * 2
        with patch.object(game, "prepare_questions", return_value=questions):
            with patch.object(game, "ask_question", side_effect=[1, 0]):
                with redirect_stdout(io.StringIO()) as out:
                    game.run_quiz()
        self.assertIn("1 out of 2 questions correctly! (50%)", out.getvalue())

class BankTests(unittest.TestCase):
    def test_bundled_toml_parses(self):
        data = game.tomllib.loads(game.QUESTIONS_PATH.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["aws"]["questions"]), 20)
        for q in data["aws"]["questions"]:
            self.assertTrue(q["question"].strip())
            self.assertTrue(q["answers"])
            self.assertTrue(q["alternatives"])
    def test_sample_count_and_cap(self):
        with patch.object(game, "get_answers", return_value=["AWS Cloud Essentials"]):
            self.assertEqual(len(game.prepare_questions(game.QUESTIONS_PATH, 8)), 8)
            self.assertEqual(len(game.prepare_questions(game.QUESTIONS_PATH, 999)), 26)
    def test_empty_bank_explains_problem(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / "questions.toml"
            p.write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "no available topics"):
                game.prepare_questions(p, 5)

class InteractionTests(unittest.TestCase):
    def test_select_answer_by_letter(self):
        with patch("builtins.input", return_value="b"), redirect_stdout(io.StringIO()):
            self.assertEqual(game.get_answers("Pick", ["No", "Yes"]), ["Yes"])
    def test_reprompt_invalid_letter(self):
        with patch("builtins.input", side_effect=["z", "a"]):
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(game.get_answers("Pick", ["Yes", "No"]), ["Yes"])
        self.assertIn("not a valid choice", out.getvalue())
    def test_hint_does_not_count_as_answer(self):
        with patch("builtins.input", side_effect=["?", "b"]):
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(game.get_answers("Pick", ["No", "Yes"], hint="Consider this"), ["Yes"])
        self.assertIn("HINT: Consider this", out.getvalue())
    def test_multiple_unique_answers(self):
        with patch("builtins.input", side_effect=["a,a", "a,c"]), redirect_stdout(io.StringIO()):
            self.assertCountEqual(game.get_answers("Pick two", ["A", "B", "C"], num_choices=2), ["A", "C"])
    def test_correct_incorrect_and_explanation(self):
        q = {"question": "Choose", "answers": ["Right"], "alternatives": ["Wrong"], "explanation": "Because"}
        with patch.object(game, "get_answers", return_value=["Right"]), redirect_stdout(io.StringIO()):
            self.assertEqual(game.ask_question(q), 1)
        with patch.object(game, "get_answers", return_value=["Wrong"]):
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(game.ask_question(q), 0)
        self.assertIn("EXPLANATION:", out.getvalue())

if __name__ == "__main__":
    unittest.main()
