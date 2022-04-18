from sentence_transformers import SentenceTransformer
from ..schemas import EmbeddingsResult

class EmbeddingsExtractor:
    def __init__(self, model_name: str = 'paraphrase-MiniLM-L6-v2') -> None:
        """Initialise the model
        :param model_name: the name of the model to use. From sentence embeddings library
        """
        self.model_name = model_name
        self.model = self.__initialise_model(model_name=model_name) 


    def __initialise_model(self, model_name):
        model = SentenceTransformer(f'sentence-transformers/{model_name}')
        return model 
        

    def __call__(self, text) -> EmbeddingsResult:
        embeddings = self.model.encode(text)

        return EmbeddingsResult(
            embedding=embeddings,
            model_name=self.model_name
        )

