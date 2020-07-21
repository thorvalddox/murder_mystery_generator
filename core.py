import networkx as nx
from random import sample, choice, random
from itertools import product
from types import SimpleNamespace
import names
from tabulate import tabulate

rooms = ['Ballroom', 'Lounge', 'Hall', 'Study', 'Library', 'Billiart Room', 'Conservatory', 'Kitchen', 'Dining Room']


class Group:
    all_ = []

    def __init__(self,vals):
        self.properties = list(vals)
        self.index = len(self.all_)
        self.all_.append(self)

    def create(self,vals):
        self.properties.extend(vals)


    def __iter__(self):
        for i,_ in enumerate(self.properties):
            yield GroupObject(self.index,i)



class GroupObject:
    def __init__(self, groupindex, objectindex):
        self.__dict__['groupindex'] = groupindex
        self.__dict__['objectindex'] = objectindex

    def __hash__(self):
        return hash((self.groupindex, self.objectindex))

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()

    def parent(self):
        return Group.all_[self.groupindex]

    def __getattr__(self,value):
        return Group.all_[self.groupindex].properties[self.objectindex][value]

    def __setattr__(self, key, value):
        Group.all_[self.groupindex].properties[self.objectindex][key] = value

    def __repr__(self):
        s = Group.all_[self.groupindex].properties[self.objectindex]
        return f"<<{s}>>"


class Plot:
    def __init__(self, np, nr, nt):
        self.people = Group(dict(name=names.get_full_name(), alive=True, guilty=False) for _ in range(np))
        self.rooms = Group(dict(name=n) for n in sample(rooms, nr))
        self.times = Group(dict(name=f"{i + 12}:00", index=i) for i in range(nt))
        self.pools = {k: set(self.people) for k in self.times}
        self.events = Group(dict(loc=r, moment=t, type='', attending=set(), claiming=set()) for r in self.rooms
                       for t in self.times)

        self.create_murder()
        self.create_crime('thief', 1, 3)
        self.create_crime('affair', 2, 2)
        self.distribute_all()

    def get_free_event(self):
        return choice([x for x in self.events if not x.type])

    def fill_event(self, event, truthful):
        pool = self.pools[event.moment]
        person = sample(pool, 1)[0]
        pool.remove(person)
        event.attending.add(person)
        if truthful:
            event.claiming.add(person)
        else:
            cev = choice([x for x in self.events if x.moment == event.moment and x != event])
            cev.claiming.add(person)

    def distribute_all(self):
        for t in self.times:
            pool = self.pools[t]
            events = [x for x in self.events if not x.type and x.moment == t]
            while pool:
                event = choice(events)
                self.fill_event(event, True)

    def create_crime(self, tp, np, dupl=1):
        for _ in range(dupl):
            event = self.get_free_event()
            event.type = tp

            for __ in range(np):
                self.fill_event(event, False)
            print(tp,event.moment,event.loc, event.attending)

    def create_murder(self):
        event = self.get_free_event()
        victim, murderer = sample(set(self.people), 2)
        event.type = 'murder'
        victim.alive = False
        murderer.guilty = True
        event.attending.add(victim)
        event.attending.add(murderer)
        self.pools[event.moment].remove(murderer)
        for after in self.times:
            if after.index > event.moment.index:
                self.pools[after].remove(victim)


class Investigate:
    accLocMemory = 1.0
    accDna = 0.5
    accPerMemory = 0.5
    accPerHearsay = 0.2

    def __init__(self, plot):
        self.plot = plot
        self.data = {}
        self.gather_all()

    def gather(self, dp, gen):
        h = next(gen)
        self.data[dp] = (list(gen), h)

    def gather_all(self):
        self.gather("victim", self.victim())
        self.gather("dna", self.dna())
        self.gather("claims", self.claims())
        self.gather("alibi", self.alibi())
        self.gather("smart lights", self.smart_lights())
        self.gather("$crimes",self.crimes())


    def print_properties(self,sol=False):
        for dp in self.data:
            if bool(sol) != dp.startswith('$'):
                continue
            yield ''
            yield dp
            yield '-' * len(dp)

            yield tabulate(sorted(list(self.data[dp][0])), headers=self.data[dp][1])

    def victim(self):
        yield "victim",
        for x in self.plot.people:
            if not x.alive:
                yield x.name,

    def crimes(self):
        yield "time", "room","crime", "person"
        for event in self.plot.events:
            if event.type:
                for p in event.attending:
                    if p.alive:
                        yield event.moment.name, event.loc.name, event.type, p.name


    def dna(self):
        yield "room", "person"
        dna = {k: list() for k in self.plot.rooms}
        for event in self.plot.events:
            for p in event.attending:
                if random() < self.accDna:
                    dna[event.loc].append(p)
        for x, pp in dna.items():
            for p in set(pp):
                yield x.name, p.name

    def claims(self):
        yield  "time", "room", "person",
        for event in self.plot.events:
            print(event.claiming)
            for p in event.claiming:
                if random() < self.accLocMemory and p.alive:
                    yield event.moment.name, event.loc.name, p.name

    def alibi(self):
        yield "time", "room", "witness","spotted",
        for event in self.plot.events:
            for witness in event.claiming:
                real = witness in event.attending
                if real:
                    for spotted in event.attending:
                        if random() < self.accPerMemory and witness != spotted:
                            yield event.moment.name, event.loc.name, witness.name, spotted.name,
                else:
                    for spotted in event.claiming:
                        if random() < self.accPerHearsay and witness != spotted:
                            yield event.moment.name, event.loc.name, witness.name, spotted.name,

    def smart_lights(self):
        yield "time","room","status"
        for event in self.plot.events:
            if event.attending:
                yield event.moment.name, event.loc.name,"on"
            else:
                yield event.moment.name, event.loc.name,"off"





p = Plot(6, 3, 5)

i = Investigate(p)
with open('report.txt','w') as file:
    for x in i.print_properties():
        file.write(x)

with open('solution.txt', 'w') as file:
    for x in i.print_properties():
        file.write(x)

print()

