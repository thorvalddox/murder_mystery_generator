import networkx as nx
from random import sample, choice, random
from itertools import product
from types import SimpleNamespace
import names
from tabulate import tabulate
import inflect
import json

rooms = ['Dining Room', "Living Room", 'Kitchen', 'Hallway', 'Study', 'Cellar', 'Lounge', 'Rooftop', 'Library']
ie = inflect.engine()


class Group:
    all_ = []

    def __init__(self, vals):
        self.properties = list(vals)
        self.index = len(self.all_)
        self.all_.append(self)

    def create(self, vals):
        self.properties.extend(vals)

    def __iter__(self):
        for i, _ in enumerate(self.properties):
            yield GroupObject(self.index, i)


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

    def __getattr__(self, value):
        return Group.all_[self.groupindex].properties[self.objectindex][value]

    def __setattr__(self, key, value):
        Group.all_[self.groupindex].properties[self.objectindex][key] = value

    def __repr__(self):
        s = Group.all_[self.groupindex].properties[self.objectindex]
        return f"<<{s}>>"


def generate_name(index):
    firstletter = 'abcdefghijklmnoprstuvwyz'[index]
    name = ''
    while not name.lower().startswith(firstletter.lower()):
        name = names.get_full_name()
    return name


class Plot:
    def __init__(self, np, nr, nt, thiefs, affairs, sms, meetings):
        self.people = Group(dict(name=generate_name(s), alive=True, guilty=False) for s in range(np))
        self.rooms = Group(dict(name=f'the {n.lower()}') for n in rooms[:nr])
        self.times = Group(dict(name=f"{i + 12}:00", index=i) for i in range(nt))
        self.pools = {k: set(self.people) for k in self.times}
        self.events = Group(dict(loc=r, moment=t, type='', attending=set(), claiming=set()) for r in self.rooms
                            for t in self.times)

        self.create_murder()
        self.create_crime('thief', 1, thiefs)
        self.create_crime('affair', 2, affairs)
        self.create_crime('secret meeting', 3, sms)
        self.create_special('meeting', 0, meetings)
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
        return person

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
            print(tp, event.moment, event.loc, event.attending)

    def create_special(self, tp, np, dupl=1):
        for _ in range(dupl):
            event = self.get_free_event()
            event.type = tp
            if np:
                for __ in range(np):
                    self.fill_event(event, True)
            else:
                while self.pools[event.moment]:
                    self.fill_event(event, True)
            print(tp, event.moment, event.loc, event.attending)

    def create_murder(self):
        event = self.get_free_event()
        victim = self.fill_event(event, True)
        murderer = self.fill_event(event, False)
        event.claiming.remove(victim)
        event.type = 'murder'
        victim.alive = False
        murderer.guilty = True
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
        self.gather("$crimes", self.crimes())

    def print_properties(self, sol=False):
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
        yield "time", "room", "crime", "person"
        for event in self.plot.events:
            for p in event.attending:
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
        yield "time", "room", "person",
        for event in self.plot.events:
            print(event.claiming)
            for p in event.claiming:
                if random() < self.accLocMemory and p.alive:
                    yield event.moment.name, event.loc.name, p.name

    def alibi(self):
        yield "time", "room", "witness", "spotted",
        for event in self.plot.events:
            for witness in event.claiming:
                if not witness.alive:
                    continue
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
        yield "time", "room", "status"
        for event in self.plot.events:
            if event.attending:
                yield event.moment.name, event.loc.name, "on"
            else:
                yield event.moment.name, event.loc.name, "off"


def subtitled(string):
    return '\n' + string + '\n' + '-' * len(string)


class WitnessReport:
    accLocMemory = 1.0
    accDna = 0.5
    accPerMemory = 0.5
    accPerHearsay = 0.2
    accNumberMemory = 0.4

    def __init__(self, plot):
        self.plot = plot
        self.data = []

    def dna(self, witness):
        yield subtitled(f'dna report of {witness.name}')
        dna = set()
        for event in self.plot.events:
            if witness in event.attending:
                if random() < self.accDna:
                    dna.add(event.loc)
        rooms = ie.join([x.name for x in dna])
        for x in dna:
            self.data.append(dict(clue='dna', name=witness.name, room=x.name))
        if dna:
            yield "This persons dna was found in the following rooms: {}".format(rooms)
        else:
            yield "This persons dna was found nowhere"

    def write(self):
        yield subtitled("victim name")
        for x in self.plot.people:
            if not x.alive:
                victim = x
                yield x.name
        self.data.append(dict(clue='victim',name=victim.name))

        yield from self.dna(victim)

        yield subtitled('inventory report')
        rooms = set()
        for event in self.plot.events:
            if event.type == 'thief':
                rooms.add(event.loc)
        for x in rooms:
            self.data.append(dict(clue='thief', room=x.name))
        rooms = ie.join([x.name for x in rooms])
        if rooms:
            yield 'There is art missing from the following rooms: {}'.format(rooms)
        else:
            yield 'N/A'

        for witness in self.plot.people:
            if not witness.alive:
                continue
            yield subtitled(f"Witness statement of {witness.name}")
            events = sorted([x for x in self.plot.events if witness in x.claiming], key=lambda x: x.moment.index)

            for event in events:

                yield f"At {event.moment.name} I was in {event.loc.name}."
                d = dict(clue='witness',name=witness.name, room=event.loc.name,time=event.moment.name,others=[])
                real = witness in event.attending
                if real:
                    wouldsay = list(event.attending)
                    wouldsay.remove(witness)
                    memory = [x for x in wouldsay if random() < self.accPerMemory]
                else:
                    wouldsay = list(event.claiming)
                    wouldsay.remove(witness)
                    memory = [x for x in wouldsay if random() < self.accPerHearsay]
                number = len(wouldsay) - len(memory)
                memNum = self.accNumberMemory > random()

                people_ = ie.join(sorted([x.name for x in memory]))
                people = "{} {}".format(ie.number_to_words(number, zero="no"), ie.plural("other person", number))
                verb = 'was' if number == 1 else 'were'
                if memory:
                    d['others'].extend(x.name for x in memory)
                    yield f"I met with {people_}."
                    if memNum:
                        yield f"{people} {verb} there.".capitalize()
                else:
                    if memNum:
                        yield f"In the same room, there {verb} {people}."
                    else:
                        yield "I don't remember who else was there."
                if memNum:
                    d['total'] = number
                self.data.append(d)
                yield ''
            yield from self.dna(witness)
        yield subtitled(f"Smart lights log")
        for event in self.plot.events:
            status = 'on' if event.attending else 'off'
            yield f'At {event.moment.name} the lights in {event.loc.name} where {status}'
            self.data.append(dict(clue='light',time=event.moment.name, room=event.loc.name, status=status))



p = Plot(6, 3, 5, 2, 1, 1, 3)

i = Investigate(p)
w = WitnessReport(p)

with open('report.txt', 'w') as file:
    for line in w.write():
        file.write(line + '\n')

with open('report.json', 'w') as file:
    json.dump(w.data, file, indent=1)

with open('solution.txt', 'w') as file:
    for line in i.print_properties(True):
        file.write(line + '\n')

print()
