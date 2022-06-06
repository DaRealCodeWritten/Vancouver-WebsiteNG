def config():
    dcfg = {}
    with open("master.config") as cfg:
        for line in cfg:
            line = line.strip("\n")
            split = line.split(":")
            dcfg[split[0]] = split[1]
    return dcfg
