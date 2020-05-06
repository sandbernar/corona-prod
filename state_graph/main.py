state_dead = ("dead", "Умер")
state_infec = ("infected", "Инфицирован")
state_hosp = ("hospitalized", "Госпитализирован")
state_healthy = ("recovery", "Выздоровление")
state_is_home = ("is_home", "Домашний Карантин")
state_is_transit = ("transit", "Транзит")
state_found = ("found", "Найден")

class GraphNode:
    def __init__(self, value):
        self.value = value
        self.nodes = []
    
    def connect(self, node):
        self.nodes.append(node)

class GraphState:
    def __init__(self):
        self.start = GraphNode(1)
        self.reached_end = False
        self.location = []
        self.patient = []
        self.location_state = [state_found, state_is_transit, state_hosp, state_is_home]
        self.patient_state = [state_infec, state_healthy, state_dead]

        self.dead = GraphNode(state_dead)
        self.infec = GraphNode(state_infec)
        self.hosp = GraphNode(state_hosp)
        self.healthy = GraphNode(state_healthy)
        self.is_home = GraphNode(state_is_home)
        self.is_transit = GraphNode(state_is_transit)
        self.found = GraphNode(state_found)

        self.start.connect(self.found)
        self.start.connect(self.infec)
        self.start.connect(self.dead)
        self.found.connect(self.is_transit)
        self.found.connect(self.is_home)
        self.found.connect(self.hosp)
        self.is_transit.connect(self.hosp)
        self.is_transit.connect(self.is_home)
        self.is_home.connect(self.hosp)
        self.hosp.connect(self.is_home)
        self.infec.connect(self.healthy)
        self.infec.connect(self.dead)
        self.healthy.connect(self.infec)
        self.healthy.connect(self.dead)

        self.states = []
    
    def add(self, in_state):
        if self.reached_end:
            return False
        states = None
        if in_state in self.location_state:
            states = self.location
        elif in_state in self.patient_state:
            states = self.patient
        states.append(in_state)
        currentNode = self.start
        for state in states:
            found = False
            for node in currentNode.nodes:
                if node.value[0] == state[0]:
                    currentNode = node
                    found = True
                    if node == self.dead:
                        self.reached_end = True
                    break
            if not found:
                states.pop()
                return False
        return True

graph = GraphState()
states = [state_hosp]
for state in states:
    result = graph.add(state)
    print(state[0], result)
print(graph.patient)
print(graph.location)