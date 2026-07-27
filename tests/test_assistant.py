import unittest

from athena.assistant import Athena
from athena.storage import Storage
from athena.tools import build_tools


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
