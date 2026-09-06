"""Probe espeak-ng to enumerate the IPA tokens it actually emits per language.

Usage: .venv/bin/python -m scripts.probe_espeak en-us
"""

from __future__ import annotations

import sys
from collections import Counter

from phonemizer.backend import EspeakBackend

sys.path.insert(0, ".")

from app.core.tokenizer import tokenize_ipa  # noqa: E402

WORDS = {
    "en-us": """the think this that there they she measure vision creation pronunciation
language should situation world water fire earth air light night right boy town
cat dog house school teacher student friend family music question answer
birthday breakfast Tuesday Wednesday Thursday Saturday February August October
brother mother father sister children people business science history
""",
    "pt-br": """criação feira pensamento começar educação água fogo terra ar luz noite
cidade casa escola professor aluno amigo família música pergunta resposta
aniversário café manhã terça quarta quinta sábado fevereiro agosto outubro
irmão mãe pai irmã filhos povo negócio ciência história trabalho direito
pão leite livro janela chuva vento sol lua estrela mar rio montanha senhor amanhã gente
""",
    "es": """creación feria pensamiento empezar educación agua fuego tierra aire luz noche
ciudad casa escuela profesor alumno amigo familia música pregunta respuesta
cumpleaños desayuno martes miércoles jueves sábado febrero agosto octubre
hermano madre padre hermana hijos gente negocio ciencia historia trabajo
pan leche libro ventana lluvia viento sol luna estrella mar río montaña
""",
    "de": """Schöpfung Jahrmarkt Gedanke anfangen Bildung Wasser Feuer Erde Luft Licht Nacht
Stadt Haus Schule Lehrer Schüler Freund Familie Musik Frage Antwort
Geburtstag Frühstück Dienstag Mittwoch Donnerstag Samstag Februar August Oktober
Bruder Mutter Vater Schwester Kinder Leute Geschäft Wissenschaft Geschichte
Brot Milch Buch Fenster Regen Wind Sonne Mond Stern Meer Fluss Berg
""",
    "fr-fr": """création foire pensée commencer éducation eau feu terre air lumière nuit
ville maison école professeur élève ami famille musique question réponse
anniversaire mardi mercredi jeudi samedi février août octobre
frère mère père sœur enfants gens commerce science histoire travail
pain lait livre fenêtre pluie vent soleil lune étoile mer rivière montagne
""",
    "it": """creazione fiera pensiero cominciare educazione acqua fuoco terra aria luce notte
città casa scuola professore alunno amico famiglia musica domanda risposta
compleanno colazione martedì mercoledì giovedì sabato febbraio agosto ottobre
fratello madre padre sorella figli gente commercio scienza storia lavoro
pane latte libro finestra pioggia vento sole luna stella mare fiume montagna
""",
    "ru": """создание ярмарка мысль начинать образование вода огонь земля воздух свет ночь
город дом школа учитель ученик друг семья музыка вопрос ответ
день рождения вторник среда четверг суббота февраль август октябрь
брат мать отец сестра дети люди бизнес наука история работа
хлеб молоко книга окно дождь ветер солнце луна звезда море река гора
думать сейчас очень человек язык человек большой маленький новый
""",
}


def main(language: str) -> None:
    backend = EspeakBackend(language, with_stress=True, language_switch="remove-flags")
    words = WORDS.get(language, WORDS["en-us"]).split()
    rows = backend.phonemize(words)
    tokens = [t.ipa for row in rows for t in tokenize_ipa(row) if "(" not in t.ipa and ")" not in t.ipa]
    counts = Counter(tokens)
    print(f"# {language}: {len(counts)} distinct tokens")
    for token, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {token}\t{count}")
    samples = {w: r for w, r in zip(words, rows) if "(" not in r and ")" not in r}
    for w in list(samples)[:6]:
        print(f"#   {w} => {' '.join(t.ipa for t in tokenize_ipa(samples[w]))}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "en-us")
