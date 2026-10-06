"""Chemical names for atoms and bonds of a small molecule, from its connectivity and total charge.

Advisor requirement: a chemistry question names chemical entities (functional group, bond type), not arbitrary row
pairs. Steps:
1. Bond orders. Each atom has allowed valences (C 4; N 3, or 4 as N+; O 2, or 1 as O-; S 2/4/6; Si 4; halogens 1;
   H 1). Every assignment of single/double/triple orders that gives every atom an allowed valence and the molecule its
   stated total charge is enumerated, component by component of the unsaturated subgraph (backtracking). A bond whose
   order differs between assignments is 'aromatic' when both atoms are in a six-membered ring, else 'delocalized'
   (e.g. carboxylate C-O). Among assignments with the stated charge, those with the fewest formally charged atoms are
   kept. Connectivity alone cannot tell a dication from its neutral quinoid form (methyl viologen),
   hence the stated charge (templates/structures.json, from the source's chemical name).
2. Atom roles from bond orders, neighbours and hydrogen count (methyl carbon, thiourea carbon, sulfonyl oxygen,
   ammonium nitrogen, ...). An atom no rule recognises gets None, and enumerators skip questions that need it.
Uses the same covalent-radius graph as the families (kit.bond_graph).
"""
import itertools
from . import kit

VALENCE = {'C': (4,), 'N': (3, 4), 'O': (2, 1), 'S': (2, 4, 6), 'Si': (4,), 'F': (1,), 'Cl': (1,), 'Br': (1,), 'I': (1,),
           'H': (1,), 'P': (3, 5)}
ORDER_WORD = {1: 'single', 2: 'double', 3: 'triple', 'aromatic': 'aromatic', 'delocalized': 'delocalized'}
SYMBOL = {1: '–', 2: '=', 3: '≡', 'aromatic': '–', 'delocalized': '–'}
MAX_SOLUTIONS = 20000


def atom_charge(element, total):
    return 1 if element == 'N' and total == 4 else -1 if element == 'O' and total == 1 else 0


def rings(elements, edges):
    """Smallest ring size through each heavy atom (None if acyclic): for each neighbour j of i, the shortest path from j
    back to i that avoids the bond i-j, plus one."""
    heavy = [i for i, e in enumerate(elements) if e != 'H']
    nb = {i: [j for j in kit.neighbors(edges, i) if elements[j] != 'H'] for i in heavy}
    size = {}
    for i in heavy:
        best = None
        for j in nb[i]:
            dist, frontier = {j: 0}, [j]
            while frontier and i not in dist:
                nxt = []
                for x in frontier:
                    for y in nb[x]:
                        if (x, y) in ((i, j), (j, i)) or y in dist:
                            continue
                        dist[y] = dist[x] + 1
                        nxt.append(y)
                frontier = nxt
            if i in dist:
                best = dist[i] + 1 if best is None else min(best, dist[i] + 1)
        size[i] = best
    return size


