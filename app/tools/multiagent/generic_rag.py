import pandas as pd
from tqdm import tqdm
from sklearn.feature_extraction.text import TfidfVectorizer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.document_loaders import DataFrameLoader
from nltk.corpus import stopwords
import numpy as np

from openai import OpenAI

API_KEY = "multivac-FQ1cWX4DpshdhkXY2m"
MODEL_URL = "http://llama38b.multivacplatform.org/v1"
client = OpenAI(api_key=API_KEY, base_url=MODEL_URL)
models = [model.id for model in client.models.list()]
 
french_stopwords = set(stopwords.words("french"))
new_stopwords = {
    "s'",
    "quel",
    "que",
    "quoi",
    "comment",
    "l'",
    "d'",
    "mais",
    "ou",
    "et",
    "donc",
    "or",
    "ni",
    "car",
    "quelle",
    "quelles",
    "pourquoi",
}
french_stopwords.update(new_stopwords)


def get_prompt_potential_questions(text):
    prompt = f"""
<|system|> Tu parles en Français
<|end|>
<|user|>
Voilà un texte : {text}
En utilisant le contenu du texte fourni, crée deux questions spécifique mais pas trop longue dont la réponse est clairement indiquée dans le texte. Assure-toi que la question n'est pas vague et qu'elle peut être facilement associée au texte, même parmi d'autres questions portant sur d'autres textes. Si le texte est simple, la question peut être simple aussi. Voici quelques exemples pour te guider :

Exemple de mauvaises questions à éviter : ["De quoi parle ce texte ?", "Qui est mentionné ici ?"] (trop vague)
Exemple de bonne question : ["Quel département est affecté par la politique XX-XXX-XX ?"] (précise et claire)
Génères uniquement des questions et non leurs réponses.
Formattes ta réponse en une liste Python contenant deux questions spécifiques sur le texte ci-dessus.
Format de réponse attendu : [ "{{question1}}", "{{question2}}" ]
Réponds uniquement avec la liste de questions et rien d'autre.
<|end|>\n<|assistant|>
"""
    return prompt


def get_potential_question(text):
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": get_prompt_potential_questions(text),
            }
        ],
        model=models[0],
        temperature=0.2,
        stream=False,
    )
    answer = chat_completion.choices[0].message.content
    return answer


def remove_french_stopwords(text):
    text = text.lower()
    tokens = text.split()  # Split text into words
    filtered_tokens = [token for token in tokens if token.lower() not in french_stopwords]
    return " ".join(filtered_tokens)


def extract_keywords_tfidf(docs, corpus, top_n=5):
    """
    Extracts the top N keywords from a given document or list of documents using TF-IDF.
    Parameters:
    - docs (str or list of str): A single document or a list of documents.
    - top_n (int): Number of top keywords to extract from each document.
    Returns:
    - list of (str, float) tuples: A list of (keyword, score) tuples for each document.
    """
    if isinstance(docs, str):
        docs = [docs]
    # Initialize the TF-IDF vectorizer
    vectorizer = TfidfVectorizer(stop_words=list(french_stopwords))
    # Fit and transform the documents
    model = vectorizer.fit(corpus)  #
    tfidf_matrix = model.transform(docs)
    # Get feature names to access the corresponding columns in the matrix
    feature_names = np.array(vectorizer.get_feature_names_out())
    # Initialize a list to hold the results
    keywords_list = []
    # Iterate through each document
    for doc_idx in range(tfidf_matrix.shape[0]):
        # Get the row corresponding to the document
        row = np.squeeze(tfidf_matrix[doc_idx].toarray())
        # Get the indices of the top N values
        top_n_indices = row.argsort()[-top_n:][::-1]
        # Extract the corresponding keywords and scores
        keywords = [
            feature_names[i] for i in top_n_indices
        ]  # [(feature_names[i], row[i]) for i in top_n_indices]
        # Add to the list of results
        keywords_list.append(keywords)
    # If only one document was processed, return its keywords directly
    if len(docs) == 1:
        return keywords_list[0]
    return keywords_list


def create_rag_df(df, text_col, metadata_cols, chunk_size=3500):
    # Make a document list with every columns we could need in the metadatas
    df_loader = DataFrameLoader(
        df[[text_col] + metadata_cols], page_content_column=text_col
    )  #'_clean'
    df_document = df_loader.load()
    # Slipt document in chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=50,
        length_function=len,
        separators=["\n\n", ". "],
    )
    baseline_docs = text_splitter.split_documents(df_document)

    chunk_ids = []
    chunk_contents = []
    chunk_metadatas = []
    # Add a chunk_id and potential questions to metadatas
    # llm = load_llm(model_path=model_path)
    for i, doc in tqdm(
        enumerate(baseline_docs), total=len(baseline_docs), desc="Processing documents"
    ):
        if len(doc.page_content) <= chunk_size:
            doc.metadata["chunk_id"] = i
            doc.metadata["potential_questions"] = get_potential_question(doc.page_content)

            # print(doc.metadata['potential_questions'])
            chunk_ids.append(i)
            chunk_contents.append(doc.page_content)
            chunk_metadatas.append(doc.metadata)

    df_chunks = pd.DataFrame()
    # df_chunks["chunk_id"] = chunk_ids
    df_chunks["chunk_content"] = chunk_contents
    df_chunks["chunk_metadata"] = chunk_metadatas

    # Recreate the columns from metadatas
    metadata_df = df_chunks["chunk_metadata"].apply(pd.Series)
    df_chunks = pd.concat([df_chunks.drop(columns=["chunk_metadata"]), metadata_df], axis=1)
    return df_chunks
