import os
import json
from posting import posting

# get the location of merge.py
ori_loc = os.getcwd()
path = "index files"
output_file = "merged_indexer.txt"
pos_counter = 0

# used to indicate the staring position of each alphabet & digit in the file
alphabet_indicator = [-1]*37
alphabet = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"]
unique_token = 0

# convert raw_data into posting
def index_converter(raw_data):
    loaded = json.loads(raw_data)
    word = loaded["token"]
    id_freq = eval(loaded["postings"])
    id_pos = eval(loaded["positions"])
    imp_freq = eval(loaded["imp_postings"])
    imp_pos = eval(loaded["imp_positions"])

    return posting(word, id_freq, id_pos, imp_freq, imp_pos)

# merge all partial index files into one merged index file
def merge():
    global ori_loc, path, output_file, alphabet, alphabet_indicator, pos_counter, unique_token
    
    # remove previous indexer file
    if os.path.exists(output_file):
        os.remove(output_file)
    
    os.chdir(path)

    # list of index file to be merged
    files_to_read = os.listdir()
    file_reader = []
    files_to_read = sorted(files_to_read)

    # store the current posting of each file
    cur_posting = []
    
    # create reader, one per file
    for index_file in files_to_read:
        file_reader.append(open(index_file, "r"))
    
    # import postings into cur_posting
    for i in range(len(file_reader)):
        data = file_reader[i].readline()
        if data == "":
            cur_posting.append("eof")
        else:
            cur_posting.append(index_converter(data))
            
    # word list which is corresopnding to cur_posting
    word_list = list()
    
    for post in cur_posting:
        if post == "eof":
            word_list.append("~")
        else:
            word_list.append(post.get_word())
    
    while True:
        # obtain the nmuber of posting needs to be mergerd
        num_to_merge = word_list.count(min(word_list))
        
        # only one minimum posting was found, no need to merge
        if num_to_merge == 1:
            index = word_list.index(min(word_list))
            to_be_merged = cur_posting[index]
            
            # read the next word for file_reader[index]
            data = file_reader[index].readline()
            
            # check if reach end of file
            if data == "":
                cur_posting[index] = "eof"
                word_list[index] = "~"
            else:
                cur_posting[index] = index_converter(data)
                word_list[index] = cur_posting[index].get_word()
                
            # write the signle posting to the disk
            os.chdir(ori_loc)
            f = open(output_file, "a")
            f.write(f"{{\"token\":\"{to_be_merged.get_word()}\", \"postings\":\"{to_be_merged.get_freq()}\", \"positions\":\"{to_be_merged.get_pos()}\", \"imp_postings\":\"{to_be_merged.get_imp_freq()}\", \"imp_positions\":\"{to_be_merged.get_imp_pos()}\"}}\n")
            f.close()

            start_char = to_be_merged.get_word()[0]

            # locate tje first position of that alphabet
            if alphabet_indicator[alphabet.index(start_char)] == -1:
                alphabet_indicator[alphabet.index(start_char)] = pos_counter

            pos_counter += 1
            
        else:
            # indicate which cur_posting are about to be merged as a list of indexs
            indexs = [i for i in range(len(word_list)) if word_list[i] == min(word_list)]
            to_be_merged = list()
            
            for i in indexs:
                # gather all postings
                to_be_merged.append(cur_posting[i])
                data = file_reader[i].readline()
                
                # check if reach end of file
                if data == "":
                    cur_posting[i] = "eof"
                    word_list[i] = "~"
                else:
                    cur_posting[i] = index_converter(data)
                    word_list[i] = cur_posting[i].get_word()
                    
            # merge the to_be_merged here...
            
            word = to_be_merged[0].get_word()
            new_id_freq = dict()
            new_id_pos = dict()
            new_imp_freq = dict()
            new_imp_pos = dict()
            
            # merge the diction of id/freq and id/pos
            for p in to_be_merged:
                new_id_freq |= p.get_freq()
                new_id_pos |= p.get_pos()
                new_imp_freq |= p.get_imp_freq()
                new_imp_pos |= p.get_imp_pos()
                
            new_id_freq = dict(sorted(new_id_freq.items(), key=lambda item: item[0]))
            new_id_pos = dict(sorted(new_id_pos.items(), key=lambda item: item[0]))
            new_imp_freq = dict(sorted(new_imp_freq.items(), key=lambda item: item[0]))
            new_imp_pos = dict(sorted(new_imp_pos.items(), key=lambda item: item[0]))
            
            os.chdir(ori_loc)
            f = open(output_file, "a")
            f.write(f"{{\"token\":\"{word}\", \"postings\":\"{new_id_freq}\", \"positions\":\"{new_id_pos}\", \"imp_postings\":\"{new_imp_freq}\", \"imp_positions\":\"{new_imp_pos}\"}}\n")
            f.close()

            start_char = word[0]

            # locate the first position of that alphabet
            if alphabet_indicator[alphabet.index(start_char)] == -1:
                alphabet_indicator[alphabet.index(start_char)] = pos_counter

            pos_counter += 1
                
            os.chdir(ori_loc)

        unique_token += 1
                
        # check if reach end of file for all files
        if cur_posting.count("eof") == len(files_to_read):
            break
        
        # mark the end position
        alphabet_indicator[36] = pos_counter

        # write the indicator.txt file
        os.chdir(ori_loc)
        f = open("indicator.txt", "w")
        f.write("[")
        temp = ""
        for i in alphabet_indicator:
            temp += (str(i) + ", ")
        temp = temp[:-2]  
        f.write(f"{temp}]\n")
        f.close()

    # append remaining info to general output
    f = open("general_output.txt", "a")
    index_file_size = os.path.getsize(output_file) / 1000
    f.write(f"Number of unique tokens: {unique_token}\n"
            + f"Total size of index: {index_file_size}KB")
    f.close()
