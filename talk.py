from collections import defaultdict
import subprocess
from pathlib import Path
import json
import math
import networkx as nx
from graphviz import Digraph as DotGraph

from params import *
from nlp import *
from nltk.corpus import stopwords

stop_words=set(stopwords.words('english'))
stop_words.union({'|(){}[]'})
client = NLPclient()

def tprint(*args) :
  if trace : print(*args)

def say(what) :
  print(what)
  if not quiet : subprocess.run(["say", what])

def tload(infile) :
  tprint('LOADING:',infile,'\n')
  with open(infile, 'r') as f: text = f.read()
  return digest(text)

def jload(infile) :
  with open(infile, 'r') as f:
    return json.load(f)

def jsave(infile,outfile):
  d=tload(infile)
  with open(outfile,'w') as g:
    json.dump(d,g,indent=0)


def load(fname) :
  if fname[-4:]==".txt":
    if force:
      db = tload(fname)
    else :
      jfname=fname[:-4]+".json"
      my_file = Path(jfname)
      if not my_file.is_file() :
         jsave(fname,jfname)
      db=jload(jfname)
  else:
    db = jload(fname)
  return db


def get_quests(qs) :
  if not isinstance(qs,list) :
    qfname=qs
    with open(qfname,'r') as f:
      qs = list(l.strip() for l in f)
  return qs

def get_db_and_quests(fname,quest_list_or_quest_file) :
  db=load(fname)
  qs=get_quests(quest_list_or_quest_file)
  return (db,qs)

def digest(text) :
  l2occ = defaultdict(list)
  sent_data=[]
  for i,xss in enumerate(client.extract(text)) :
    lexs,deps,ies=xss
    sent,lemma,tag,ner=[],[],[],[]
    for j,t in enumerate(lexs):
      w,l,p,n=t
      wi=len(l2occ)
      l2occ[l].append((i,j))
      sent.append(w)
      lemma.append(l)
      tag.append(p)
      ner.append(n)
    d=(tuple(sent),tuple(lemma),tuple(tag),tuple(ner),tuple(deps),tuple(ies))
    sent_data.append(d)
  #tprint('DIGESTED')
  return sent_data,l2occ

SENT,LEMMA,TAG,NER,DEP,IE=0,1,2,3,4,5

def rel_from(d):
  def to_lems(ux):
    f,t=ux
    if f>=0:
      for u in range(*ux):
        yield lemma[u]
  rs=[]
  for ts in d[IE] :
    for t in ts :
      sx, vx, ox = t
      lemma = d[LEMMA]
      sub = tuple(to_lems(sx))
      rel = tuple(to_lems(vx))
      ob = tuple(to_lems(ox))
      res = (sub, rel, ob)
      rs.append(res)
  yield tuple(rs)

def dep_from(id,d):
  deps=d[DEP]
  lemmas=d[LEMMA]
  tags=d[TAG]
  for dep in deps :
    f, r, t = dep
    if t == -1 : target,ttag=id,'SENT'
    else: target,ttag = lemmas[t],tags[t]
    res = lemmas[f],tags[f],r,target,ttag
    yield res

def deps_from(id,d) :
  return (t for t in dep_from(id,d))

def to_edges(db) :
  sent_data,l2occ=db
  for id,sd in enumerate(sent_data) :
    for dep in dep_from(id,sd):
      f,f_,r,t,t_=dep
      if r == 'punct': continue
      if f in stop_words or t in stop_words : continue
      if r in ['nsubj','dobj','iobj'] or t_[0]=='V':
        yield (t,f)
        yield (f,id)
      elif r=='ROOT' :
        yield (t,f)
      else :
        yield (f,t)

def get_avg_len(db) :
  sent_data,_=db
  lens=[len(x[LEMMA]) for x in sent_data]
  n=len(lens)
  s=sum(lens)
  return round(s/n)

def to_graph(db,personalization=None) :
  g = nx.DiGraph()
  for e in to_edges(db) :
    f,t=e
    g.add_edge(f,t)
  pr=nx.pagerank(g,personalization=personalization)
  by_rank=[(x,r) for (x,r) in pr.items()]
  by_rank.sort(key=lambda x : x[1],reverse=True)
  return g,by_rank

def ners_from(d):
  ners=[]
  for j, ner in enumerate(d[NER]):
    lemma = d[LEMMA][j]
    if ner != 'O': ners.append((lemma,ner))
  return tuple(ners)

def show_db(db) :
    sent_data,l2occ = db
    for i,d in enumerate(sent_data) :
      for trip in rel_from(d): print('TRIPLES:', trip)
      for dep in deps_from(i,d) : print('DEPENDS:',dep)
      print("NERS",ners_from(d))
    print('')

