import sys
import re #regular expressions library
#from src import readFiles, globalStuff
from src.readFiles import readISA
from src.globalStuff import buffer_max_size
import json
import time
import os
import csv

class Node:
    def __init__(self):
        self.reg = ""
        self.opcode = ""
        self.parent = 0
        self.child_num = 0
        self.start_line = 0


S = list()
ST_dict = dict()

def getOp(line):
    #print(line)
    line_ = line.split(' ')
    
    if len(line_) >= 3:
        #print(line_)
        for idx, oprd in enumerate(line_[1:]):
            oprd = re.sub(r' ','',oprd)
            oprd = re.sub(r'[\n|,|;]+','',oprd)
            line_[idx+1] = oprd 

        return line_[0], line_[1:]
    else:
        return "x","x"

def findLine(reversed_BB,dst):
    if len(S)==0:
        print("empty!!")
        return "empty S", -1
    #S.remove(dst)
    for idx, l in enumerate(reversed_BB):
        _, operands = getOp(l)
        #if operands == "x":
        #    return "no matching line", -1

        #operands = re.sub(r' ','',operands[0])
        #operands = re.sub(r'[\n,;]+',' ',operands)
        
        opr = re.sub(r'[\[\]]','',re.sub("\t","",operands[0]))
        #print(f"operand: {opr}")
        #print(f"destination: {dst}")

        if opr==dst:
            return l, idx

    return "no matching line", -1

def buildSyntaxTree(reversed_BB, ST,MAX_DEPTH):
    next_id = 1
    n_id = 0
    limit_met = False
    start_idx = 0
    max_len = len(reversed_BB)
    #print(f"max len: {max_len}") 
    while(len(S) !=0 and limit_met==False and start_idx <= max_len):
        start_idx = ST[n_id].start_line
        l, idx = findLine(reversed_BB[start_idx:], S[0])
        #print(S)
        S.remove(S[0])
        
        if idx == -1:
            n_id += 1
            continue

        start_idx += idx
        
        if start_idx ==len(reversed_BB):
            break
        
        opcode, operands = getOp(l)
        #operands = re.sub(r' ','',operands[0])
        #operands = re.sub(r'[\n,;]+',' ',operands)
        for idx_, oprd in enumerate(operands):
            oprd = re.sub(r' ','',oprd)
            oprd = re.sub(r'[\n|,|;]+','',oprd)
            oprd = re.sub(r"[\[\]]","",oprd)
            if oprd.startswith("%"):
                oprd = re.sub(r"[\+\-]\d*","",oprd)
            operands[idx_] = oprd
        
        
        ## if the source of ld.global instruction was in other instruction's destination,
        #src = operands[0]
        
        #S.extend(src)
        ST[n_id].opcode = opcode
        ST[n_id].child_num = len(operands[1:])
        #print(operands)
        S.extend(operands[1:])
        for src_ in operands[1:]:
            if next_id >= 500:
                limit_met = True
                break
            if src_ =="":
                print("src is empty***********************")
                print(l)
                print(operands)
                print("**********************")
            ST[next_id].reg = src_
            ST[next_id].parent = n_id
            ST[next_id].start_line = start_idx+1 
            next_id += 1
            #S.extend(src_)
        n_id += 1
    if(next_id >MAX_DEPTH):
        MAX_DEPTH = next_id
    #print(start_idx)
    #print(max_len)
    #if start_idx <max_len:
    #    print("DDDDDD")
    return MAX_DEPTH

