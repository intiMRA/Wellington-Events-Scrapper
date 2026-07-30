from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer  # Or LsaSummarizer, TextRankSummarizer, etc.
import nltk


def sumerize(description) -> str:
    try:
        nltk.data.find('tokenizers/punkt')
    except:
        nltk.download('punkt')

    parser = PlaintextParser.from_string(description, Tokenizer("english"))
    summarizer = LexRankSummarizer()
    summary_sentences = summarizer(parser.document, sentences_count=5)

    return "\n".join([str(sentence) for sentence in summary_sentences])