def materialize(db) :
  sent_data,l2occ= db
  for i,d in enumerate(sent_data) :
      rels=(t for t in rel_from(d))
      deps=(t for t in deps_from(i,d))
      ners=ners_from(d)
      yield tuple(d[LEMMA]),tuple(d[TAG]),ners,tuple(rels),tuple(deps)

def answer_quest(q,db) :
    sent_data,l2occ=db
    matches = defaultdict(set)
    q_sent_data,q_l2occ=digest(q)
    unknowns=[]
    for q_lemma in q_sent_data[0][LEMMA]:
       if q_lemma in stop_words or q_lemma in ".?" : continue
       ys = l2occ.get(q_lemma)
       if not ys :
         unknowns.append(q_lemma)
         continue
       for sent,pos in ys:
         matches[sent].add(q_lemma)
         #else : print('UNMATCHED LEMMA',q_lemma,q_tag,tag)
    if unknowns: tprint("UNKNOWNS:", unknowns,'\n')
    best=[]
    for (id, shared) in matches.items() :
      sent=sent_data[id][SENT]
      l=len(shared)
      ls=len(sent)
      r=l/(1+math.log(ls/(l*l)))
      best.append((r,id,shared,sent))
    best.sort(reverse=True)

    answers=[]
    for i,b in enumerate(best):
      if i >= max_answers : break
      rank, id, shared, sent = b
      answers.append((id,sent,round(rank,2),shared))
    answers.sort()
    return answers

def query(fname,qs) :
  db,qs=get_db_and_quests(fname,qs)
  if trace > 1:
    show_db(db)
  answer_with(db,qs)

def answer_with(db,qs)     :
  qs = get_quests(qs)
  if qs:
    for q in qs : interact(q,db)
  else:
    while True:
      q=input('> ')
      if not q : break
      interact(q,db)

def interact(q,db):
  tprint('----- QUERY ----\n')
  say(q)
  print('')
  for info, sent, rank, shared in answer_quest(q, db):
    print(info,end=': ')
    say(nice(sent))
    tprint('  ', shared, rank)
  print('')
  tprint('------END-------', '\n')

class Talker :
  def __init__(self,from_file,sk=5,wk=8):
    self.db=load(from_file)
    self.avg_len = get_avg_len(self.db)
    self.g,self.pr=to_graph(self.db)
    self.get_sum_and_words(sk,wk)

  def query_with(self,qs):
    qs = get_quests(qs)
    answer_with(self.db,qs)

  def get_tags(self,w):
    l2occ=self.db[1]
    sent_data=self.db[0]
    occs=l2occ.get(w)
    tags=set()
    for i,j in occs:
      tag=sent_data[i][TAG][j]
      tags.add(tag)
    return tags

  def get_sum_and_words(self,sk,wk):
    def good_sent(ws) :
      return len(ws)<=self.avg_len+2
    sents,words=[],[]
    for i  in range(len(self.pr)):
      x,r=self.pr[i]
      if sk and isinstance(x,int) :
        ws=self.db[0][x][SENT]
        if good_sent(ws) :
          sk-=1
          sents.append((x,ws))
      elif wk and isinstance(x,str) :
        for tag in self.get_tags(x) :
          if tag[0]=='N' :
            wk -= 1
            words.append(x)
            break
    sents.sort(key=lambda x: x[0])
    self.summary=[(s,nice(ws)) for (s,ws) in sents]
    self.keywords=words


  def show_summary(self):
    say('SUMMARY:')
    for s in self.summary:
      say(s)
    print('')

  def show_keywords(self):
    print('KEYWORDS:')
    print(self.keywords)
    print('')


# helpers

def nice(ws) :
  ws=[cleaned(w) for w in ws]
  sent=" ".join(ws)
  #print(sent)
  sent=sent.replace(" 's","'s")
  sent=sent.replace(" ,",",")
  sent=sent.replace(" .",".")
  sent = sent.replace('``', '"')
  sent = sent.replace("''", '"')
  return sent

def good_tag(tag,starts="NVJA"):
  c=tag[0]
  return c in starts


def showGraph(dot, show=True, file_name='textgraph.gv'):
    dot.render(file_name, view=show)

def gshow(g,file_name='textgraph.gv',show=True):
    dot = DotGraph()
    for e in g.edges():
        f, t = e
        #w = g[f][t]['weight']
        w=''
        dot.edge(str(f), str(t), label=str(w))
    dot.render(file_name, view=show)

