import re
import dotenv
import os
from openai import OpenAI

from .prompts import *
from .retrieval import search_db, find_official_sources, create_web_collection, search_tmp_rag

dotenv.load_dotenv(".env")
LLAMA_URL = os.getenv("LLAMA_URL")
MISTRAL_URL = os.getenv("MISTRAL_URL")
LLAMA_API_KEY = os.getenv("LLAMA_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

open_client_llama = OpenAI(api_key=LLAMA_API_KEY, base_url=LLAMA_URL)
model_llama = [model.id for model in open_client_llama.models.list()][0]

open_client_mistral = OpenAI(api_key=MISTRAL_API_KEY, base_url=MISTRAL_URL)
model_mistral = [model.id for model in open_client_mistral.models.list()][0]


def extract_number(string):
    # string = string.strip()
    match = re.search(r"\b[0-4]\b", string)
    if match:
        return int(match.group())
    else:
        return None  # or handle the case when no number is found


def get_ragger_choice(question, docs, error=0):
    chat_completion = open_client_mistral.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": get_prompt_ragger(question, docs),
            }
        ],
        model=model_mistral,
        temperature=0.1,
        max_tokens=3,
        stream=False,
    )

    answer = chat_completion.choices[0].message.content

    try:
        answer = int(extract_number(answer))
        return answer
    except:
        error += 1
        print(f"oups [pas un int][{answer}]")
        if error >= 3:
            print("damn")
            return 0
        else:
            return get_ragger_choice(question, docs, error=error)


def get_teller_answer(question, context, choice):
    prompt = get_prompt_teller(question, context, choice)

    chat_completion = open_client_llama.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model=model_llama,
        temperature=0.3,
        top_p=0.9,
        stream=False,
    )

    answer = chat_completion.choices[0].message.content

    return answer


def get_checker_answer(question, response, refs):
    chat_completion = open_client_llama.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": get_prompt_checker(question, response, refs),
            }
        ],
        model=model_llama,
        temperature=0.5,
        top_p=0.9,
        stream=False,
    )

    answer = chat_completion.choices[0].message.content

    return answer


def get_googleizer_answer(question):
    chat_completion = open_client_llama.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": get_prompt_googleizer(question),
            }
        ],
        model=model_llama,
        temperature=0.2,
        stream=False,
    )

    answer = chat_completion.choices[0].message.content

    return answer


def get_teller_answer(question, context, choice):
    prompt = get_prompt_teller(question, context, choice)

    chat_completion = open_client_llama.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model=model_llama,
        temperature=0.3,
        stream=False,
    )

    answer = chat_completion.choices[0].message.content

    return answer


