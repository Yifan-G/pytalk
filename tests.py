import glob
import os
from doctalk.talk import *
from doctalk.nlp import *
from doctalk.query import *

import pprint

doc_dir="examples/"
doc_files = sorted(glob.glob(doc_dir+"*.txt"))
quest_files = sorted(glob.glob(doc_dir+"*_quest.txt"))

def quest2doc(qf) :
  return qf.replace('_quest.txt','.txt')

def process_docs() :
  for quest_file in quest_files :
    process_doc(quest_file)

def process_doc(quest_file) :
    print(quest_file)
    doc_file=quest2doc(quest_file)
    print(doc_file,'-->',quest_file,'?')
    query(doc_file,quest_file)

#clean files at given directory path
def clean_path(path) :
  os.makedirs(path,exist_ok=True)

  files = glob.glob(path+"/*")
  for f in files:
    os.remove(f)

def clean()  :
  D=doc_dir
  files = glob.glob(D + "/*.json")
  for f in files:
    os.remove(f)
  files = glob.glob(D + "/*_cloud.pdf")
  for f in files:
    os.remove(f)

# tests to run

def nlp_test() :
  to_json('examples/test.txt', 'examples/temp.json')
  show_extract('examples/test.txt')

def mtest() :
  fname = 'examples/summary.txt'
  t=Talker(from_file=fname)
  db=t.db
  for m in materialize(db) :
    lemmas,words,tags,ners,rels,svos,deps,comps = m
    #pprint.pprint(rels)
    #pprint.pprint(svos)
    pprint.pprint(comps)
    print('')

def stest() :
  fname = 'examples/geo.txt'
  for svo in svos(fname) :
    print(svo)


def ttest() :
  fname='examples/test'
  run_with(fname,query=True,show=False)

def do(qf) :
    df=qf.replace("_quest.txt","")
    run_with(df,query=True,show=True)

def ftest() :
  do('examples/test_quest.txt')

def go()  :
  D=doc_dir
  files = sorted(glob.glob(D + "/*_quest.txt"))
  for qf in files:
    df=qf.replace("_quest.txt","")
    run_with(df,query=True,show=True)

if __name__== "__main__" :
  #nlp_test()
  #go()
  #ttest()
  #mtest()
  #mtest()
  ftest()
  pass