def getAllSyntaxTrees(filepath, ISA, state_spaces, inst_types, isa_type, MAX_DEPTH):
    max_reg= 500
    print(filepath)
    f = open(filepath)
    f_ = f.readlines()
    #occurrences_global=np.zeros(len(ISA), dtype=np.int32)
    #shared_id = state_spaces.index('shared')
    
    ST = list()
    BB_id = 0
    total_len = len(f_)
    check_found=False
    kernel_name = ""
    
    for idx, line in enumerate(f_):
        line = re.sub(r"\t","",line)

        #detect kernel
        if line.startswith(".visible"):
            kernel_name = line.split(' ')[2]
            kernel_name = kernel_name.split('(')[0]
            if kernel_name not in ST_dict:
                ST_dict[kernel_name] = dict()
            print(f"kernel name: {kernel_name}")
            continue

        opcode, operands = getOp(line)
        #dismiss non operational line        
        if opcode =='x':
            continue

        opcode = opcode.split(' ')[0]
        for idx_, oprd in enumerate(operands):
            oprd = re.sub(r' ','',oprd)
            oprd = re.sub(r'[\n|,|;]+','',oprd)
            operands[idx_] = oprd
  
        if opcode.split('.')[0] not in ISA: 
            continue

        #ld global finding starts
        if opcode.startswith("ld.global") or "ld.global" in opcode:
            #print(line)
            ld_reg = re.sub(r'[\[\]]','',operands[-1])
            
            if oprd.startswith("%"):
                if "+" in ld_reg or "-" in ld_reg:
                    ld_reg = re.sub(r"[\+\-]\d*","",ld_reg)

            # check if there is same register target
            if ld_reg in ST_dict[kernel_name]:
                continue
            ST.append([Node() for x in range(max_reg)])

            s_id = len(ST)-1
            S.append(ld_reg)

            ST[s_id][0].parent = -1
            ST[s_id][0].reg = ld_reg
            rev_BB = f_[idx-1::-1]
            MAX_DEPTH = buildSyntaxTree(rev_BB,ST[s_id],MAX_DEPTH)
            S.clear()
            line_ = re.sub("[\t\n]","",line)
            
            if ST[s_id][1].reg != "" :
                ST_dict[kernel_name][ld_reg] = list()
                
                for idx, l in enumerate(ST[s_id]):
                    if l.reg == "":
                        break
                    temp_dict = dict()
                    temp_dict["reg"] = l.reg
                    temp_dict["opcode"] = l.opcode
                    temp_dict["parent"] = l.parent
                    temp_dict["child_num"] = l.child_num
                    temp_dict["start_line"] = l.start_line
                    
                    ST_dict[kernel_name][ld_reg].append(temp_dict)
                    
                #print(ST_dict[line_])
            
            #exit(1)  #ddddd  
            '''
            for idx, l in enumerate(ST[s_id]):
                if l.reg == "":
                    print("")
                    break
                #if len(l)==1:
                #    continue
                print(f"idx: {idx} reg: {l.reg}, opcode:{l.opcode}, parent:{l.parent}, child num:{l.child_num}, start line : {l.start_line}")
        '''
        
        if check_found:
            print(line)
    f.close()
    return ST, MAX_DEPTH

def main():
    """Main function."""
    import argparse
    import sys

    parser = argparse.ArgumentParser()

    isa_type = 'PTX'

    # parser.add_argument('isa_type', type=str)
    parser.add_argument('isa_files_path', type=str)
    parser.add_argument('benchmark_source_file', type=str)
    parser.add_argument('--v', action='store_const', const=True, default=False)
    args = vars(parser.parse_args())
    print(args)

    # isa_type = args['isa_type']
    isa_files_path =  args['isa_files_path']
    ptx_path = args['benchmark_source_file']
    global verbose
    verbose = args['v']

    isa_file_path = '%s/ptx_isa.txt' %isa_files_path
    state_spacesfile_path = '%s/ptx_state_spaces.txt' %isa_files_path
    instruction_types_file_path = '%s/ptx_instruction_types.txt' %isa_files_path

    ISA = readISA(isa_file_path)
    print('\n\n======================= ARCHITECTURE =======================\n')
    print("ISA has %d instructions" %(len(ISA)))
    state_spaces = readISA(state_spacesfile_path)
    print("state_spaces has %d spaces" %(len(state_spaces)))
    inst_types = readISA(instruction_types_file_path)
    print("inst_types has %d types" %(len(inst_types)))
    workload_list = ["parsec","polybench","rodinia"]
    time_list = list()
    if verbose == True:
        print('\n\n================== BEGINNING PTX PARSING ==================\n')
    #####jieun part start
    for workload_ in workload_list:        
        workload_path = os.path.join(ptx_path, workload_)
        file_list = os.listdir(workload_path)
        for file_ in file_list:
            if file_  == "myocyte.ptx":
                continue
            max_ = 0
            ptx_file_path = os.path.join(workload_path,file_)
            start_time = time.time()
            ST , max_ = getAllSyntaxTrees(ptx_file_path, ISA, state_spaces, inst_types, isa_type, 0)
            end_time = time.time()

            workload = file_.split(".")[0]
            with open(f"ptx_files/syntax_tree/{workload_}/{workload_}_{workload}.json", "w") as json_file:
                json.dump(ST_dict, json_file, indent = 4)
            time_list.append([workload_,workload,end_time-start_time, len(ST_dict), max_])
            ST_dict.clear()
            S.clear()

    ####jieun part end
    '''
    with open("ptx_files/workload_features.csv","w") as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerows(time_list) '''


if __name__ == "__main__":
    main()
