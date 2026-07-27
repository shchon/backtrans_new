"""AI evaluation worker -- queue dispatch + AI calls only, no business logic."""

from queue import Queue
from PySide6.QtCore import QObject, QThread, Signal
from backtranslate.ai.client import call_ai

MAX_RETRIES = 3


class EvaluationWorker(QObject):
    evaluation_done = Signal(int, object)   # eval_id, result_dict
    evaluation_failed = Signal(int, str)    # eval_id, error_message

    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue: Queue = Queue()
        self._retries: dict[int, int] = {}

    def add_task(self, eval_id: int, prompt_template: str,
                 context: str, user_input: str, official: str,
                 api_key: str, base_url: str, model: str) -> None:
        self._queue.put({
            "eval_id": eval_id,
            "prompt_template": prompt_template,
            "context": context,
            "user_input": user_input,
            "official": official,
            "api_key": api_key,
            "base_url": base_url,
            "model": model,
        })

    def process_next(self) -> None:
        if self._queue.empty():
            return
        task = self._queue.get()

        error_msg = ""
        try:
            result = call_ai(
                task["base_url"], task["api_key"], task["model"],
                task["prompt_template"], task["context"],
                task["user_input"], task["official"],
            )
        except Exception as e:
            result = None
            error_msg = str(e)

        if result is not None:
            self.evaluation_done.emit(task["eval_id"], result)
            self._retries.pop(task["eval_id"], None)
        else:
            retries = self._retries.get(task["eval_id"], 0) + 1
            if retries <= MAX_RETRIES:
                self._retries[task["eval_id"]] = retries
                self._queue.put(task)
            else:
                self._retries.pop(task["eval_id"], None)
                self.evaluation_failed.emit(task["eval_id"], error_msg)


class EvaluationThread(QThread):
    def __init__(self, worker: EvaluationWorker, parent=None):
        super().__init__(parent)
        self.worker = worker
        self._running = False

    def run(self) -> None:
        self._running = True
        while self._running:
            self.worker.process_next()
            self.msleep(100)

    def stop(self) -> None:
        self._running = False
        self.wait(1000)
