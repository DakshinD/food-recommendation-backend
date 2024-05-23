# -*- coding: utf-8 -*-
import nltk
from nltk.corpus import stopwords
from nltk.corpus import wordnet

from scraper.scraper import *



def findFoodNouns(reviews):
    food_nouns = set()
    
    for review in reviews:
        # tokenize
        tokens = nltk.word_tokenize(review)

        # remove stop words
        stop_words = set(stopwords.words('english'))
        filtered_tokens = [w for w in tokens if not w.lower() in stop_words]
        #print(filtered_tokens)

        # Part of speech tagging --> need to filter for only nouns
        tokens_with_POS = nltk.pos_tag(filtered_tokens)
        types_of_nouns = ["NN", "NNS", "NNP", "NNPS"]
        noun_tokens = list(filter(lambda pair: pair[1] in types_of_nouns, tokens_with_POS))

        # check if noun is a word
        def if_food(word):

            syns = wordnet.synsets(str(word), pos = wordnet.NOUN)

            for syn in syns:
                if 'food' in syn.lexname():
                    return (1, word)
            return (0, word)

        for word in noun_tokens:
            if if_food(word[0])[0]:
                food_nouns.add(word[0].lower())
    return list(food_nouns)

def findFoodNounsWithNER(reviews):
    food_nouns = []
    all_food_nouns_found = []

    # initialize transformer model
    from transformers import AutoTokenizer, AutoModelForTokenClassification
    from transformers import pipeline
    tokenizer = AutoTokenizer.from_pretrained("Dizex/InstaFoodRoBERTa-NER")
    model = AutoModelForTokenClassification.from_pretrained("Dizex/InstaFoodRoBERTa-NER")
    pipe = pipeline("ner", model=model, tokenizer=tokenizer)

    for review in reviews:
        
        ner_entity_results = pipe(review, aggregation_strategy="simple")

        def convert_entities_to_list(text, entities) -> list:
            ents = []
            for ent in entities:
                e = {"start": ent["start"], "end": ent["end"], "label": ent["entity_group"]}
                if ents and -1 <= ent["start"] - ents[-1]["end"] <= 1 and ents[-1]["label"] == e["label"]:
                    ents[-1]["end"] = e["end"]
                    continue
                ents.append(e)

            return [text[e["start"]:e["end"]] for e in ents]
        
        def add_foods_to_list(foods):
            nonlocal food_nouns, all_food_nouns_found
            for food in foods:
                all_food_nouns_found.append(food)
                from difflib import get_close_matches
                similar_food = get_close_matches(food, food_nouns, n=1)
                if not similar_food:
                    food_nouns.append(food.lower())

        add_foods_to_list(convert_entities_to_list(review, ner_entity_results))
    
    return {"food_nouns": food_nouns, "all_food_nouns_found": all_food_nouns_found }




def getVADERprediction(sentence):
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    #test = "This place is overrated, i would give only 2 stars. We got a table through waitlist on yelp so it was very convenient and fast however food experience was not as great. We ordered crab cakes, which were good, came with spicy salad, Fettuccine with clams which was extremely oily and had so much garlic that it was impossible to eat and surf and turf which was also very oily. I love oil and garlic but this was just too much of everything.Picture quality is due to poor lighting."
    analyzer = SentimentIntensityAnalyzer()
    vs = analyzer.polarity_scores(sentence)
    #print(str(vs))
    return vs

def mapSentencestoFoodNounsNER(food_nouns, reviews, all_food_nouns_found):
    from collections import defaultdict
    sentences_per_food_noun = defaultdict(list)

    for review in reviews:
        sentences = nltk.sent_tokenize(review)
        for sentence in sentences:
            foods_in_sentence = []
            for possible_food in all_food_nouns_found:
                if possible_food in sentence:
                    foods_in_sentence.append(possible_food)
                    continue
            for food in set(foods_in_sentence):
                from difflib import get_close_matches
                similar_food = get_close_matches(food, food_nouns, n=1)
                # if there is no similar food fix it
                # fix requirements.txt
                if not similar_food:
                    similar_food.append(food) 
                sentences_per_food_noun[similar_food[0]].append(sentence)
    return sentences_per_food_noun

def mapSentencesToFoodNouns(food_nouns, reviews):
    from collections import defaultdict
    sentences_per_food_noun = defaultdict(list)

    for review in reviews:
        sentences = nltk.sent_tokenize(review)
        for sentence in sentences:
            print(sentence)

            words = nltk.word_tokenize(sentence)
            for word in set(words):
                if word in food_nouns:
                    sentences_per_food_noun[word].append(sentence)
    return sentences_per_food_noun

def getAverageSentimentScorePerWord(food_nouns, sentences_per_food_noun):

    food_score_result = []

    for food in food_nouns:

        total_sum_of_probabilities = 0

        if len(sentences_per_food_noun[food]) == 0:
            continue
        
        filtered_sentences = [*set(sentences_per_food_noun[food])]
        sentences_per_food_noun[food] = filtered_sentences
        sentence_rating_pairs = []
        for sentence in filtered_sentences:
            result = getVADERprediction(sentence) # returns {neg, neu, pos, compound}
            compound_score = result["compound"]
            if compound_score != 0.0:
                sentence_rating_pairs.append({
                    "sentence": sentence,
                    "score": compound_score
                })
            total_sum_of_probabilities += compound_score
        sentence_rating_pairs.sort(key=lambda x: x["score"], reverse=True)
        sentences_per_food_noun[food] = sentence_rating_pairs
        avg_score = total_sum_of_probabilities/len(filtered_sentences)
        sentiment = ""
        if -0.3 < avg_score < 0.3: sentiment = "neutral"
        elif avg_score >= 0.3: sentiment = "positive"
        else: sentiment = "negative"
        if avg_score != 0.0 or (avg_score == 0.0 and sentence_rating_pairs):
            food_score_result.append((food, sentiment, avg_score))

    return { 
        "food_score_result": food_score_result,
        "sentences_per_food_nouns": sentences_per_food_noun
    } # [(food_noun, positive/neutral/negative, avg_score)]

def getBestAndWorstFoods(food_score_results, sentences_per_food_noun):
    positive_foods = []
    neutral_foods = []
    negative_foods = []

    for food in food_score_results:
        if food[1] == "positive":
            positive_foods.append({
                "food": food[0],
                "score": food[2],
                "sentences": sentences_per_food_noun[food[0]]
            })
        elif food[1] == "negative":
            negative_foods.append({
                "food": food[0],
                "score": food[2],
                "sentences": sentences_per_food_noun[food[0]]
            })
        else:
            neutral_foods.append({
                "food": food[0],
                "score": food[2],
                "sentences": sentences_per_food_noun[food[0]]
            })
    
    positive_foods.sort(key=lambda food: food["score"], reverse=True)
    negative_foods.sort(key=lambda food: food["score"], reverse=True)
    neutral_foods.sort(key=lambda food: food["score"], reverse=True)


    return {
        "positive_foods": positive_foods,
        "neutral_foods": neutral_foods,
        "negative_foods": negative_foods
    }

