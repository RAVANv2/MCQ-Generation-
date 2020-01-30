from flask import Flask,request,jsonify,render_template
from textblob import TextBlob
import nltk
from textblob import Word
import sys

import pandas as pd
from IPython.display import Markdown, display, clear_output

import _pickle as cPickle
from pathlib import Path

import spacy
from spacy import displacy
import en_core_web_sm

import gensim
from gensim.test.utils import datapath, get_tmpfile
from gensim.models import KeyedVectors

from gensim.scripts.glove2word2vec import glove2word2vec

app = Flask(__name__)
@app.route('/',methods=['POST'])

def general():
    def dumpPickle(fileName, content):
        pickleFile = open(fileName, 'wb')
        cPickle.dump(content, pickleFile, -1)
        pickleFile.close()

    def loadPickle(fileName):    
        file = open(fileName, 'rb')
        content = cPickle.load(file)
        file.close()
        
        return content
    
    def pickleExists(fileName):
        file = Path(fileName)
        
        if file.is_file():
            return True
        
        return False
    
    nlp = en_core_web_sm.load() 

    def extractAnswers(qas, doc):
        answers = []

        senStart = 0
        senId = 0

        for sentence in doc.sents:
            senLen = len(sentence.text)

            for answer in qas:
                answerStart = answer['answers'][0]['answer_start']

                if (answerStart >= senStart and answerStart < (senStart + senLen)):
                    answers.append({'sentenceId': senId, 'text': answer['answers'][0]['text']})

            senStart += senLen
            senId += 1
        
        return answers

    def tokenIsAnswer(token, sentenceId, answers):
        for i in range(len(answers)):
            if (answers[i]['sentenceId'] == sentenceId):
                if (answers[i]['text'] == token):
                    return True
        return False

    def getNEStartIndexs(doc):
        neStarts = {}
        for ne in doc.ents:
            neStarts[ne.start] = ne
            
        return neStarts 

    def getSentenceStartIndexes(doc):
        senStarts = []
        
        for sentence in doc.sents:
            senStarts.append(sentence[0].i)
        
        return senStarts

    def getSentenceForWordPosition(wordPos, senStarts):
        for i in range(1, len(senStarts)):
            if (wordPos < senStarts[i]):
                return i - 1

    def addWordsForParagrapgh(newWords, text):
        doc = nlp(text)

        neStarts = getNEStartIndexs(doc)
        senStarts = getSentenceStartIndexes(doc)
        
        #index of word in spacy doc text
        i = 0
        
        while (i < len(doc)):
            #If the token is a start of a Named Entity, add it and push to index to end of the NE
            if (i in neStarts):
                word = neStarts[i]
                #add word
                currentSentence = getSentenceForWordPosition(word.start, senStarts)
                wordLen = word.end - word.start
                shape = ''
                for wordIndex in range(word.start, word.end):
                    shape += (' ' + doc[wordIndex].shape_)

                newWords.append([word.text,
                                0,
                                0,
                                currentSentence,
                                wordLen,
                                word.label_,
                                None,
                                None,
                                None,
                                shape])
                i = neStarts[i].end - 1
            #If not a NE, add the word if it's not a stopword or a non-alpha (not regular letters)
            else:
                if (doc[i].is_stop == False and doc[i].is_alpha == True):
                    word = doc[i]

                    currentSentence = getSentenceForWordPosition(i, senStarts)
                    wordLen = 1

                    newWords.append([word.text,
                                    0,
                                    0,
                                    currentSentence,
                                    wordLen,
                                    None,
                                    word.pos_,
                                    word.tag_,
                                    word.dep_,
                                    word.shape_])
            i += 1

    def oneHotEncodeColumns(df):
        columnsToEncode = ['NER', 'POS', "TAG", 'DEP']

        for column in columnsToEncode:
            one_hot = pd.get_dummies(df[column])
            one_hot = one_hot.add_prefix(column + '_')

            df = df.drop(column, axis = 1)
            df = df.join(one_hot)
        
        return df

    def generateDf(text):
        words = []
        addWordsForParagrapgh(words, text)

        wordColums = ['text', 'titleId', 'paragrapghId', 'sentenceId','wordCount', 'NER', 'POS', 'TAG', 'DEP','shape']
        df = pd.DataFrame(words, columns=wordColums)
        print(df.shape)
        return df


    def prepareDf(df):
        #One-hot encoding
        wordsDf = oneHotEncodeColumns(df)

        #Drop unused columns
        columnsToDrop = ['text', 'titleId', 'paragrapghId', 'sentenceId', 'shape']
        wordsDf = wordsDf.drop(columnsToDrop, axis = 1)

        #Add missing colums 
        predictorColumns = ['wordCount','NER_CARDINAL','NER_DATE','NER_EVENT','NER_FAC','NER_GPE','NER_LANGUAGE','NER_LAW','NER_LOC','NER_MONEY','NER_NORP','NER_ORDINAL','NER_ORG','NER_PERCENT','NER_PERSON','NER_PRODUCT','NER_QUANTITY','NER_TIME','NER_WORK_OF_ART','POS_ADJ','POS_ADP','POS_ADV','POS_CCONJ','POS_DET','POS_INTJ','POS_NOUN','POS_NUM','POS_PART','POS_PRON','POS_PROPN','POS_PUNCT','POS_SYM','POS_VERB','POS_X','TAG_''','TAG_-LRB-','TAG_.','TAG_ADD','TAG_AFX','TAG_CC','TAG_CD','TAG_DT','TAG_EX','TAG_FW','TAG_IN','TAG_JJ','TAG_JJR','TAG_JJS','TAG_LS','TAG_MD','TAG_NFP','TAG_NN','TAG_NNP','TAG_NNPS','TAG_NNS','TAG_PDT','TAG_POS','TAG_PRP','TAG_PRP$','TAG_RB','TAG_RBR','TAG_RBS','TAG_RP','TAG_SYM','TAG_TO','TAG_UH','TAG_VB','TAG_VBD','TAG_VBG','TAG_VBN','TAG_VBP','TAG_VBZ','TAG_WDT','TAG_WP','TAG_WRB','TAG_XX','DEP_ROOT','DEP_acl','DEP_acomp','DEP_advcl','DEP_advmod','DEP_agent','DEP_amod','DEP_appos','DEP_attr','DEP_aux','DEP_auxpass','DEP_case','DEP_cc','DEP_ccomp','DEP_compound','DEP_conj','DEP_csubj','DEP_csubjpass','DEP_dative','DEP_dep','DEP_det','DEP_dobj','DEP_expl','DEP_intj','DEP_mark','DEP_meta','DEP_neg','DEP_nmod','DEP_npadvmod','DEP_nsubj','DEP_nsubjpass','DEP_nummod','DEP_oprd','DEP_parataxis','DEP_pcomp','DEP_pobj','DEP_poss','DEP_preconj','DEP_predet','DEP_prep','DEP_prt','DEP_punct','DEP_quantmod','DEP_relcl','DEP_xcomp']

        for feature in predictorColumns:
            if feature not in wordsDf.columns:
                wordsDf[feature] = 0
        print(wordsDf.shape)
        return wordsDf

    def predictWords(wordsDf, df):
    
        predictorPickleName = 'data/pickles/nb-predictor.pkl'
        predictor = loadPickle(predictorPickleName)
        
        y_pred = predictor.predict_proba(wordsDf)

        labeledAnswers = []
        for i in range(len(y_pred)):
            labeledAnswers.append({'word': df.iloc[i]['text'], 'prob': y_pred[i][0]})
        return labeledAnswers

    def blankAnswer(firstTokenIndex, lastTokenIndex, sentStart, sentEnd, doc):
        leftPartStart = doc[sentStart].idx
        leftPartEnd = doc[firstTokenIndex].idx
        rightPartStart = doc[lastTokenIndex].idx + len(doc[lastTokenIndex])
        rightPartEnd = doc[sentEnd - 1].idx + len(doc[sentEnd - 1])
        
        question = doc.text[leftPartStart:leftPartEnd] + '_____' + doc.text[rightPartStart:rightPartEnd]
        
        return question


    def addQuestions(answers, text):
        doc = nlp(text)
        currAnswerIndex = 0
        qaPair = []

        #Check wheter each token is the next answer
        for sent in doc.sents:
            for token in sent:
                
                #If all the answers have been found, stop looking
                if currAnswerIndex >= len(answers):
                    break
                
                #In the case where the answer is consisted of more than one token, check the following tokens as well.
                answerDoc = nlp(answers[currAnswerIndex]['word'])
                answerIsFound = True
                
                for j in range(len(answerDoc)):
                    if token.i + j >= len(doc) or doc[token.i + j].text != answerDoc[j].text:
                        answerIsFound = False
            
                #If the current token is corresponding with the answer, add it 
                if answerIsFound:
                    question = blankAnswer(token.i, token.i + len(answerDoc) - 1, sent.start, sent.end, doc)
                    
                    qaPair.append({'question' : question, 'answer': answers[currAnswerIndex]['word'], 'prob': answers[currAnswerIndex]['prob']})
                    
                    currAnswerIndex += 1
                    
        return qaPair

    def sortAnswers(qaPairs):
        orderedQaPairs = sorted(qaPairs, key=lambda qaPair: qaPair['prob'])
        
        return orderedQaPairs 
        
    glove_file = 'data/embeddings/glove.6B.300d.txt'
    tmp_file = 'data/embeddings/word2vec-glove.6B.300d.txt'   

    glove2word2vec(glove_file, tmp_file)
    model = KeyedVectors.load_word2vec_format(tmp_file)


    def generate_distractors(answer, count):
        answer = str.lower(answer)
        
        ##Extracting closest words for the answer. 
        try:
            closestWords = model.most_similar(positive=[answer], topn=count)
        except:
            #In case the word is not in the vocabulary, or other problem not loading embeddings
            return []

        #Return count many distractors
        distractors = list(map(lambda x: x[0], closestWords))[0:count]
    
        return distractors

    def addDistractors(qaPairs, count):
        for qaPair in qaPairs:
            distractors = generate_distractors(qaPair['answer'], count)
            qaPair['distractors'] = distractors
        
        return qaPairs

    def generateQuestions(text, count):
    
        # Extract words 
        df = generateDf(text)
        wordsDf = prepareDf(df)
        
        # Predict 
        labeledAnswers = predictWords(wordsDf, df)

    
        # Transform questions
        qaPairs = addQuestions(labeledAnswers, text)
        
        # Pick the best questions
        orderedQaPairs = sortAnswers(qaPairs)
        
        # Generate distractors
        questions = addDistractors(orderedQaPairs[:count], 4)
        
        # Print
        for i in range(count):
            display(Markdown('### Question ' + str(i + 1) + ':'))
            print(questions[i]['question'])

            display(Markdown('#### Answer:'))
            print(questions[i]['answer'])
            
            display(Markdown('#### Incorrect answers:'))
            for distractor in questions[i]['distractors']:
                print(distractor)
            
            print()

    
    text="By the late 1830s, botanist Matthias Schleiden and zoologist Theodor Schwann were studying tissues and proposed the unified cell theory. The unified cell theory states that: all living things are composed of one or more cells; the cell is the basic unit of life; and new cells arise from existing cells. Rudolf Virchow later made important contributions to this theory.Schleiden and Schwann proposed spontaneous generation as the method for cell origination, but spontaneous generation (also called abiogenesis) was later disproven. Rudolf Virchow famously stated “Omnis cellula e cellula”… “All cells only arise from pre-existing cells. “The parts of the theory that did not have to do with the origin of cells, however, held up to scientific scrutiny and are widely agreed upon by the scientific community today. "
    print(len(text))

    generateQuestions(text, 15)
    
    
    return "something"

if __name__=="__main__":
    app.run(debug=True,port=5000)