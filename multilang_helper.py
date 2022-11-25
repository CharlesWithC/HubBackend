import os, sys, json

pre = "./src/languages"

if sys.argv[1] == "distribute":
    d = json.loads(open(f"{pre}/en.json","r",encoding="utf-8").read())
    k = d.keys()

    e = open(f"{pre}/en.json","r",encoding="utf-8").read().split("\n")
    b = []
    for i in range(len(e)):
        if e[i] == "":
            b.append(i)

    l = os.listdir(pre)
    for ll in l:
        if ll == "en.json":
            continue
        t = json.loads(open(f"{pre}/{ll}","r",encoding="utf-8").read())
        u = t.keys()
        v = {}
        for kk in k:
            if kk in u:
                v[kk] = t[kk]
            else:
                v[kk] = d[kk]
        g = json.dumps(v, indent=4, ensure_ascii=False).split("\n")
        for bb in b:
            g.insert(bb, "")
        g = "\n".join(g)
        open(f"{pre}/{ll}","w",encoding="utf-8").write(g)
    
    print("Distribution finished.")

elif sys.argv[1] == "compare":
    d = json.loads(open(f"{pre}/en.json","r",encoding="utf-8").read())
    k = d.keys()

    l = os.listdir(pre)
    for ll in l:
        if ll == "en.json":
            continue

        print(ll)
        
        t = json.loads(open(f"{pre}/{ll}","r",encoding="utf-8").read())
        u = t.keys()
        for kk in k:
            if kk in u:
                if d[kk] == t[kk]:
                    print(f"Not translated: {kk}")
            else:
                print(f"Not found: {kk}")
        
        print("")

    print("Comparation finished.")