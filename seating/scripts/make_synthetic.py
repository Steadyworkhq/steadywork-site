"""Generate synthetic (fictional) guest lists for development and samples.

All names are randomly combined from common given names and surnames; any
resemblance to real people is coincidental. No real customer data is used.
"""
import csv, random, sys, os

FIRST = ["Ava","Jonah","Mía","Lucas","Zoë","Mateo","Chloé","Noah","Amélie","Liam","Sofía","Ethan","Inés","Oliver","Léa","Elijah",
         "Freya","Kai","Nadia","Theo","Priya","Arjun","Hana","Kenji","Siobhán","Seán","Björn","Åsa","Søren","Małgorzata","Zoltán",
         "Ngozi","Chidi","Aroha","Tāne","Fatima","Omar","Yusuf","Leila","Dmitri","Anya","Grace","Henry","Isla","Jack","Rosa","Diego",
         "Camille","Hugo","Marisol","Tomás","Joaquín","Renée","François","Dagný","Þór","Gülşen","Ştefan","Nguyễn","Trinh","Ayesha"]
LAST = ["Garcia","Smith","Nguyen","O'Brien","MacDonald","López","Müller","Østergaard","Kowalczyk","Szabó","Haddad","Okafor","Patel",
        "Tanaka","Johansson","Rossi","Dubois","Fernández","Ní Bhriain","van der Berg","de la Cruz","Abernathy","Whitfield","Castellanos",
        "Papadopoulos","Kim","Wójcik","Novák","Ibáñez","Ó Súilleabháin","Bergström","Yılmaz","Popescu","Țepeș","Hwang","Moreau","Carter"]
LONG = ["Maximiliana Alejandra Montgomery-Castellanos","Bartholomew Fitzgerald-Worthington III","Dr. Anastasia Konstantinopoulou-Richardson",
        "Siobhán Ní Bhriain Ó Súilleabháin","Jean-Baptiste Émile de Saint-Exupéry-Lefèvre"]

def make(n, tables, named=False, seed=1, dup_pairs=1, missing=0, long_names=2):
    rnd = random.Random(seed)
    names = set()
    rows = []
    labels = tables if named else [str(i) for i in range(1, tables + 1)]
    while len(rows) < n - long_names - dup_pairs:
        nm = f"{rnd.choice(FIRST)} {rnd.choice(LAST)}"
        if nm in names: continue
        names.add(nm); rows.append(nm)
    rows += LONG[:long_names]
    out = []
    for i, nm in enumerate(rows):
        out.append([nm, labels[i % len(labels)]])
    for k in range(dup_pairs):
        # A legitimate shared name (e.g. two cousins) at different tables.
        out.append([out[k][0], labels[(k + 3) % len(labels)]])
    for k in range(missing):
        out[-(k + 5)][1] = ""
    rnd.shuffle(out)
    return out

def write(path, rows, header=("Guest Name", "Table")):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)

if __name__ == "__main__":
    d = sys.argv[1] if len(sys.argv) > 1 else "samples"
    os.makedirs(d, exist_ok=True)
    write(f"{d}/small-numbered-64.csv", make(64, 8, seed=3, dup_pairs=1, long_names=2))
    write(f"{d}/medium-named-120.csv", make(120, ["Head Table","Rosemary","Sage","Thyme","Lavender","Juniper","Fern","Olive","Laurel","Willow","Magnolia","Cedar","Birch","Ivy"], named=True, seed=7, long_names=3))
    write(f"{d}/large-numbered-250.csv", make(250, 25, seed=11, dup_pairs=2, long_names=5))
    write(f"{d}/messy-with-missing.csv", make(40, 5, seed=5, dup_pairs=1, missing=3))
    print("ok")
