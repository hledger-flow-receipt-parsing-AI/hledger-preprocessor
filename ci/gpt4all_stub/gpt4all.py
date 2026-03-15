"""Minimal gpt4all stub for CI — the real gpt4all is a placeholder dependency
that is not used by tests or GIF demos."""


class GPT4All:
    def __init__(self, *args, **kwargs):
        pass

    def generate(self, prompt, **kwargs):
        return "ci_stub"
