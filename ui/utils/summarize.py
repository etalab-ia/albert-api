import requests
from openai import OpenAI

from config import BASE_URL


def generate_toc(collection_id: str, document_id: str, api_key: str, model: str):
    response = requests.get(f"{BASE_URL}/chunks/{collection_id}/{document_id}", headers={"Authorization": f"Bearer {api_key}"})
    assert response.status_code == 200, f"{response.status_code} - {response.json()}"
    chunks = response.json()["data"]
    chunks = sorted(chunks, key=lambda x: x["metadata"]["document_part"])
    text = "\n".join([chunk["content"] for chunk in chunks])

    system_prompt = """Tu es un agent de l'administration française qui fait des synthèses de textes. Tu sais en particulier faire des plans de synthèses. Tu parles en français. Tu ne réponds que des chapitres."""

    user_prompt = f"""Tu dois me faire un plan d'une synthèse de texte. Je veux uniquement des chapitres, pas de sous chapitre. 
Voici le texte: \n 
```{text}``` \n 
Réponds en français.
Je veux un plan en 2, 3 ou 4 parties. Donne moi les titres de chaque chapitre. Je veux uniquement des grandes parties, pas de sous partie.
REPONDS EN FRANCAIS
"""

    chat_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    client = OpenAI(base_url=BASE_URL, api_key=api_key)

    chat_response = client.chat.completions.create(model=model, stream=False, max_tokens=3000, top_p=0.9, temperature=0.2, messages=chat_messages)
    output = chat_response.choices[0].message.content

    return output


# def map_reduce_with_toc(
#     text_pdf,
#     plan,
#     api_key=api_key,
#     my_model_name="meta-llama/Meta-Llama-3.1-70B-Instruct",
#     chunk_size=3000,
#     chunk_overlap=100,
# ):
#     llm = ChatOpenAI(
#         openai_api_base=openai_api_base,
#         api_key=openai_api_key,
#         model=my_model_name,
#         temperature=0.5,
#     )

#     text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
#         model_name="gpt-4",
#         chunk_size=chunk_size,
#         chunk_overlap=chunk_overlap,
#     )

#     text_docs_splitted = text_splitter.split_documents([Document(text_pdf)])

#     map_prompt_template = """
#                             <|begin_of_text|><|start_header_id|> system <|end_header_id|>  Tu es un agent de l'administration qui fait des résumés de textes en français.
#                             <|eot_id|>
#                             <|start_header_id|>user<|end_header_id|>
#                             \n Tu dois résumer le texte suivant:
#                             '''{text}'''
#                             \n Ne garde que les éléments importants et pertinents du passage. Concerver les idées générales et les conculsions. Si des chiffres ou exemples te semblent pertinents, conserve les.
#                         <|eot_id|><|start_header_id|>assistant<|end_header_id|>
#                         """

#     map_prompt = PromptTemplate(template=map_prompt_template, input_variables=["text"])

#     combine_prompt_template = (
#         """
#                         <|begin_of_text|><|start_header_id|> system <|end_header_id|> Tu es un agent de l'administration qui fait des synthèses de textes.
#                         <|eot_id|>
#                         <|start_header_id|>user<|end_header_id|>

#                         Voici plusieurs textes qui sont des résumés d'un seul document. Tu dois synthétiser ces textes pour obtenir une seule synthèse du document initial.
#                         Voici les textes : \n
#                         ```{text}``` \n
#                         Sois complet et réponds suis bien le plan qui t'as été donné.
#                         Structurer ta synthèse. Utilise des connecteurs logiques. Si des chiffres ou exemples te semblent pertinents, conserve les.
#                         Ta synthèse dois suivre le plan suivant:
#                         """
#         + plan
#         + """


#                         <|eot_id|>
#                         <|start_header_id|>assistant<|end_header_id|>
#                         """
#     )

#     combine_prompt = PromptTemplate(template=combine_prompt_template, input_variables=["text"])

#     map_reduce_chain = load_summarize_chain(
#         llm,
#         chain_type="map_reduce",
#         map_prompt=map_prompt,
#         combine_prompt=combine_prompt,
#         # return_intermediate_steps=True,
#     )

#     map_reduce_outputs = map_reduce_chain(text_docs_splitted)

#     return map_reduce_outputs["output_text"]


# def maj_summary_RAG(
#     retour_utilisateur,
#     resume,
#     retrieved_doc,
#     openai_api_base=base_url,
#     openai_api_key=api_key,
#     my_model_name="meta-llama/Meta-Llama-3.1-70B-Instruct",
# ):
#     llm = ChatOpenAI(
#         openai_api_base=openai_api_base,
#         api_key=openai_api_key,
#         model=my_model_name,
#         temperature=0.5,
#     )

#     concatenated_retrieved_doc = " \n ".join([doc.page_content for doc in retrieved_doc])

#     harmonisation_prompt_template = """
#                         <|begin_of_text|><|start_header_id|>system<|end_header_id|>\n
#                         Tu es un agent de l'administration qui rédige des textes dans un français parfait et avec une grande maîtrise de la rédaction.
#                         <|eot_id|>\n\n
#                         <|start_header_id|>user<|end_header_id|>
#                         Je vais te donner un texte et je souhaite que tu le MODIFIE. Tu ne dois pas le remplacer mais uniquement rajouter des choses en respectant une demande que je te donnerais après.
#                         \n Voici un texte :
#                         '''{resume}'''
#                         \n

#                         Voici la demande que j'ai sur ce texte :
#                         '''{retour_utilisateur}'''. \n
#                         Tu dois donc le modifier pour qu'il corresponde à cette. Pour ceci, voici des éléments que tu peux utiliser :

