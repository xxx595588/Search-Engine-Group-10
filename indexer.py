import os
import json
import nltk
import re
import time
import shutil
import sys
from posting import posting
from merge import merge
from bs4 import BeautifulSoup
from nltk import ngrams

# store the location of indexer.py
ori_loc = os.getcwd()

# partial indexer file counter
file_counter = 1

# url counter
acc_url_counter = 1

# combine version of frequency and position
final_index = dict()

# focuse on these tags for indexing
tag = ["title", "h1", "h2", "h3", "h4", "h5", "h6", "b", "strong"]

# map an id to url, the structure is {url: ID}
url_map = dict()

# reversed version of url_map (for better lookup)
url_lookup = dict()

# The structure of the index_freq is {word: {ID: freq}}, key is a string and value is a dictionary
index_freq = dict()
important_index_freq = dict()

# The structure of the index_pos is {word: [(ID, pos)]}, key is a string and value is a list of tuple
index_pos = dict()
important_index_pos = dict()

# Set contain indexed document to avoid same content
dup = set()

# Number of total document
total_doc = 0

# Number of indexed document
indexed_doc = 0

# Number of duplicated document which didn't be indexed
dup_doc = 0

# Time calculator
start_time = None
end_time = None

stemmer = nltk.stem.SnowballStemmer("english")


def create_token_dicts(token_string):
    tokens = nltk.word_tokenize(token_string)
    tokens = [stemmer.stem(t.lower()) for t in tokens]

    # to be removed word set (number or special character)
    tbr = set()

    # remove any non-alphanumeric character
    for w in tokens:
        if len(w) == 1 or re.search("[^a-z0-9]", w):
            tbr.add(w)

    # do up to trigram
    tokens_list = [w for w in tokens if w not in tbr]
    ngram_iteration = [2, 3]
    ngram_temp = list()

    for iter in ngram_iteration:
        ngramTokens = list(ngrams(tokens_list, iter))
        for ngram in ngramTokens:
            ngram_temp.append(ngram)

    tokens_list += ngram_temp

    # dictionary of word/freq
    tokens_freq = dict()
    
    # dictionary of word/pos
    tokens_pos = dict()

    # count for the word's frequency
    for i in range(len(tokens_list)):
        # section for ngram
        if(type(tokens_list[i]) == tuple):
            # print(tokens_list[i])
            ngramString = " ".join(list(tokens_list[i]))
            #sprint(ngramString)
            if ngramString in tokens_freq:
                tokens_freq[ngramString] += 1
            else:
                tokens_freq[ngramString] = 1
        # section for single word
        else:
            if tokens_list[i] in tokens_freq:
                tokens_freq[tokens_list[i]] += 1
            else:
                tokens_freq[tokens_list[i]] = 1

            # indicate the word's position -> word:[pos]
            if tokens_list[i] in tokens_pos:
                tokens_pos[tokens_list[i]].append(i+1)
            else:
                tokens_pos[tokens_list[i]] = [i+1]
    
    return tokens_freq, tokens_pos


# tokenize the content fetch from the json file
def tokenize(html_file):
    global tag

    raw_data = json.load(open(html_file))
    # get the content
    soup = BeautifulSoup(raw_data["content"], features = "html.parser")
    tag_list = soup.find_all(tag, text=True)

    temp_ter = ""
    important_words = ""

    important_tags = ["title", "h1", "h2", "h3", "strong"]
    for t in tag_list:
        if t.name in important_tags:
            # add to important index
            important_words += t.text
            important_words += "."
        else:
            # add to main index
            temp_ter += t.text
            temp_ter += "."
    
    main_tokens_freq, main_tokens_pos = create_token_dicts(temp_ter)
    important_tokens_freq, important_tokens_pos = create_token_dicts(important_words)

    return main_tokens_freq, main_tokens_pos, important_tokens_freq, important_tokens_pos, raw_data["url"]

