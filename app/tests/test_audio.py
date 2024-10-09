from openai import OpenAI
import requests

with open('audio.mp3', 'wb') as fopen:
    r = requests.get('https://huggingface.co/datasets/huseinzol05/temp-storage/resolve/main/Lex-Fridman-on-Grigori-Perelman-turning-away-1million-and-Fields-Medal.mp3?download=true')
    fopen.write(r.content)
  
client = OpenAI(
    api_key='jules-f0b946fa-0da4-4500-a536-e4fb7448d6bc',
    base_url = 'http://127.0.0.1:8080'
)

audio_file = open("audio.mp3", "rb")
transcript = client.audio.transcriptions.create(
  file=audio_file,
  model="Systran/faster-distil-whisper-large-v3",
  response_format="json",
  #timestamp_granularities="segment"
)

print(transcript)