def bond_orders(elements, edges, charge):
    """{(a, b): set of possible orders} for every bond, consistent with valences and the total charge."""
    n = len(elements)
    degree = [len(kit.neighbors(edges, i)) for i in range(n)]
    spare = [max(VALENCE[e]) - degree[i] for i, e in enumerate(elements)]
    if any(s < 0 for s in spare):
        raise ValueError('Atom exceeds its maximum valence')
    open_bonds = sorted((a, b) for a, b in edges if spare[a] > 0 and spare[b] > 0)
    # Atoms outside the unsaturated subgraph keep total = degree.
    fixed_charge = 0
    in_open = {x for bond in open_bonds for x in bond}
    for i, e in enumerate(elements):
        if i not in in_open:
            if degree[i] not in VALENCE[e]:
                raise ValueError('No allowed valence for atom %d' % (i + 1))
            fixed_charge += atom_charge(e, degree[i])
    # Connected components of the unsaturated subgraph, solved independently.
    parent = {x: x for x in in_open}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in open_bonds:
        parent[find(a)] = find(b)
    groups = {}
    for bond in open_bonds:
        groups.setdefault(find(bond[0]), []).append(bond)
    per_component = []
    for bonds in groups.values():
        atoms = sorted({x for bond in bonds for x in bond})
        incident = {x: [k for k, bond in enumerate(bonds) if x in bond] for x in atoms}
        last = {x: max(incident[x]) for x in atoms}
        extra = {x: 0 for x in atoms}
        found = {}
        orders = [0] * len(bonds)

        def search(k):
            if len(found) > MAX_SOLUTIONS:
                raise ValueError('Too many bond-order assignments')
            if k == len(bonds):
                charges = [atom_charge(elements[x], degree[x] + extra[x]) for x in atoms]
                found.setdefault((sum(charges), sum(map(abs, charges))), []).append(tuple(orders))
                return
            a, b = bonds[k]
            for o in (0, 1, 2):
                if extra[a] + o > spare[a] or extra[b] + o > spare[b]:
                    break
                extra[a] += o
                extra[b] += o
                orders[k] = o
                done = [x for x in (a, b) if last[x] == k]
                if all(degree[x] + extra[x] in VALENCE[elements[x]] for x in done):
                    search(k + 1)
                extra[a] -= o
                extra[b] -= o
        search(0)
        if not found:
            raise ValueError('No valence-consistent bond orders')
        per_component.append((bonds, found))
    # Keys are (net charge, number of charged atoms). Among assignments with the stated total charge keep those with
    # the fewest formally charged atoms (no zwitterionic resonance forms such as S=N+ / S-O- for a sulfonamide).
    combos = [c for c in itertools.product(*[sorted(f) for _, f in per_component])
              if fixed_charge + sum(q for q, _ in c) == charge]
    if not combos:
        raise ValueError('No bond-order assignment matches the stated charge %+d' % charge)
    fewest = min(sum(n for _, n in c) for c in combos)
    combos = [c for c in combos if sum(n for _, n in c) == fewest]
    result = {tuple(sorted(e)): {1} for e in edges}
    for k, (bonds, found) in enumerate(per_component):
        allowed = {c[k] for c in combos}
        for j, bond in enumerate(bonds):
            result[bond] = {1 + s[j] for q in allowed for s in found[q]}
    return result


