

def generate_embedding(embedding_model, text: str) -> list:
    """
    Generate embedding vector for given text using embedding_model.
    """
    # TODO: Implement actual embedding generation logic
    return embedding_model.embed(text)  # Should return a list of floats