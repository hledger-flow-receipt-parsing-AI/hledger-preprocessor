items = [
    "abbonement.monthly.phone",
    "abbonement.monthly.rent",
    "wallet.physical",
    "withdrawl.euro.pound",
]


from collections import defaultdict


def tree():
    return defaultdict(tree)


root = tree()

for path in items:
    parts = path.split(".")
    cur = root
    for p in parts:
        cur = cur[p]


def dump(node, indent=0):
    pad = "  " * indent
    for k in sorted(node.keys()):
        if node[k]:
            print(f"{pad}{k}:")
            dump(node[k], indent + 1)
        else:
            print(f"{pad}{k}: {{}}")


dump(root)