class Molecule:
    def __init__(self, elements, points, charge=0):
        self.elements, self.points = elements, points
        self.edges = kit.bond_graph(elements, points)
        self.ring = rings(elements, self.edges)
        self.order = {}
        for (a, b), values in bond_orders(elements, self.edges, charge).items():
            if len(values) == 1:
                self.order[(a, b)] = next(iter(values))
            else:
                self.order[(a, b)] = 'aromatic' if self.ring.get(a) == 6 and self.ring.get(b) == 6 else 'delocalized'
        self.names = {i: self._role(i) for i in range(len(elements))}

    def bond_order(self, a, b):
        return self.order[(min(a, b), max(a, b))]

    def nb(self, i, element=None):
        return [j for j in kit.neighbors(self.edges, i) if element is None or self.elements[j] == element]

    def heavy(self, i):
        return [j for j in self.nb(i) if self.elements[j] != 'H']

    def hcount(self, i):
        return len(self.nb(i, 'H'))

    def double_to(self, i, element):
        return [j for j in self.nb(i, element) if self.bond_order(i, j) == 2]

    def unsaturated(self, i):
        return any(self.bond_order(i, j) != 1 for j in self.heavy(i))

    def carboxylate(self, c):
        terminal = [j for j in self.nb(c, 'O') if len(self.nb(j)) == 1]
        return self.elements[c] == 'C' and len(terminal) == 2

    def _role(self, i):
        e, h, heavy = self.elements[i], self.hcount(i), self.heavy(i)
        orders = {self.bond_order(i, j) for j in heavy}
        where = ' in the %d-membered ring' % self.ring[i] if self.ring.get(i) else ''
        if e == 'H':
            return None
        if e == 'C':
            if self.double_to(i, 'S'):
                ns = len(self.nb(i, 'N'))
                return 'thiourea carbon (C=S)' if ns == 2 else 'thioamide carbon (C=S)' if ns == 1 else 'thiocarbonyl carbon'
            if self.carboxylate(i):
                return 'carboxylate carbon (COO⁻)'
            if self.double_to(i, 'O'):
                return 'carbonyl carbon (C=O)'
            if self.double_to(i, 'N'):
                return 'imine carbon (C=N)' + where
            if 'aromatic' in orders:
                return 'aromatic carbon' + where
            if 'delocalized' in orders:
                return None
            if 3 in orders:
                return 'sp carbon (triple bond)'
            if 2 in orders:
                return 'alkene carbon (C=C)' + where
            return {3: 'methyl carbon (CH3)', 2: 'methylene carbon (CH2)', 1: 'methine carbon (CH)', 0: 'quaternary carbon'}[h] + where
        if e == 'N':
            if len(self.nb(i)) == 4:
                return {3: 'ammonium nitrogen (NH3+)', 0: 'quaternary ammonium nitrogen (N+)'}.get(h, 'ammonium nitrogen (N+)')
            if 'aromatic' in orders and h == 0:
                return 'pyridinium nitrogen (N+)' + where
            if 2 in orders:
                return 'imine nitrogen (C=N)' + where
            if any(self.elements[j] == 'S' and len(self.double_to(j, 'O')) == 2 for j in heavy):
                return 'sulfonamide nitrogen (N%s)' % {2: 'H2', 1: 'H', 0: ''}[h]
            if any(self.elements[j] == 'C' and self.double_to(j, 'S') for j in heavy):
                return {2: 'thioamide NH2 nitrogen', 1: 'thioamide N–H nitrogen', 0: 'thioamide nitrogen'}[h] + where
            if any(self.unsaturated(j) for j in heavy):
                return {2: 'NH2 nitrogen bonded to an sp2 carbon', 1: 'N–H nitrogen bonded to an sp2 carbon',
                        0: 'nitrogen bonded to an sp2 carbon'}[h] + where
            return {2: 'primary amino nitrogen (NH2)', 1: 'secondary amine nitrogen (NH)', 0: 'tertiary amine nitrogen'}[h] + where
        if e == 'O':
            if len(heavy) == 1 and h == 0 and self.carboxylate(heavy[0]):
                return 'carboxylate oxygen (COO⁻)'
            if len(heavy) == 1 and self.bond_order(i, heavy[0]) == 2:
                return 'sulfonyl oxygen (S=O)' if self.elements[heavy[0]] == 'S' else 'carbonyl oxygen (C=O)'
            if len(heavy) == 1 and h == 1:
                return 'sulfonic acid hydroxyl oxygen (S–OH)' if self.elements[heavy[0]] == 'S' else 'hydroxyl oxygen (OH)'
            if len(heavy) == 1 and h == 0 and self.elements[heavy[0]] == 'S':
                return 'sulfonate oxygen (S–O⁻)'
            if len(heavy) == 2 and h == 0:
                return 'ether oxygen (C–O–C)' + where
            return None
        if e == 'S':
            if self.double_to(i, 'C'):
                return 'thiocarbonyl sulfur (C=S)'
            terminal_o = [j for j in self.nb(i, 'O') if len(self.nb(j)) == 1]
            if len(heavy) == 4 and len(terminal_o) >= 2:
                if len(terminal_o) == 3:
                    return 'sulfonate sulfur (SO3⁻)'
                rest = sorted(self.elements[j] for j in heavy if j not in terminal_o)
                if 'N' in rest:
                    return 'sulfonamide sulfur (SO2)'
                if 'O' in rest:
                    return 'sulfonic acid sulfur (SO3H)'
                return 'sulfone sulfur (SO2)' + where
            if len(heavy) == 2 and orders == {1}:
                return 'ring sulfur' + where if self.ring.get(i) else 'thioether sulfur (C–S–C)'
            return None
        if e == 'Si':
            return 'silicon of the trimethylsilyl group' if sum(self.hcount(j) == 3 for j in heavy) == 3 else None
        return None

    def atom(self, i):
        """'C5, the thiourea carbon (C=S)' or None."""
        return None if self.names[i] is None else '%s%d, the %s' % (self.elements[i], i + 1, self.names[i])

    def bond_word(self, a, b):
        o = self.bond_order(a, b)
        return '%s %s%s%s bond' % (ORDER_WORD[o], self.elements[a], SYMBOL[o], self.elements[b])

    def bond(self, a, b):
        """'the double C=S bond between C5, the thiourea carbon (C=S), and S6, the thiocarbonyl sulfur (C=S)' or None."""
        if self.names[a] is None or self.names[b] is None:
            return None
        return 'the %s between %s, and %s' % (self.bond_word(a, b), self.atom(a), self.atom(b))

    def angle(self, a, v, b):
        """Description of the angle a-v-b at vertex v, or None."""
        if None in (self.names[a], self.names[v], self.names[b]):
            return None
        return 'the angle at %s, between its %s to %s, and its %s to %s' % (
            self.atom(v), self.bond_word(v, a), self.atom(a), self.bond_word(v, b), self.atom(b))

    def hydrogen(self, h):
        """'H10 is bonded to C1, the methyl carbon (CH3)' or None."""
        [parent] = self.nb(h)
        if self.names[parent] is None:
            return None
        return 'H%d is bonded to %s' % (h + 1, self.atom(parent))