# fetch all json file and tokenize the text from its content
def fetch_data():
    global ori_loc, url_map, index_freq, index_pos, total_doc, indexed_doc, dup_doc, acc_url_counter, file_counter

    if os.path.exists("index files"):
        shutil.rmtree("index files")

    os.mkdir("index files")

    path = input("Input the path: ")
    os.chdir(path)

    global index_freq, index_pos, important_index_freq, important_index_pos, total_doc, indexed_doc, dup_doc, acc_url_counter, file_counter

    for web_folder in os.listdir():
        os.chdir(web_folder)
        for html_file in os.listdir():

            # words with frequency in dict -> words: freq
            main_tokens_freq, main_tokens_pos, important_tokens_freq, important_tokens_pos, url = tokenize(html_file)

            print(f"Processing {url}")

            total_doc += 1

            # set of tokens without repeating
            main_tokens = main_tokens_freq.keys()
            important_tokens = important_tokens_freq.keys()
            all_tokens = set(main_tokens).union(set(important_tokens))
            hash_num = hash(frozenset(all_tokens))

            # check for duplcation
            if hash_num not in dup:
                indexed_doc += 1
                dup.add(hash_num)
                url_map[url] = acc_url_counter
                acc_url_counter += 1

                # MAIN INDEX
                for w in main_tokens:
                    # section for index frequency
                    if index_freq.get(w) is None:
                        new_dict = dict()
                        new_dict[url_map[url]] = main_tokens_freq[w]
                        index_freq[w] = new_dict
                    else:
                        index_freq[w][url_map[url]] = main_tokens_freq[w]

                    # section for index position
                    if(" " not in w):
                        if index_pos.get(w) is None:
                            index_pos[w] = dict()

                        index_pos[w][url_map[url]] = main_tokens_pos[w]

                # IMPORTANT WORDS INDEX
                for w in important_tokens:
                    # section for index frequency
                    if important_index_freq.get(w) is None:
                        new_dict = dict()
                        new_dict[url_map[url]] = important_tokens_freq[w]
                        important_index_freq[w] = new_dict
                    else:
                        important_index_freq[w][url_map[url]] = important_tokens_freq[w] 
                    
                    # section for index position
                    if(" " not in w):
                        if important_index_pos.get(w) is None:
                            important_index_pos[w] = dict()

                        important_index_pos[w][url_map[url]] = important_tokens_pos[w]

                # store the current indexs to partial index file if size is over 700000 bytes
                if sys.getsizeof(index_freq) > 700000:
                    wrap_up()
                    write_file(file_counter)
                    file_counter += 1
                    os.chdir(ori_loc + "/" + path + "/" + web_folder)

            else:
                dup_doc += 1

        # go to parent folder
        os.chdir(os.path.dirname(os.getcwd()))

    os.chdir(ori_loc)

# wrap up for the indexer (combine index_freq and index_pos)
def wrap_up():
    global final_index, index_freq, index_pos, important_index_freq, important_index_pos


    # integrate index_freq, index_pos, important_index_freq, & important_index_pos to posting
    for i in range(len(index_freq)):
        key_list = list(index_freq.keys())
        word = key_list[i]
        new_posting = posting(word, dict(), list(), dict(), list())
        new_posting.freq_add(index_freq[word])

        if(" " not in key_list[i]):
            new_posting.pos_add(index_pos[word])

        imp_key_list = list(important_index_freq.keys())
        if(word in imp_key_list):
            new_posting.imp_freq_add(index_freq[word]) 

            if(" " not in key_list[i]):
                new_posting.imp_pos_add(index_pos[word])

        final_index[word] = new_posting
    
    for i in range(len(important_index_freq)):
        key_list = list(important_index_freq.keys())
        word = key_list[i]

        # if the word isn't already in the final index
        # (it only shows up in headers or in bold)
        if word not in final_index.keys():
            new_posting = posting(word, dict(), list(), dict(), list()) 
            new_posting.imp_freq_add(important_index_freq[word])

            if(" " not in key_list[i]):
                new_posting.imp_pos_add(important_index_pos[word])
    
            final_index[word] = new_posting

    index_freq.clear()
    index_pos.clear()
    important_index_freq.clear()
    important_index_pos.clear()

# generate the ouput file
def write_file(file_counter):
    global index_freq, index_pos, final_index, ori_loc

    # sort the words
    final_index = dict(sorted(final_index.items(), key=lambda item: item[0]))

    # output the final index
    os.chdir(ori_loc)
    os.chdir("index files")
    file_name = "index_" + str(file_counter) + ".txt"
    f = open(file_name, "w")
    for i in final_index:
        f.write(f"{{\"token\":\"{i}\", \"postings\":\"{final_index[i].get_freq()}\", \"positions\":\"{final_index[i].get_pos()}\", \"imp_postings\":\"{final_index[i].get_imp_freq()}\", \"imp_positions\":\"{final_index[i].get_imp_pos()}\"}}\n")
    f.close()

    final_index.clear()

def general_output():
    global url_lookup, url_map, total_doc, indexed_doc, dup_doc

    # construct the url lookup table
    url_lookup = {id: url for url, id in url_map.items()}

    # contain some general info for the indexing process
    f = open("general_output.txt", "w")
    elapsed_time = end_time - start_time
    f.write(f"Total number of documents: {total_doc}\n"
                + f"Number of indexed documents: {indexed_doc}\n"
                + f"Number of duplicated documents: {dup_doc}\n"
                + f"Total runtime: {elapsed_time} seconds\n")
    f.close()

    # output the url lookup table
    # ID: url
    f = open("url_lookup.txt", "w")
    for i in url_lookup:
        f.write(f"{{\"id\":\"{i}\", \"url\":\"{url_lookup[i]}\"}}\n")
    f.close()

# export the remaining data which is less than 700000 byte at the end
def export_remain():
    global file_counter, index_freq

    if len(index_freq) != 0:
        wrap_up()
        write_file(file_counter)

def main():
    global start_time
    start_time = time.time()

    fetch_data()
    export_remain()

    global end_time
    end_time = time.time()

    os.chdir(ori_loc)
    general_output()
    merge()
    

if __name__ == "__main__":
    main()