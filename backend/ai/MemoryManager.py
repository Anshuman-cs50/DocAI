from typing import List, Any

def format_timeline_as_messages(timeline_entries: List[Any]) -> List[dict]:
    """
    Converts ConsultationTimeline entries into standard HuggingFace Chat Template messages.
    Returns:
       [
          {"role": "user", "content": "hello"},
          {"role": "assistant", "content": "hi"}
       ]
    """
    messages = []
    for entry in timeline_entries:
        if entry.user_query:
            messages.append({"role": "user", "content": entry.user_query})
        if entry.model_response:
            # HuggingFace standard usually uses 'assistant' or 'model' depending on the template
            # Standard OpenAI uses 'assistant', Gemma supports 'model'. We'll use 'model' 
            # as it maps to MedGemma's standard, but Kaggle script handles role translation.
            messages.append({"role": "model", "content": entry.model_response})
    return messages