#                         '''{concatenated_retrieved_doc}''' \n
#                         Tu dois donc le modifier pour qu'il corresponde à ce retour. Le texte soumis dois être conforme au texte de base mais respecter la modification demandée.
#                         Le texte dois garder la même structure.  REPOND EN FRANCAIS;


#                         <|eot_id|>
#                         \n\n<|start_header_id|>assistant<|end_header_id|>
#                         """

#     harmonisation_prompt = PromptTemplate(
#         template=harmonisation_prompt_template, input_variables=["resume", "retour_utilisateur", "concatenated_retrieved_doc"]
#     )

#     output_parser = StrOutputParser()

#     chain = harmonisation_prompt | llm | output_parser

#     output = chain.invoke({"resume": resume, "retour_utilisateur": retour_utilisateur, "concatenated_retrieved_doc": " coucou"})

#     return output


# def maj_summary_noRAG(
#     retour_utilisateur, resume, openai_api_base=base_url, openai_api_key=api_key, my_model_name="meta-llama/Meta-Llama-3.1-70B-Instruct"
# ):
#     llm = ChatOpenAI(
#         openai_api_base=openai_api_base,
#         api_key=openai_api_key,
#         model=my_model_name,
#         temperature=0.5,
#     )

#     harmonisation_prompt_template = """
#                         <|begin_of_text|><|start_header_id|>system<|end_header_id|>\n
#                         Tu es un agent de l'administration qui rédige des textes dans un français parfait et avec une grande maîtrise de la rédaction.
#                         <|eot_id|>\n\n
#                         <|start_header_id|>user<|end_header_id|>
#                         \n Je vais te donner un texte que tu devras modifier en respectant une consigne d'un utilisateur. Voici le texte en question :
#                         '''{resume}'''
#                         \n
#                         Voici la consigne que tu dois réaliser. Modifie le texte pour répondre à la consigne.
#                         '''{retour_utilisateur}'''. \n
#                         Le texte soumis dois être conforme au texte de base mais respecter la modification demandée.
#                         Le texte dois garder la même structure.

#                         <|eot_id|>
#                         \n\n<|start_header_id|>assistant<|end_header_id|>
#                         """
#     harmonisation_prompt = PromptTemplate(
#         template=harmonisation_prompt_template, input_variables=["resume", "retour_utilisateur", "concatenated_retrieved_doc"]
#     )

#     output_parser = StrOutputParser()

#     chain = harmonisation_prompt | llm | output_parser

#     output = chain.invoke({"resume": resume, "retour_utilisateur": retour_utilisateur})

#     return output


# def extract_json(text):
#     # Utiliser une expression régulière pour trouver le contenu entre accolades
#     # Cette version gère les imbrications jusqu'à une profondeur de 5 niveaux
#     pattern = r"\{(?:[^{}]|\{(?:[^{}]|\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\})*\})*\}"
#     match = re.search(pattern, text)

#     if match:
#         json_string = match.group(0)
#         try:
#             # Tenter de parser le JSON pour vérifier sa validité
#             json_object = json.loads(json_string)
#             return json_string
#         except json.JSONDecodeError:
#             return "JSON invalide trouvé"
#     else:
#         return "Aucun JSON trouvé"


# def classifier_RAG(retour_utilisateur, openai_api_base=base_url, openai_api_key=api_key, my_model_name="meta-llama/Meta-Llama-3.1-70B-Instruct"):
#     prompt_systeme = (
#         """Tu es un agent intermédiaire qui doit classifier les besoins d'un utilisateur qui demande des modifications sur un texte généré. """
#     )

#     prompt_user_template = f"""Un utilisateur fais des retours sur un résumé de texte qui a été généré.
#                             Je vais te donner son retour et tu vas me dire si l'utilisateur à besoin
#                             d'informations supplémentaires dans son résumé. Voici le retour de l'utilisateur : \n
#                             ```{retour_utilisateur}``` \n

#                             Détermine si l'utilisateur à besoin de rajouter des informations dans le résumé qui a été généré.

#                             Si oui, dis moi les informations clairement dont l'utilisateur à besoin ET UNIQUEMENT CELA.
#                             Ne me Repond QUE L'INFORMATION DEMANDEE. Répond sous forme d'un json avec comme clé : 'information_demandée'.
#                             Ne répond QU'AVEC UN JSON.
#                             Si le retour de l'utilisateur ne demande pas d'information supplémentaire mais fait un retour sur le style, la taille, des informations à enlever, des informations à réduire ou tout autre demande, REPOND 'False'
#                             Je ne veux qu'un json en sortie, exemple :
#                             Si besoin d'information :

#                             '''{{"information_demandée": "Ici mettre les informations demandées"}}```

#                             Si pas besoin d'information :

#                             ```{{"information_demandée": "False"}}```

#                             TU NE DOIS RENVOYER QU'UN FORMAT JSON.
#                             Exemple de réponse:
#                             ```{{"information_demandée": "False"}}```
#                             '''{{"information_demandée": "Ici mettre les informations demandées"}}```

#                             """

#     chat_messages = [
#         {"role": "system", "content": prompt_systeme},
#         {"role": "user", "content": prompt_user_template},
#     ]

#     client = OpenAI(base_url=base_url, api_key=api_key)

#     # stream chat.completions
#     chat_response = client.chat.completions.create(
#         model=my_model_name,  # this must be the model name the was deployed to the API server
#         #    stream=True,
#         max_tokens=1000,
#         top_p=0.9,
#         temperature=0.1,
#         messages=chat_messages,
#     )
#     output = chat_response.choices[0].message.content
#     return output
