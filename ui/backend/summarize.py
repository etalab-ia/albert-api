from openai import OpenAI
import requests
import streamlit as st

from ui import settings


def get_chunks(collection_id: str, document_id: str, api_key: str) -> list:
    response = requests.get(f"{settings.base_url}/chunks/{collection_id}/{document_id}", headers={"Authorization": f"Bearer {api_key}"})
    assert response.status_code == 200, f"{response.status_code} - {response.json()}"
    chunks = response.json()["data"]
    chunks = sorted(chunks, key=lambda x: x["metadata"]["document_part"])

    return chunks


def generate_toc(chunks: list, model: str):
    client = OpenAI(base_url=settings.api_url + "/v1", api_key=st.session_state["user"].api_key)
    text = "\n".join([chunk["content"] for chunk in chunks])

    system_prompt = """Tu es un agent de l'administration française qui fait des synthèses de textes. Tu sais en particulier faire des plans de synthèses. Tu parles en français. Tu ne réponds que des chapitres."""

    user_prompt = f"""
Génère un plan structuré pour une synthèse du texte suivant :

'''
{text}
'''

Instructions :
	•	Le plan doit comporter 2, 3 ou 4 grandes parties.
	•	Uniquement des titres de chapitres (pas de sous-parties).
	•	Les titres doivent être clairs, synthétiques et pertinents par rapport au contenu du texte.
	•	La réponse doit être en français.

Format attendu :
	1.	Titre du premier chapitre
	2.	Titre du deuxième chapitre
	3.	(Éventuellement) Titre du troisième chapitre
	4.	(Éventuellement) Titre du quatrième chapitre

Réponds uniquement avec le plan, pas de commentaires et en français.
"""

    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]

    try:
        response = client.chat.completions.create(model=model, stream=False, temperature=0.2, messages=messages)
    except Exception:
        st.error(body="Generation failed, please try again.")
        st.stop()

    output = response.choices[0].message.content

    return output


def generate_summary(toc: str, chunks: list, model: str):
    client = OpenAI(base_url=settings.api_url + "/v1", api_key=st.session_state["user"].api_key)

    system_prompt = """Tu es un agent de l'administration française qui fait des synthèses de textes. Tu sais en particulier faire des plans de synthèses. Tu parles en français. Tu ne réponds que des chapitres."""
    sumarize_prompt = """Génère un résumé du texte suivant :

{text}

Instructions :
	•	Ne conserve que les éléments importants et pertinents.
	•	Garde les idées générales et les conclusions.
	•	Si des chiffres ou des exemples sont significatifs, inclue-les dans le résumé.
	•	Le résumé doit être clair, concis et structuré.
"""

    merge_prompt = """Fusionne les résumés suivants en une seule synthèse cohérente du document initial :

'''
{text}
'''

Instructions :
    •   Respecte le plan suivant qui t'es donné. 
    •   Structure ta synthèse en utilisant des connecteurs logiques.
	•	Suis rigoureusement le plan suivant:

'''
{toc}
'''
"""
    map_reduce_outputs = []

    progress_text = "✨ Summarizing each chunk... Please wait."
    progress_bar = st.progress(value=0, text=progress_text)

    for i, chunk in enumerate(chunks):
        progress_bar.progress(value=i / len(chunks), text=progress_text)
        prompt = sumarize_prompt.format(text=chunk["content"])
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
        response = client.chat.completions.create(model=model, stream=False, temperature=0.2, messages=messages)
        output = response.choices[0].message.content
        map_reduce_outputs.append(output)

    map_reduce_outputs = merge_prompt.format(text=map_reduce_outputs, toc=toc)
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": map_reduce_outputs}]

    try:
        response = client.chat.completions.create(model=model, stream=False, temperature=0.2, messages=messages)
    except Exception:
        st.error(body="Generation failed, please try again.")
        st.stop()

    progress_bar.empty()

    output = response.choices[0].message.content

    return output


def summary_with_feedback(feedback: str, summary: str, api_key: str, model: str):
    client = OpenAI(base_url=settings.base_url, api_key=api_key)

    system_prompt = """Tu es un agent de l'administration française qui fait des synthèses de textes. Tu sais en particulier faire des plans de synthèses. Tu parles en français. Tu ne réponds que des chapitres."""

    user_prompt = """Je vais te fournir un texte ainsi qu’une consigne de modification. Adapte le texte en respectant strictement cette consigne.

Texte à modifier :

'''
{summary}
'''

Consigne de modification :

'''{feedback}'''

Instructions :
	•	Le texte final doit rester fidèle au texte initial, tout en intégrant la modification demandée.
	•	Conserve la structure et le style du texte d’origine.
	•	La reformulation doit être fluide et naturelle.
"""
    prompt = user_prompt.format(summary=summary, feedback=feedback)
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
    try:
        response = client.chat.completions.create(model=model, stream=False, temperature=0.2, messages=messages)
    except Exception:
        st.error(body="Generation failed, please try again.")
        st.stop()

    output = response.choices[0].message.content

    return output
