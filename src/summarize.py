"""
Local text summarization/insight generation using a small,
free, open-source language model. No API keys, no external LLM
service — keeps the agent fully self-contained and free to run
on every scheduled execution.
"""

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

MODEL_NAME = "google/flan-t5-small"


class Summarizer:
    def __init__(self, model_name=MODEL_NAME):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

    def summarize(self, description, max_new_tokens=40):
        """Generates a one-line 'why this might matter' insight from
        a repo's description, rather than just repeating it verbatim."""
        prompt = (
            f"In one short sentence, explain why a developer might find "
            f"this project interesting: {description}"
        )
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=256)
        outputs = self.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
