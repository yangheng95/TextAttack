"""
universal sentence encoder class
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
"""

from textattack.constraints.semantics.sentence_encoders import SentenceEncoder
from textattack.shared.utils import LazyLoader

hub = LazyLoader("tensorflow_hub", globals(), "tensorflow_hub")


class UniversalSentenceEncoder(SentenceEncoder):
    """Constraint using similarity between sentence encodings of x and x_adv
    where the text embeddings are created using the Universal Sentence
    Encoder."""

    def __init__(self, threshold=0.8, large=False, metric="angular", **kwargs):
        super().__init__(threshold=threshold, metric=metric, **kwargs)
        if large:
            tfhub_url = "https://tfhub.dev/google/universal-sentence-encoder-large/5"
            mirror_tfhub_url = "https://hub.tensorflow.google.cn/google/universal-sentence-encoder-large/5"
        else:
            tfhub_url = "https://tfhub.dev/google/universal-sentence-encoder/4"
            mirror_tfhub_url = (
                "https://hub.tensorflow.google.cn/google/universal-sentence-encoder/4"
            )

        self._tfhub_url = tfhub_url
        self.mirror_tfhub_url = mirror_tfhub_url
        # Lazily load the model
        self.model = None

    def encode(self, sentences):
        if not self.model:
            try:
                self.model = hub.load(self._tfhub_url)
            except Exception as e:
                print(
                    "Error loading model from tfhub, trying mirror url. Exception: ", e
                )
                self.model = hub.load(self.mirror_tfhub_url)
        return self.model(sentences).numpy()

    def __getstate__(self):
        state = self.__dict__.copy()
        state["model"] = None
        return state

    def __setstate__(self, state):
        self.__dict__ = state
        try:
            self.model = hub.load(self._tfhub_url)
        except Exception as e:
            print("Error loading model from tfhub, trying mirror url. Exception: ", e)
            self.model = hub.load(self.mirror_tfhub_url)
