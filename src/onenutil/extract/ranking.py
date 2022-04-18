from dataclasses import dataclass
from math import sqrt
from typing import List

import pytextrank
import spacy
from ..schemas import TagResult




class TagExtractor:
    """Extract the tags from the text. Also produce the summary."""
    def __init__(self, limit_phrases: int = 4, limit_sentences: int = 3) -> None:
        self.nlp = self.__initialise_spacy()
        self.limit_phrases = limit_phrases 
        self.limit_sentences = limit_sentences

    def __initialise_spacy(self):
        nlp = spacy.load("en_core_web_sm")
        # add PyTextRank to the spaCy pipeline
        nlp.add_pipe("textrank")
        return nlp 

    def __call__(self, text: str) -> TagResult:
        doc = self.nlp(text)
        tags = self.extract_tags(doc)
        summary = self.extract_summary(doc)
        return TagResult(tags, summary)

    def extract_tags(self, doc) -> List[str]:
        # examine the top-ranked phrases in the document
        phrases = [phrase.text for phrase in doc._.phrases]
        return phrases[:self.limit_phrases]

    def extract_summary(self, doc) -> List[str]:
        sent_bounds = [[s.start, s.end, set([])] for s in doc.sents]
        unit_vector = []
        # the ._._phrases should've been sorted by score
        for phrase_id, p in enumerate(doc._.phrases):
            unit_vector.append(p.rank)
            for chunk in p.chunks:
                for sent_start, sent_end, sent_vector in sent_bounds:
                    if chunk.start >= sent_start and chunk.end <= sent_end:
                        sent_vector.add(phrase_id)
                        break
            if phrase_id == self.limit_phrases:
                break
        sum_ranks = sum(unit_vector)
        unit_vector = [ rank/sum_ranks for rank in unit_vector ]
        sent_rank = {}
        sent_id = 0
        for sent_start, sent_end, sent_vector in sent_bounds:
            sum_sq = 0.0
            for phrase_id in range(len(unit_vector)):
                if phrase_id not in sent_vector:
                    sum_sq += unit_vector[phrase_id]**2.0

            sent_rank[sent_id] = sqrt(sum_sq)
            sent_id += 1

        sent_rank = sorted(sent_rank.items(), key=lambda x: x[1], reverse=True)
        all_sents = list(doc.sents)
        sent_text = {
            sent_id: all_sents[s_id[0]].text
            for s_id in sent_rank[:self.limit_sentences]
        }
        return list(sent_text.values())



