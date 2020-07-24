import json
from types import SimpleNamespace

with open('report.json') as file:
    clues = json.load(file)

from tabulate import tabulate


class ClueSolver:
    def __init__(self, clues):
        self.reorganise(clues)
        self.names = sorted(list(set(self.extract_names())))
        self.rooms = sorted(list(set(self.extract_rooms())))
        self.times = sorted(list(set(self.extract_times())))
        self.victim = self.names.index(self.clues['victim'])

        self.build_prcomb()
        self.build_ptcomb()
        self.build_rtcomb()
        self.count_claims()
        self.incon_inactive()
        for _ in range(20):
            self.incon_count()
            self.con_real_locations()
            self.incon_direct_count()

    def reorganise(self, clues):
        self.clues = {}
        for x in clues:
            if 'clue' in x:
                s = x.copy()
                clue = s['clue']
                del s['clue']
                if clue not in self.clues:
                    self.clues[clue] = []
                self.clues[clue].append(SimpleNamespace(**s))

    def extract_names(self):
        for x in self.clues['witness']:
            yield x.name
        for x in self.clues['victim']:
            yield x.name

    def extract_rooms(self):
        for x in self.clues['witness']:
            yield x.room

    def extract_times(self):
        for x in self.clues['witness']:
            yield x.time

    def get_room(self, x):
        return self.rooms.index(x.room)

    def get_person(self, x):
        return self.names.index(x.name)

    def get_time(self, x):
        return self.times.index(x.time)


    def build_rtcomb(self):
        self.rt = {}
        for x in self.clues['light']:
            self.rt[self.get_room(x), self.get_time(x)] = dict(active=x.status == "on")

    def build_ptcomb(self):
        self.pt = {}
        for x in self.clues['witness']:
            self.pt[self.get_person(x), self.get_time(x)] = dict(
                claim=self.get_room(x),
                real=None,
                claimsee=[self.names.index(y) for y in x.others])
            if 'total' in x.__dict__:
                self.pt[self.get_person(x), self.get_time(x)]['number'] = x.total + len(x.others) + 1

    def build_prcomb(self):
        self.pr = {}
        for x in self.clues['dna']:
            self.pr[self.get_person(x), self.get_room(x)] = dict(dna=True)

    def get_rooms_tcr(self, tm, crime=False):
        for (r, t), s in self.rt.items():
            if t == tm and s['active'] and s.get('iscrime', crime) == crime:
                yield r

    def count_claims(self):
        for (r, t), s in self.rt.items():
            s['cc'] = []
            s['cn'] = []
            for (p2, t2), s2 in self.pt.items():
                if not t == t2:
                    continue
                if not s2['claim'] == r:
                    continue
                if 'number' in s2:
                    s['cn'].append(s2['number'])
                s['cc'].append(p2)

    def mark_lying(self, time, person):
        print(f"{self.names[person]} was lying about whereabouts at {self.times[time]}")
        if not mark_boolean(self.pt[person, time], 'lying', True):
            return
        self.pt[person, time]['lying'] = True
        self.lookup_real_location(time, person)

    def con_real_locations(self):
        for (p, t), s in self.pt.items():
            if s.get('lying'):
                self.lookup_real_location(t, p)
            else:
                self.direct_real_location(t,p)

    def lookup_real_location(self, time, person):
        tcr = list(self.get_rooms_tcr(time, True))
        if len(tcr) == 1:
            self.mark_real_loc(time, person, tcr[0])

    def direct_real_location(self, time, person):
        tcr = list(self.get_rooms_tcr(time, True))
        if len(tcr) == 0:
            self.mark_truthful(time, person)

    def mark_real_loc(self, time, person, room):
        self.pt[person, time]['realloc'] = room
        if mark_boolean(self.rt[room, time], 'iscrime', True):
            self.mark_room_crime(time, room)

    def mark_truthful(self, time, person):
        print(f"{self.names[person]} was truthful about whereabouts at {self.times[time]}")
        if mark_boolean(self.pt[person, time], 'lying', False):
            self.pt[person, time]['realloc'] = self.pt[person, time]['claim']
            for x in self.pt[person, time]['claimsee']:
                self.mark_truthful(time, x)
            self.mark_room_safe(time, self.pt[person, time]['claim'])

    def mark_room_safe(self, time, room):
        print(f"{self.rooms[room]} was safe at {self.times[time]}")
        mark_boolean(self.rt[room, time], 'iscrime', False)

    def mark_room_crime(self, time, room):
        print(f"{self.rooms[room]} was unsafe or inactive at {self.times[time]}")
        for x in self.rt[room, time]['cc']:
            self.mark_lying(time, x)

    def incon_inactive(self):
        for (r, t), s in self.rt.items():
            if not s['active']:
                self.mark_room_crime(t, r)

    def incon_count(self):
        for (r, t), s in self.rt.items():
            ts = set(s['cn'])
            clg = len(s['cc'])
            assert len(ts) <= 2
            ts = ts - {clg, clg + 1}
            if ts:
                s['real_count'] = list(ts)[0]
                self.mark_room_safe(t, r)
        for (p, t), s in self.pt.items():
            if 'real_count' in self.rt[s['claim'], t] and 'number' in s:
                if self.rt[s['claim'], t]['real_count'] != s['number']:
                    self.mark_lying(t, p)
                else:
                    self.mark_truthful(t, p)

    def incon_direct_count(self):
        for (r, t), s in self.rt.items():
            if 'realcount' in s:
                s2 = [self.pt[p, t] for p in s['cn']]
                lying = [p for p in s2 if p.get('lying')]
                truthful = [p for p in s2 if not p.get('lying', True)]
                unknown = [p for p in s2 if not 'lying' in p]
                if len(truthful) == s['realcount']:
                    for x in unknown:
                        self.mark_lying(t, x)
                if len(truthful) + len(unknown) == s['realcount']:
                    for x in unknown:
                        self.mark_truthful(t, x)

    def print_loc(self):
        return tabulate([[str(t)] +
                         [
                             ''.join(x[0] if self.pt.get((i, t),{}).get('realloc') == r else
                                     x[0].lower() if self.pt.get((i, t), {}).get('claim') == r else
                                     ('.' if 'realloc' in self.pt.get((i, t),{}) else '?')
                                     for i, x in enumerate(self.names))

                             for r in range(len(self.rooms))
                         ]

                         for t in range(len(self.times))
                         ], headers=[''] + self.rooms)


def mark_boolean(dict_, field, val):
    if field not in dict_:
        dict_[field] = val
        return True
    else:
        assert dict_[field] == val, "Field has already opposite value"
        return False


print(ClueSolver(clues).print_loc())