def get_final_answer(question, answers, history):
    prompt = get_prompt_concat_answer(answers, question)
    chat_completion = open_client_llama.chat.completions.create(
        messages=history[-2:]
        + [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model=model_llama,
        temperature=0.2,
        max_tokens=1024,
        stream=False,
    )
    answer = chat_completion.choices[0].message.content
    return answer


def get_list_web_sources(question):
    results = find_official_sources(question, n=5)
    results = "\n".join(
        [
            f"""• :url_start:{site['title']} ---- {site['href']}:url_end:\nExtrait : "{site['body']}"\n"""
            for site in results
        ]
    )
    answer = f"Voilà ce que j'ai trouvé sur internet parmi les sources officielles de l'État :\n\n{results}"
    return answer


async def teller_multi_stuffs(prompts, history):
    async def multivac_batch_completions(prompts):
        # test simple list
        batch = open_client_llama.completions.create(
            model=model_llama,  # this must be the model name the was deployed to the API server
            stream=False,
            max_tokens=400,
            top_p=0.9,
            temperature=0.1,
            prompt=prompts,
        )
        # batch = open_client_llama.chat.completions.create(
        #    messages=history + {"role":"user", "content":prompt}
        return batch

    # prompts_list = [f"<|user|>{prompt}<|end|>\n<|assistant|>" for prompt in prompts]
    prompts_list = [
        " ".join([f"<|{x['role']}|>{x['content']}<|end|>\n" for x in history[-2:]])
        + f"<|user|>{prompt}<|end|>\n<|assistant|>"
        for prompt in prompts
    ]

    results = await multivac_batch_completions(prompts_list)
    answers = [res.text for res in results.choices]
    return answers


# Pipeline recursif
async def go_pipeline(question, docs=[], refs=[], n=0, fact=5, history=None):
    # print(history)
    if docs == []:
        # print(f"Trying with {fact} firsts docs")
        docs, refs = search_db(question, k=25)  # Get docs a first time
        docs_tmp = docs[:fact]
        refs_tmp = refs[:fact]
    else:
        # print(f"Retrying with following docs {n*fact}->{(n*fact)+fact}")
        docs_tmp = docs[n * fact : (n * fact) + fact]
        refs_tmp = refs[n * fact : (n * fact) + fact]

    if len(docs) > 0:
        context = "\n-------\n".join(docs_tmp[:fact])
        context_refs = refs_tmp[:fact]  # "\n".join(refs_tmp[:fact])
    else:
        context = ""

    print("CONTEXT")
    print(context)
    print("END CONTEXT")
    if question.lower().strip().startswith("web") or question.lower().strip().startswith(
        "internet"
    ):
        choice = 4  # web search
    else:
        choice = get_ragger_choice(question, context)
    print("CHOIX: ", choice)
    print(f"[{peter_explain[choice]}]")

    if choice in [0, 3] and len(docs) >= 1 and n < 3 and (((n * fact) + fact) < len(docs)):
        print(f"retest {n}")
        n += 1
        return await go_pipeline(
            question,
            docs=docs,
            refs=refs,
            n=n,
            fact=fact,
            history=history,
        )
    if choice in [1, 2]:
        # print(context)
        # print("LEN DOCS", len(docs_tmp))
        prompts = get_prompt_teller_multi(
            question, docs_tmp, choice
        )  # get_teller_answer(question, docs_tmp, choice)
        answers = await teller_multi_stuffs(prompts, history)
        # print("-- Every answer for now --")
        # print(answers)
        # print("-- End   answer for now --")
        answer = get_final_answer(question, answers, history)

        # Adding refs
        if choice == 1:
            ref_answer = get_checker_answer(question, answer, "\n".join(context_refs))
        else:
            ref_answer = "🤖"  # "Je n'ai pas utilisé de sources pour cette réponse."
    if choice == 4 or n == 3:  # too much retry ? go internet
        choice = 4
        google_search = get_googleizer_answer(question)
        print(question, "---->", google_search)
        web_results = find_official_sources(google_search)
        print("WEB RESULTS", web_results)
        if web_results == []:
            answer = "Désolé je n'ai rien trouvé à ce sujet, ni dans les documents de l'État, ni sur internet !"
            ref_answer = ""
            return answer, ref_answer
        print("Je classe ça...")
        create_web_collection(web_results)
        print("Je regarde ça...")
        docs_tmp = search_tmp_rag(question)
        print(docs_tmp)
        print("Je lis tout ça...")
        prompts = get_prompt_teller_multi(question, docs_tmp, choice)
        print("prompt: ", prompts)
        print("Je parle avec des potes...")
        answers = await teller_multi_stuffs(prompts, history)
        answer = get_final_answer(question, answers, history)

        # ref_answer = '- '+'\n- '.join([stuff['href'] for stuff in web_results])
        ref_answer = "\n".join(
            [
                f"""• :url_start:{site['title']} ---- {site['href']}:url_end:\nExtrait : "{site['body']}"\n"""
                for site in web_results
            ]
        )

    elif choice == 0 or (choice == 3):
        context = ""
        context_refs = ""
        answer = f"Je n'ai pas compris la question, désolé. {peter_explain[choice]}"
        ref_answer = ""
    # print(choice, n)
    # print(f"Question: {question}")
    # print(f"Answer:\n{answer}")
    return answer, ref_answer
