import unittest

from athena.assistant import Athena
from athena.storage import Storage
from athena.tools import _extract_article, build_tools
from athena.speech import prepare_for_speech


def test_article_extraction_returns_clean_metadata():
    article = _extract_article("https://example.com/news/1", "<html><title>AI News</title><article><p>Hello technology world.</p></article></html>")
    assert article["title"] == "AI News"
    assert "Hello technology world" in article["text"]


def test_speech_cleanup_removes_urls_and_symbols():
    spoken = prepare_for_speech("News — [AI update] https://example.com/a?id=1 🚀")
    assert spoken == "News AI update"


class AssistantTests(unittest.TestCase):
    def make_assistant(self):
        return Athena(build_tools(Storage(":memory:")))


    def test_task_creation_requires_confirmation(self):
        assistant = self.make_assistant()
        self.assertIn("confirm", assistant.handle("add task Buy milk").lower())
        self.assertIn("done", assistant.handle("yes").lower())
        self.assertIn("Buy milk", assistant.handle("show my tasks"))


    def test_cancel_does_not_create_task(self):
        assistant = self.make_assistant()
        assistant.handle("add task Secret task")
        self.assertEqual(assistant.handle("cancel"), "Cancelled.")
        self.assertIn("no tasks", assistant.handle("show my tasks").lower())


    def test_unknown_command_is_safe(self):
        assistant = self.make_assistant()
        self.assertIn("don’t know", assistant.handle("send all my money").lower())


if __name__ == "__main__":
    unittest.main()
