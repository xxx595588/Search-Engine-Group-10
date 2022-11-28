import json
import time
import linecache
import nltk
import math
from posting import posting
from doc_tfidf import doc_tfidf
from nltk import ngrams

stemmer = nltk.stem.SnowballStemmer("english")
alphabet = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"]
ngram_iteration = [2, 3]

# implement binary search to find the target word in the file
def binary_search(mid_list, start, end, word, indexer_list, allPostings):

    # valid conditioin for binary search
    if end >= start:
        mid = (start + end) // 2

        # get the mid-th word in the file
        line = linecache.getline("merged_indexer.txt", mid)
        loaded = json.loads(line)

        mid_list.append(mid)

        # compare word with mid-th word
        if word == loaded["token"]:
            postings = posting(word, eval(loaded["postings"]), eval(loaded["positions"]))
            indexer_list.append(postings)
            allPostings.append(postings.get_freq().keys())
            return mid_list
        # search start to mid - 1
        elif word < loaded["token"]:
            return binary_search(mid_list, start, mid - 1, word, indexer_list, allPostings)
        # search mid + 1 to end
        else:
            return binary_search(mid_list, mid + 1, end, word, indexer_list, allPostings)
    # word isn't present in the file
    else:
        return list()

# calculate the tf-idf for query
def tf_idf_query(raw_query, queries, indexer_list, num_indexed_doc):
    # get the tf-idf for query
    tf_query = list()
    idf_query = list()
    found_terms = list()
    found_term_freq = list()

    raw_query = nltk.word_tokenize(raw_query)

    raw_query = [stemmer.stem(t.lower()) for t in raw_query]
    raw_query = " ".join(raw_query)

    for posting in indexer_list:
        found_terms.append(posting.get_word())
        found_term_freq.append(posting.get_freq())

    for term in queries:
        if term not in found_terms:
            tf_query.append(0)
            idf_query.append(0)
        else:
            index = found_terms.index(term)
            tf_query.append(1 + math.log(raw_query.count(term), 10))
            idf_query.append(math.log(num_indexed_doc/len(found_term_freq[index]), 10))

    tf_idf_query = list()
    length_query = 0

    # calculate tf_idf without normalization
    for i in range(len(tf_query)):
        tf_idf_query.append(tf_query[i] * idf_query[i])
        length_query += tf_idf_query[i]**2

    length_query = math.sqrt(length_query)

    for i in range(len(tf_query)):
        tf_idf_query[i] = tf_idf_query[i]/length_query

    return tf_idf_query

def tf_idf_documents(queries, indexer_list, num_indexed_doc):
    doc_union = set()
    word_list = list()

    # obtain the union of the document id
    for i in indexer_list:
        word_list.append(i.get_word())
        for id in i.get_freq().keys():
            if id not in doc_union:
                doc_union.add(id)
    
    doc_union = sorted(list(doc_union))

    doc_list = list()
    
    # calculate the tf for each document
    for id in doc_union:
        doc_item = doc_tfidf(id, queries)
        sum = 0
        for q in queries:
            if q in word_list:
                index = word_list.index(q)
                if index >= 0:
                    freq = indexer_list[index].get_freq()
                    if freq.get(id) != None:
                        tf = 1 + math.log(indexer_list[index].get_freq()[id], 10)
                        doc_item.tf_add(q, tf)
                        sum += tf**2

        length_doc = math.sqrt(sum)
        
        # normalization
        for key, value in doc_item.get_tf().items():
            doc_item.get_tf()[key] = value / length_doc
        
        doc_list.append(doc_item)

    return doc_list

def ranking(raw_query, queries, indexer_list):
    line = linecache.getline("general_output.txt", 2)
    num_indexed_doc = int(line.split(":")[-1])

    tf_idf_q = tf_idf_query(raw_query, queries, indexer_list, num_indexed_doc)
    tf_idf_d = tf_idf_documents(queries, indexer_list, num_indexed_doc)
    top_five = dict()

    for doc_item in tf_idf_d:
        id = doc_item.get_id()
        tf_doc = doc_item.get_tf()
        sum = 0

        for i in range(len(queries)):
            sum += (tf_idf_q[i] * tf_doc[queries[i]])
        
        top_five[id] = sum
        top_five = dict(sorted(top_five.items(), key=lambda item: item[1], reverse=True))

        if len(top_five) > 5:
            top_five.popitem()

    return list(top_five.keys())


def search():
    query = input("Enter your query seperated by spaces: ")
    queries = nltk.word_tokenize(query)
    queries = [stemmer.stem(w.lower()) for w in queries]
    

    # doing ngram
    global ngram_iteration
    ngram_temp = list()

    for iter in ngram_iteration:
        ngramTokens = list(ngrams(queries, iter))
        for ngram in ngramTokens:
            ngram_temp.append(ngram)

    queries += ngram_temp

    for i in range(len(queries)):
        if(type(queries[i]) == tuple):
            queries[i] = " ".join(list(queries[i]))

    # open indicator.txt file which can boost the binary search speed
    f = open("indicator.txt", "r")
    indicator = eval(f.readline()[:-1])

    # list of query words' docID, used for finding intersection
    allPostings = list()

    # dictionary of posting, will be used in tf-idf calculation
    indexer_list = list()

    # sort the query for better performance
    queries = sorted(queries)
    global alphabet
    
    start = time.time()

    # partition query's word into 26 sublist by their starting alphabet
    partition_word = [None]*26
    for word in queries:
        if partition_word[alphabet.index(word[0])] is None:
            partition_word[alphabet.index(word[0])] = [word]
        else:
            partition_word[alphabet.index(word[0])].append(word)

    for sublist in partition_word:
        if sublist is not None:
            first_time = True
            # collect all mid value to help following search in the same sublist
            mid_list = list()
            for word in sublist:
                # original start and end position for corresponding alphabet
                start_pos = indicator[alphabet.index(word[0])]
                end_pos = indicator[alphabet.index(word[0]) + 1] - 1

                if first_time:
                    mid_list = binary_search(mid_list, start_pos, end_pos, word, indexer_list, allPostings)
                    first_time = False
                else:
                    # check with mid_list to trim the search range
                    for pos in mid_list:
                        line = linecache.getline("merged_indexer.txt", pos)
                        loaded = json.loads(line)

                        if word < loaded["token"]:
                            if pos < end_pos:
                                end_pos = pos
                        
                        if word > loaded["token"]:
                            if pos > start_pos:
                                start_pos = pos

                    mid_list = binary_search(mid_list, start_pos, end_pos, word, indexer_list, allPostings)

    top_five = ranking(query, queries, indexer_list)

    end = time.time()  

    url_result_list = list()

    # look up the url
    for id in top_five:
        line = linecache.getline("url_lookup.txt", id)
        loaded = json.loads(line)
        url_result_list.append(loaded["url"])

    if len(url_result_list) == 0:
        print("No matched result was found.")
    else:
        for i in range(len(url_result_list)):
            print(f"{i + 1}. {url_result_list[i]}")

    print(f"\n{len(top_five)} results ({end-start} seconds)")
    print(f"-----------------------------end of search-----------------------------")

search()