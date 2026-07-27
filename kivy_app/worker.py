"""
Kivy-compatible AI evaluation worker.
Uses threading.Thread + Queue instead of PySide6 QThread/QObject.
"""
import json
import threading
from queue import Queue
from functools import partial

from kivy.clock import Clock

from backtranslate.ai.client import call_ai

MAX_RETRIES = 3


class EvaluationWorker:
    """Processes AI evaluation tasks in a background thread."""

    def __init__(self, base_url: str, api_key: str, model: str, prompt_template: str):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.prompt_template = prompt_template
        self.queue: Queue = Queue()
        self._retries: dict[int, int] = {}
        self._running = False
        self._thread: threading.Thread | None = None
        # Callbacks (set by main app)
        self.on_done = None   # callback(eval_id, result_dict)
        self.on_failed = None # callback(eval_id)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def add_task(self, eval_id: int, translation_id: int,
                 user_input: str, official: str, context: str) -> None:
        task = {
            "eval_id": eval_id,
            "translation_id": translation_id,
            "user_input": user_input,
            "official": official,
            "context": context,
        }
        self.queue.put(task)

    def _run_loop(self):
        while self._running:
            try:
                task = self.queue.get(timeout=0.5)
            except Exception:
                continue

            result = call_ai(
                self.base_url, self.api_key, self.model,
                self.prompt_template, task["context"],
                task["user_input"], task["official"],
            )

            eval_id = task["eval_id"]
            if result is not None:
                self._retries.pop(eval_id, None)
                # Schedule UI update on main thread
                if self.on_done:
                    Clock.schedule_once(partial(self._emit_done, eval_id, result))
            else:
                retries = self._retries.get(eval_id, 0) + 1
                if retries <= MAX_RETRIES:
                    self._retries[eval_id] = retries
                    self.queue.put(task)
                else:
                    self._retries.pop(eval_id, None)
                    if self.on_failed:
                        Clock.schedule_once(partial(self._emit_failed, eval_id))

    def _emit_done(self, eval_id, result, dt):
        if self.on_done:
            self.on_done(eval_id, result)

    def _emit_failed(self, eval_id, dt):
        if self.on_failed:
            self.on_failed(eval_id)